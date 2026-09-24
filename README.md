# AI Solutions

Welcome to the AI Solutions repository, a collection of deployable apps, workshops and tools built with Oracle technologies, some of them featured in [oracle.ai](https://oracle.ai). This repository contains practical implementations, demos, and guides for various AI use cases.

## Repository Structure

- `apps/`: Deployable applications, automation scripts, and infrastructure-as-code projects.
- `workshops/`: Step-by-step guides, LiveLabs content, and educational materials.
- `notebooks/`: Reserved for notebook-driven explorations and tutorials (currently minimal).

## Samples

| Sample | Brief |
| --- | --- |
| [Agentic RAG](./apps/agentic_rag/) | Agentic retrieval-augmented generation for PDFs and web content, with Oracle AI Database, Ollama, FastAPI, a CLI, and a Gradio interface. |
| [OCI GenAI Sandbox Lab](./apps/oci-sandbox-demo/) | Interactive Streamlit lab for OCI Generative AI Sandboxes and the OpenAI-compatible Responses API, including executable sandbox tutorials. |
| [Langflow + Oracle Database MCP](./apps/langflow-agentic-ai-oracle-mcp-vector-nl2sql/) | Langflow agent flows that use Oracle Database MCP, vector RAG, Select AI/NL2SQL, and AI Optimizer. |
| [LangGraph File Search](./apps/langgraph_agent_with_genai/) | Indexes PDFs, images, DOCX, and text files, then provides conversational file discovery using LangGraph, OCI Generative AI, and Oracle AI Database. |
| [Oracle MCP AI Agents](./apps/oracle-mcp-ai-agents/) | Reference architecture for agents that access live Oracle AI Database data through Model Context Protocol. |
| [MCP Audio on OKE](./apps/oracle-mcp-oke/) | Deploys an MCP audio server and Gradio client to OKE, with Terraform, OCIR image publishing, transcription, and text-analysis workflows. |
| [Oracle Select AI Insights](./apps/oracle-select-ai-insights/) | Natural-language exploration of industry data with Oracle Select AI and Oracle AI Database. |
| [RAG in a Box](./apps/rag_in_a_box/) | Podman-based local RAG demo combining Oracle AI Database and Ollama across macOS, Windows, and Linux. |
| [NVIDIA NIM on OKE](./apps/nvidia-nim-oke/) | Guide and manifests for serving NVIDIA Inference Microservices on GPU-enabled Oracle Kubernetes Engine. |
| [NVIDIA Holoscan on OCI](./apps/holoscan/) | Terraform stack that provisions an Oracle Linux A10 GPU instance with NVIDIA Holoscan and Jupyter. |
| [OCI Vision with Oracle JET](./apps/OJET%20(VDOM)%20-%20OCI%20Vision/) | Oracle JET virtual-DOM front end that presents image analysis results from OCI Vision. |
| [MongoDB Migration Tools](./apps/mongo-migration/) | Utilities and example scripts for moving MongoDB collections and workloads to Oracle Database. |
| [CSV/JSON Translation](./apps/oci-csv-json-translation/) | Translates selected CSV columns or JSON keys with OCI Language while preserving source structure. |
| [Bulk Document Translation](./apps/oci-language-multiple-translation/) | Translates multiple documents between OCI Object Storage buckets with OCI Language. |
| [OCI Language Translation Tools](./apps/oci-language-translation/) | Combined document and field-translation utilities built on OCI Language. |
| [OCI Subtitle Translation](./apps/oci-subtitle-translation/) | Transcribes audio to SRT and translates subtitles into multiple languages using OCI Speech and OCI Language. |

## Workshops

| Workshop | Brief |
| --- | --- |
| [AI Meetings](./workshops/ai-meetings/) | Build a Visual Builder application for meeting transcription, summarization, sentiment analysis, and question answering. |
| [Data in the AI Revolution](./workshops/data-in-ai-revolution/) | Introduction to AI data types, structures, processing, and representative ML use cases. |
| [Mask Detection: Labeling](./workshops/mask_detection_labeling/intro/intro.md) | Create and label a computer-vision dataset for correct, incorrect, and absent mask states using Roboflow. |
| [Mask Detection: Training](./workshops/mask_detection_training/intro/intro.md) | Train, augment, and run inference with a YOLO mask-detection model on OCI. |
| [Neural Networks Hero](./workshops/neural_networks_hero/intro/intro.md) | Build a machine-learning workflow that predicts League of Legends match outcomes and player-performance insights. |

## Getting started

1. Choose a sample or workshop from the tables above.
2. Read its README or introductory lab before provisioning services or installing dependencies.
3. Follow that project's setup instructions; OCI-based examples commonly require an OCI account, IAM policies, and configured credentials.

## Repository layout

- `apps/` — applications, scripts, and infrastructure-as-code projects.
- `workshops/` — hands-on educational material and LiveLabs-style labs.
- `notebooks/` — reserved for notebook-based explorations.

## Resources

- [Oracle AI Database](https://www.oracle.com/database/ai-native-database-26ai/)
- [Oracle Cloud Infrastructure](https://www.oracle.com/cloud/)

## 🤝 Contributing

We welcome contributions! Please see individual solution directories for contribution guidelines.

## License

Copyright (c) 2024 Oracle and/or its affiliates.

Licensed under the Universal Permissive License (UPL), Version 1.0. See [LICENSE](./LICENSE).
