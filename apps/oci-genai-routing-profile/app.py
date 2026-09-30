"""OCI Generative AI routing-profile demo server (standard-library only)."""

from __future__ import annotations

import json
import os
import time
import asyncio
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import httpx2
import httpx
import oci
from openai import APIStatusError, AsyncOpenAI, OpenAI
from langchain_openai import ChatOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
LOGS: list[dict] = []
EXPERIMENTS: dict[str, object] = {}


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Load simple KEY=VALUE entries without overriding an explicitly exported value."""
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


load_dotenv()

# The local environment has an unavailable proxy. OCI inference and control-plane
# calls must both connect directly; explicit shell exports can still be used by
# other processes outside this demo server.
for proxy_variable in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(proxy_variable, None)


def add_log(level: str, message: str, **details: object) -> None:
    LOGS.insert(0, {"at": datetime.now(timezone.utc).isoformat(), "level": level, "message": message, **details})
    del LOGS[80:]


def configuration() -> dict:
    return {
        "region": os.getenv("OCI_REGION", "us-chicago-1"),
        "projectId": os.getenv("OCI_GENAI_PROJECT_ID", ""),
        "configured": bool(os.getenv("OCI_GENAI_API_KEY") and os.getenv("OCI_GENAI_PROJECT_ID")),
        "model": os.getenv("OCI_MODEL_ID", "openai.gpt-oss-120b"),
        "routingProfileId": os.getenv("OCI_ROUTING_PROFILE_ID", ""),
    }


def routed_response(prompt: str, selected_model: str) -> dict:
    """Run one OCI OpenAI-compatible request and retain routing evidence."""
    cfg = configuration()
    base_url = f"https://inference.generativeai.{cfg['region']}.oci.oraclecloud.com/20231130/actions/v1"
    started = time.perf_counter()
    client = OpenAI(
        base_url=base_url,
        api_key=os.environ["OCI_GENAI_API_KEY"],
        timeout=120.0,
        http_client=httpx2.Client(trust_env=False),
    )
    try:
        raw_response = client.responses.with_raw_response.create(model=selected_model, input=prompt)
        response = raw_response.parse()
        metadata = {key: value for key, value in raw_response.headers.items() if key.startswith("opc-") or "region" in key.lower()}
        return {
            "text": response.output_text or "(No text output returned)",
            "id": response.id,
            "usage": response.usage.model_dump() if response.usage else None,
            "model": selected_model,
            "elapsedMs": round((time.perf_counter() - started) * 1000),
            "ociMetadata": metadata,
            "selectedRegion": metadata.get("x-genai-selected-region"),
        }
    finally:
        client.close()


def relevant_metadata(headers: object) -> dict:
    return {str(key): str(value) for key, value in dict(headers or {}).items() if str(key).startswith("opc-") or "region" in str(key).lower()}


def langchain_agent_response(prompt: str, selected_model: str) -> dict:
    """Invoke a real LangChain chat workflow through the routing profile."""
    cfg = configuration()
    started = time.perf_counter()
    model = ChatOpenAI(
        model=selected_model,
        base_url=f"https://inference.generativeai.{cfg['region']}.oci.oraclecloud.com/20231130/actions/v1",
        api_key=os.environ["OCI_GENAI_API_KEY"],
        http_client=httpx.Client(trust_env=False),
        include_response_headers=True,
        temperature=0,
    )
    response = model.invoke([
        ("system", "You are a concise regional-routing analyst. Answer in one sentence."),
        ("human", prompt),
    ])
    metadata = relevant_metadata(response.response_metadata.get("headers", {}))
    return {"text": str(response.content), "id": response.id or "langchain-run", "usage": response.usage_metadata, "model": selected_model, "elapsedMs": round((time.perf_counter() - started) * 1000), "ociMetadata": metadata, "selectedRegion": metadata.get("x-genai-selected-region"), "task": "LangChain agent"}


def oci_python_sdk_response(prompt: str, selected_model: str) -> dict:
    """Use OCI request signing with ~/.oci/config and the DEFAULT profile."""
    config_file = os.path.expanduser(os.getenv("OCI_CONFIG_FILE", "~/.oci/config"))
    profile_name = os.getenv("OCI_CLI_PROFILE", "DEFAULT")
    sdk_config = oci.config.from_file(file_location=config_file, profile_name=profile_name)
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(sdk_config)
    started = time.perf_counter()
    response = client.chat(
        oci.generative_ai_inference.models.ChatDetails(
            compartment_id=os.getenv("OCI_ROUTING_PROFILE_COMPARTMENT_ID", os.environ["OCI_COMPARTMENT_ID"]),
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(model_id=selected_model),
            chat_request=oci.generative_ai_inference.models.GenericChatRequest(
                messages=[oci.generative_ai_inference.models.UserMessage(content=[oci.generative_ai_inference.models.TextContent(text=prompt)])],
                temperature=0,
                max_completion_tokens=120,
            ),
        )
    )
    choice = response.data.chat_response.choices[0]
    output = "".join(item.text for item in choice.message.content if getattr(item, "text", None))
    metadata = relevant_metadata(response.headers)
    return {"text": output, "id": metadata.get("opc-request-id", "oci-sdk-run"), "usage": None, "model": selected_model, "elapsedMs": round((time.perf_counter() - started) * 1000), "ociMetadata": metadata, "selectedRegion": metadata.get("x-genai-selected-region"), "task": "OCI Python SDK (DEFAULT)"}


async def agents_sdk_response_async(prompt: str, selected_model: str) -> dict:
    """Invoke the OpenAI Agents SDK with OCI as its OpenAI-compatible provider."""
    cfg = configuration()
    captured_headers: list[dict] = []

    async def capture_headers(response: httpx.Response) -> None:
        captured_headers.append(relevant_metadata(response.headers))

    started = time.perf_counter()
    http_client = httpx.AsyncClient(trust_env=False, event_hooks={"response": [capture_headers]})
    client = AsyncOpenAI(base_url=f"https://inference.generativeai.{cfg['region']}.oci.oraclecloud.com/20231130/actions/v1", api_key=os.environ["OCI_GENAI_API_KEY"], http_client=http_client)
    try:
        set_tracing_disabled(True)
        agent = Agent(
            name="Routing validation agent",
            instructions="Answer the user concisely in one sentence. Do not call external tools.",
            model=OpenAIChatCompletionsModel(model=selected_model, openai_client=client),
        )
        result = await Runner.run(agent, prompt)
        metadata = next((item for item in captured_headers if item.get("x-genai-selected-region")), captured_headers[-1] if captured_headers else {})
        return {"text": str(result.final_output), "id": "agents-sdk-run", "usage": None, "model": selected_model, "elapsedMs": round((time.perf_counter() - started) * 1000), "ociMetadata": metadata, "selectedRegion": metadata.get("x-genai-selected-region"), "task": "OpenAI Agents SDK"}
    finally:
        await client.close()
        await http_client.aclose()


def run_task(task: str, prompt: str, selected_model: str) -> dict:
    if task == "oci-sdk":
        return oci_python_sdk_response(prompt, selected_model)
    if task == "langchain":
        return langchain_agent_response(prompt, selected_model)
    if task == "agents-sdk":
        return asyncio.run(agents_sdk_response_async(prompt, selected_model))
    result = routed_response(prompt, selected_model)
    result["task"] = "OpenAI SDK inference"
    return result


def profile_evidence(profile_id: str) -> dict:
    """Read the control-plane policy that constrains routing, using DEFAULT."""
    cfg = configuration()
    sdk_config = oci.config.from_file(profile_name=os.getenv("OCI_CLI_PROFILE", "DEFAULT"))
    profile = oci.generative_ai.GenerativeAiClient(sdk_config).get_routing_profile(profile_id).data
    return {
        "id": profile.id,
        "state": profile.lifecycle_state,
        "allowedModels": profile.model_routing_policy.allowed_models,
        "allowedRegions": profile.region_routing_policy.allowed_regions,
        "compartmentId": profile.compartment_id,
        "controlPlaneRegion": cfg["region"],
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        request_url = urlparse(self.path)
        if request_url.path == "/api/config":
            self.send_json(HTTPStatus.OK, configuration())
        elif request_url.path == "/api/logs":
            self.send_json(HTTPStatus.OK, LOGS)
        elif request_url.path == "/api/profile":
            profile_id = parse_qs(request_url.query).get("profileId", [configuration()["routingProfileId"]])[0]
            if not profile_id:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Set OCI_ROUTING_PROFILE_ID first."})
                return
            try:
                self.send_json(HTTPStatus.OK, profile_evidence(profile_id))
            except Exception as error:
                self.send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Unable to read routing profile: {error}"})
        else:
            super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {"/api/chat", "/api/experiment", "/api/experiment/cancel"}:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(content_length))
            if self.path == "/api/experiment/cancel":
                run_id = data.get("runId", "")
                cancel_event = EXPERIMENTS.get(run_id)
                if not cancel_event:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "Experiment run was not found or already completed."})
                    return
                cancel_event.set()
                add_log("info", "Experiment cancellation requested", runId=run_id)
                self.send_json(HTTPStatus.OK, {"runId": run_id, "cancellationRequested": True})
                return
            prompt = data.get("prompt", "").strip()
            if not prompt:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "A prompt is required."})
                return
            cfg = configuration()
            selected_model = data.get("routingProfileId") or cfg["routingProfileId"] or data.get("model") or cfg["model"]
            if not cfg["configured"]:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing OCI_GENAI_API_KEY or OCI_GENAI_PROJECT_ID. Set them in your shell; the browser never receives the key."})
                return
            endpoint = f"https://inference.generativeai.{cfg['region']}.oci.oraclecloud.com/20231130/actions/v1/responses"
            if self.path == "/api/chat":
                add_log("info", "Submitting OpenAI-compatible Responses request", endpoint=endpoint, model=selected_model, routingProfile=selected_model.startswith("ocid1."))
                result = run_task(data.get("task", "direct"), prompt, selected_model)
                add_log(
                    "success",
                    "Routed response received",
                    status=200,
                    elapsedMs=result["elapsedMs"],
                    responseId=result["id"],
                    selectedRegion=result["selectedRegion"],
                    ociMetadata=result["ociMetadata"],
                    responseText=result["text"],
                    usage=result["usage"],
                )
                self.send_json(HTTPStatus.OK, result)
                return

            task = data.get("task", "direct")
            if task not in {"direct", "langchain", "agents-sdk", "oci-sdk"}:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Unknown experiment task."})
                return
            count = max(1, min(int(data.get("count", 6)), 24))
            concurrency = max(1, min(int(data.get("concurrency", 2)), 6))
            run_id = data.get("runId") or str(uuid.uuid4())
            cancel_event = __import__("threading").Event()
            EXPERIMENTS[run_id] = cancel_event
            add_log("info", "Starting routing experiment", runId=run_id, count=count, concurrency=concurrency, model=selected_model, task=task)
            results = []
            executor = ThreadPoolExecutor(max_workers=concurrency)
            try:
                jobs = {executor.submit(run_task, task, prompt, selected_model): index for index in range(1, count + 1)}
                pending = set(jobs)
                while pending and not cancel_event.is_set():
                    done, pending = wait(pending, timeout=0.25, return_when=FIRST_COMPLETED)
                    for future in done:
                        index = jobs[future]
                        try:
                            result = future.result()
                            result["sequence"] = index
                            result["ok"] = True
                            results.append(result)
                        except Exception as error:
                            results.append({"sequence": index, "ok": False, "error": str(error)})
                if cancel_event.is_set():
                    for future in pending:
                        future.cancel()
                        results.append({"sequence": jobs[future], "ok": False, "cancelled": True, "error": "Cancelled before completion"})
            finally:
                executor.shutdown(wait=not cancel_event.is_set(), cancel_futures=cancel_event.is_set())
                EXPERIMENTS.pop(run_id, None)
            results.sort(key=lambda item: item["sequence"])
            cancelled = cancel_event.is_set()
            add_log("info" if cancelled else "success", "Routing experiment cancelled" if cancelled else "Routing experiment complete", runId=run_id, passed=sum(item["ok"] for item in results), total=count)
            self.send_json(HTTPStatus.OK, {"runId": run_id, "cancelled": cancelled, "task": task, "model": selected_model, "count": count, "concurrency": concurrency, "results": results})
        except APIStatusError as error:
            message = error.message or str(error)
            add_log("error", "OCI rejected inference request", status=error.status_code, detail=message)
            self.send_json(error.status_code, {"error": message})
        except (TimeoutError, ValueError, KeyError, OSError) as error:
            add_log("error", "Demo server error", detail=str(error))
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    print(f"OCI Routing Profile Demo: http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
