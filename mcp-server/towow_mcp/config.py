"""Local configuration management for ~/.towow/config.json."""

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".towow"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_BACKEND_URL = "https://towow-production.up.railway.app"


def _read_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_config(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_backend_url() -> str:
    env_url = os.environ.get("TOWOW_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")
    config = _read_config()
    return config.get("backend_url", DEFAULT_BACKEND_URL).rstrip("/")


def get_agent_id() -> str | None:
    return _read_config().get("agent_id")


def get_last_negotiation_id() -> str | None:
    return _read_config().get("last_negotiation_id")


def save_agent(agent_id: str, display_name: str) -> None:
    config = _read_config()
    config["agent_id"] = agent_id
    config["display_name"] = display_name
    _write_config(config)


def save_last_negotiation(negotiation_id: str) -> None:
    config = _read_config()
    config["last_negotiation_id"] = negotiation_id
    _write_config(config)
