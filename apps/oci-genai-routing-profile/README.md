# OCI Routing Profile Lab

An Oracle-themed local lab for validating OCI Generative AI routing profiles with three live workloads:

- Direct OpenAI Python SDK inference
- LangChain chat-agent workflow
- OpenAI Agents SDK workflow

Every run sends the routing-profile OCID as `model`, records `x-genai-selected-region`, and validates that the selected region belongs to the profile’s allowed-region policy. The browser never receives `OCI_GENAI_API_KEY`.

## Run

1. Refer Infra section to setup profiles.
1. Copy `.env.example` to `.env` and set your OCI values, including `OCI_ROUTING_PROFILE_ID` and `OCI_GENAI_API_KEY`.
1. Install dependencies and run the local server:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://localhost:3000. Use **Validate profile**, then choose one of the three experiment modes. Each experiment produces real model usage.

## Infra - Terraform deployment

The direct Terraform resource `oci_generative_ai_routing_profile` creates a profile and a compartment-scoped policy for `generativeaiapikey` principals.

```sh
cd infra
cp terraform.tfvars.example terraform.tfvars
# Set tenancy_id, compartment_id, model_id, and target_regions.
terraform init
terraform apply
```

Use `terraform output -raw routing_profile_id` as `OCI_ROUTING_PROFILE_ID`. For an existing profile in another compartment, set `policy_compartment_id` to its owning compartment before applying the policy.

## Validation model

OCI guarantees that routed requests select only from the profile’s configured target regions. This lab verifies both sides: it reads the active control-plane policy and compares each response’s `x-genai-selected-region` header with that allowlist.

## References

[OCI routing profiles](https://docs.oracle.com/en-us/iaas/Content/generative-ai/routing-profile.htm) · [OCI API-key permissions](https://docs.oracle.com/en-us/iaas/Content/generative-ai/add-api-permission.htm) · [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
