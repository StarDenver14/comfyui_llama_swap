import re
import base64
import requests
import numpy as np
import random
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


def _tensor_to_base64(image_tensor) -> str:
    img_np = (image_tensor.numpy() * 255).clip(0, 255).astype(np.uint8)
    pil_img = Image.fromarray(img_np, mode="RGB")
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class LlamaSwapClient:
    CATEGORY = "llama-swap"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("response", "thinking")
    OUTPUT_TOOLTIPS = (
        "Clean response text with <think> blocks removed",
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

        payload = {"model": model, "messages": messages, "stream": False}

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
        inputs = LlamaSwapClient.INPUT_TYPES()
        inputs["optional"]["randomize_seed"] = (
            "BOOLEAN",
            {
                "default": False,
                "label_on": "Random seed",
                "label_off": "Fixed seed",
                "tooltip": "If enabled, a random seed will be generated ignoring the provided seed value.",
            },
        )
        return inputs

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
        randomize_seed=False,
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
            "seed": seed if not randomize_seed else random.randint(0, 2**32 - 1),
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


class LlamaSwapModelSelector:
    CATEGORY = "llama-swap"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("model_name",)
    FUNCTION = "select"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "server_url": ("STRING", {"default": DEFAULT_URL}),
                "model": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Model name — click Fetch Models button to pick from the server",
                    },
                ),
            }
        }

    def select(self, server_url: str, model: str):
        return (model,)


NODE_CLASS_MAPPINGS = {
    "LlamaSwapClient": LlamaSwapClient,
    "LlamaSwapModelSelector": LlamaSwapModelSelector,
    "LlamaSwapClientDev": LlamaSwapClientDev,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LlamaSwapClient": "🦙 Llama-Swap Client",
    "LlamaSwapModelSelector": "🦙 Llama-Swap Model Selector",
    "LlamaSwapClientDev": "🦙 Llama-Swap Client Dev",
}
