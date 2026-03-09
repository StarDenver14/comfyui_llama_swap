# ComfyUI Llama-Swap Client

A ComfyUI custom node for [llama-swap](https://github.com/mostlygeek/llama-swap) — the hot-swap model manager for llama.cpp.

## Nodes

| Node | Purpose |
|---|---|
| 🦙 **Llama-Swap Client** | Full inference: text + vision, system prompt, unload toggle |
| 🦙 **Llama-Swap Model Selector** | Standalone model picker to feed `model_name` into other nodes |

## Features

- **Fetch Models** button — live-pulls `/v1/models` from your running llama-swap server and refreshes the dropdown in-place
- **Running** button — queries `/running` and shows which model is currently in GPU memory
- **Unload All** button — manually calls `/unload` to free VRAM without leaving ComfyUI
- **Unload after Generate** toggle — auto-calls `/unload` after every generation (great for VRAM-constrained workflows)
- **Vision support** — attach any ComfyUI IMAGE node; the first frame is JPEG-encoded and sent as an `image_url` message
- **Thinking extraction** — `<think>` / `<thinking>` blocks are stripped from `response` and surfaced in the separate `thinking` output; connect it to a Note node or another text output to debug reasoning chains

## Outputs

| Output | Content |
|---|---|
| `response` | Clean human-readable text, **no** `<think>` blocks |
| `thinking` | Extracted reasoning (empty string if the model produced none) |

## Setup

1. Clone / copy this folder to `ComfyUI/custom_nodes/comfyui_llama_swap/`
2. Restart ComfyUI
3. Add a **🦙 Llama-Swap Client** node, set `server_url` to your llama-swap address, hit **🔄 Fetch Models**

## Requirements

```
pip install requests pillow
```
(Both are usually already present in a standard ComfyUI environment.)
