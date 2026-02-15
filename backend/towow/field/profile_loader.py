"""
Profile loader — converts agent JSON files into natural-language text for encoding.

Functions:
  - profile_to_text: single agent dict -> text string
  - load_profiles_from_json: single JSON file -> {agent_key: text}
  - load_all_profiles: all scene directories -> {prefixed_id: text}

The text format uses " | " as separator, matching the POC convention.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Scene directories and their ID prefixes (avoid cross-scene ID collision)
_SCENE_DIRS = [
    ("S1_hackathon", "h_"),
    ("S2_skill_exchange", "s_"),
    ("R1_recruitment", "r_"),
    ("M1_matchmaking", "m_"),
]

# Fields to extract from each agent profile
_CORE_FIELDS = ["name", "role", "occupation", "bio"]
_LIST_FIELDS = ["skills", "interests"]
_EXTRA_FIELDS = [
    "can_teach", "want_to_learn", "looking_for",
    "experience", "ideal_match", "values",
    "quirks", "work_style",
]


def profile_to_text(agent_data: dict) -> str:
    """Convert an agent profile dict into a natural-language text string.

    Includes: name, role/occupation, bio, skills, interests, and
    scene-specific fields (can_teach, want_to_learn, looking_for, etc.).

    Parts are joined with " | " as separator.
    Returns empty string if no meaningful data found.
    """
    parts: list[str] = []

    # Core scalar fields
    for field_name in _CORE_FIELDS:
        val = agent_data.get(field_name)
        if val and str(val).strip():
            parts.append(str(val).strip())

    # List fields (skills, interests)
    for field_name in _LIST_FIELDS:
        val = agent_data.get(field_name)
        if val and isinstance(val, list):
            joined = ", ".join(str(item) for item in val if str(item).strip())
            if joined:
                parts.append(f"{field_name}: {joined}")

    # Extra scene-specific fields
    for field_name in _EXTRA_FIELDS:
        val = agent_data.get(field_name)
        if not val:
            continue
        if isinstance(val, list):
            joined = ", ".join(str(v) for v in val if str(v).strip())
            if joined:
                parts.append(f"{field_name}: {joined}")
        else:
            text = str(val).strip()
            if text:
                parts.append(f"{field_name}: {text}")

    return " | ".join(parts)


def load_profiles_from_json(filepath: str | Path) -> dict[str, str]:
    """Load agent profiles from a single JSON file.

    Args:
        filepath: Path to an agents.json file.
            Expected format: {"agent_key": {profile dict}, ...}

    Returns:
        {agent_key: profile_text} for agents with non-empty text.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning("Agent file not found: %s", filepath)
        return {}

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles: dict[str, str] = {}
    for agent_key, agent_data in data.items():
        text = profile_to_text(agent_data)
        if text.strip():
            profiles[agent_key] = text

    return profiles


def load_all_profiles(data_dirs: list[str | Path] | None = None) -> dict[str, str]:
    """Load all agent profiles from scene directories.

    Args:
        data_dirs: Optional list of explicit paths to search.
            If None, searches the default apps/ directories relative to project root.

    Returns:
        {prefixed_agent_id: profile_text} with scene prefix to avoid ID collisions.
        Prefixes: h_ (hackathon), s_ (skill_exchange), r_ (recruitment), m_ (matchmaking).
    """
    if data_dirs is not None:
        # Explicit paths mode — no prefix, just load and merge
        all_profiles: dict[str, str] = {}
        for dir_path in data_dirs:
            agents_file = Path(dir_path) / "data" / "agents.json"
            if not agents_file.exists():
                # Also try the path directly as a file
                agents_file = Path(dir_path)
                if not agents_file.exists():
                    logger.warning("Path not found: %s", dir_path)
                    continue
            loaded = load_profiles_from_json(agents_file)
            all_profiles.update(loaded)
        return all_profiles

    # Default mode — find apps/ directory relative to this file
    # backend/towow/field/profile_loader.py -> backend/ -> project_root/
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    apps_dir = project_root / "apps"

    all_profiles = {}
    for scene_dir_name, prefix in _SCENE_DIRS:
        agents_file = apps_dir / scene_dir_name / "data" / "agents.json"
        loaded = load_profiles_from_json(agents_file)
        for agent_key, text in loaded.items():
            all_profiles[f"{prefix}{agent_key}"] = text

    logger.info("Loaded %d agent profiles from %d scenes", len(all_profiles), len(_SCENE_DIRS))
    return all_profiles
