import requests
from server import PromptServer
from aiohttp import web


def setup_routes():
    @PromptServer.instance.routes.get("/llama_swap/models")
    async def get_models(request):
        url = request.query.get("url", "http://localhost:8080").rstrip("/")
        try:
            r = requests.get(f"{url}/v1/models", timeout=5)
            r.raise_for_status()
            models = [m["id"] for m in r.json().get("data", [])]
            return web.json_response({"models": models, "status": "ok"})
        except Exception as e:
            return web.json_response({"models": [], "status": "error", "error": str(e)})

    @PromptServer.instance.routes.get("/llama_swap/running")
    async def get_running(request):
        url = request.query.get("url", "http://localhost:8080").rstrip("/")
        try:
            r = requests.get(f"{url}/running", timeout=5)
            r.raise_for_status()
            return web.json_response(r.json())
        except Exception as e:
            return web.json_response({"running": [], "error": str(e)})

    @PromptServer.instance.routes.get("/llama_swap/unload")
    async def do_unload(request):
        url = request.query.get("url", "http://localhost:8080").rstrip("/")
        try:
            r = requests.get(f"{url}/unload", timeout=10)
            return web.json_response({"status": "ok", "message": r.text.strip()})
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)})
