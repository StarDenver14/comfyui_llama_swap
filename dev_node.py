import re
import base64
import requests
import numpy as np
from io import BytesIO
from PIL import Image

DEFAULT_URL = "http://localhost:8080"


def _extract_thinking(text: str):
    pattern = re.compile(
        r"<think(?:ing)?>(.*?)</think(?:ing)?>", re.DOTALL | re.IGNORECASE
    )
    thinking_parts = pattern.findall(text)
    thinking_text = "\n\n".join(p.strip() for p in thinking_parts)
    clean_text = pattern.sub("", text).strip()
    return clean_text, thinking_text


class LlamaSwapClientDev:
    CATEGORY = "llama-swap"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("response", "thinking")
    OUTPUT_TOOLTIPS = (
        "Clean response text with <think> blocks removed (debug node)",
        "Extracted thinking/reasoning content (empty if model produced none)",
    )
    FUNCTION = "generate"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "server_url": (
                    "STRING",
                    {
                        "default": DEFAULT_URL,
                        "tooltip": "llama-swap server base URL",
                    },
                ),
                "model": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Model name — click Fetch Models button to pick from the server",
                    },
                ),
                "system_prompt": (
                    "STRING",
                    {
                        "default": "You are a helpful assistant.",
                        "multiline": True,
                        "tooltip": "System prompt sent before the user message",
                    },
                ),
                "prompt": (
                    "STRING",
                    {
                        "default": "Hello!",
                        "multiline": True,
                        "tooltip": "User message / question",
                    },
                ),
                "unload_after_generate": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "Unload model after ✓",
                        "label_off": "Keep model loaded",
                        "tooltip": "Call /unload on the llama-swap server after generation",
                    },
                ),
            },
            "optional": {
                "image": (
                    "IMAGE",
                    {
                        "tooltip": "Optional image for vision models (first frame used)",
                    },
                ),
                "temperature": (
                    "NUMBER",
                    {
                        "default": 0.7,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.1,
                        "tooltip": "Sampling temperature",
                    },
                ),
                "top_p": (
                    "NUMBER",
                    {
                        "default": 0.9,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "Nucleus sampling probability",
                    },
                ),
                "top_k": (
                    "INT",
                    {
                        "default": 40,
                        "min": 0,
                        "max": 1000,
                        "step": 1,
                        "tooltip": "Top‑k sampling",
                    },
                ),
                "max_tokens": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 4096,
                        "step": 1,
                        "tooltip": "Maximum number of tokens to generate. 0 = unlimited.",
                    },
                ),
                "stop": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Stop sequence(s). One per line.",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": -1,
                        "min": -1,
                        "max": 2147483647,
                        "tooltip": "Random seed. -1 = system clock.",
                    },
                ),
                "logit_bias": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Map token id to bias logits. Format: `12345:-1.0, 67890:1.5`",
                    },
                ),
                "frequency_penalty": (
                    "NUMBER",
                    {
                        "default": 0.0,
                        "min": -2.0,
                        "max": 2.0,
                        "step": 0.1,
                        "tooltip": "Frequency penalty",
                    },
                ),
                "presence_penalty": (
                    "NUMBER",
                    {
                        "default": 0.0,
                        "min": -2.0,
                        "max": 2.0,
                        "step": 0.1,
                        "tooltip": "Presence penalty",
                    },
                ),
            },
        }

    def generate(
        self,
        server_url,
        model,
        system_prompt,
        prompt,
        unload_after_generate,
        image=None,
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        max_tokens=0,
        stop="",
        seed=-1,
        logit_bias="",
        frequency_penalty=0.0,
        presence_penalty=0.0,
    ):
        base_url = server_url.rstrip("/")
        messages = []

        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})

        if image is not None:
            img_b64 = _tensor_to_base64(image[0])
            user_content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                },
            ]
        else:
            user_content = prompt

        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_tokens": max_tokens,
            "stop": [s.strip() for s in stop.split("\n") if s.strip()],
            "seed": seed,
            "logit_bias": logit_bias,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }

        try:
            r = requests.post(
                f"{base_url}/v1/chat/completions",
                json=payload,
                timeout=300,
            )
            r.raise_for_status()
            full_text = r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            err = f"[LlamaSwap ERROR] {exc}"
            if unload_after_generate:
                try:
                    requests.get(f"{base_url}/unload", timeout=5)
                except Exception:
                    pass
            return (err, "")

        clean_text, thinking_text = _extract_thinking(full_text)

        if unload_after_generate:
            try:
                requests.get(f"{base_url}/unload", timeout=5)
            except Exception:
                pass

        return (clean_text, thinking_text)


NODE_CLASS_MAPPINGS = {
    "LlamaSwapClientDev": LlamaSwapClientDev,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LlamaSwapClientDev": "🦙 Llama‑Swap Client Dev",
}
