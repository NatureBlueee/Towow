"""REST client for the Towow Store API."""

import httpx

from .config import get_backend_url


class TowowClient:
    """Thin async wrapper around Store API endpoints."""

    def __init__(self, backend_url: str | None = None):
        self.base = (backend_url or get_backend_url()).rstrip("/")
        self._http = httpx.AsyncClient(timeout=30.0)

    def _url(self, path: str) -> str:
        return f"{self.base}/store/api{path}"

    async def get_scenes(self) -> list[dict]:
        resp = await self._http.get(self._url("/scenes"))
        resp.raise_for_status()
        data = resp.json()
        return data.get("scenes", [])

    async def get_agents(self, scope: str = "all") -> list[dict]:
        resp = await self._http.get(self._url("/agents"), params={"scope": scope})
        resp.raise_for_status()
        data = resp.json()
        return data.get("agents", [])

    async def quick_register(
        self,
        email: str,
        display_name: str,
        raw_text: str,
        scene_id: str = "",
    ) -> dict:
        resp = await self._http.post(
            self._url("/quick-register"),
            json={
                "email": email,
                "phone": "",
                "display_name": display_name,
                "raw_text": raw_text,
                "subscribe": False,
                "scene_id": scene_id,
            },
        )
        if resp.status_code == 409:
            # Already registered — extract agent_id from response
            data = resp.json()
            return {
                "agent_id": data.get("agent_id", ""),
                "display_name": display_name,
                "message": data.get("message", data.get("error", "already registered")),
            }
        resp.raise_for_status()
        return resp.json()

    async def negotiate(self, intent: str, scope: str, user_id: str) -> dict:
        resp = await self._http.post(
            self._url("/negotiate"),
            json={
                "intent": intent,
                "scope": scope,
                "user_id": user_id,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_negotiation(self, negotiation_id: str) -> dict:
        resp = await self._http.get(self._url(f"/negotiate/{negotiation_id}"))
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._http.aclose()
