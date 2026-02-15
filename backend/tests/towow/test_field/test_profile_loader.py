"""
Tests for profile_loader — converting agent JSON into text for encoding.

Tests both the text conversion logic and file loading.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from towow.field.profile_loader import (
    load_all_profiles,
    load_profiles_from_json,
    profile_to_text,
)

# Project root (Towow/) for locating real agent data files
# Path: backend/tests/towow/test_field/test_profile_loader.py -> 5 parents -> Towow/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


class TestProfileToText:
    """Tests for profile_to_text()."""

    def test_basic(self):
        """Basic profile with name, role, bio produces non-empty text."""
        agent = {
            "name": "Alice",
            "role": "ML Engineer",
            "bio": "5 years of NLP experience",
        }
        text = profile_to_text(agent)
        assert "Alice" in text
        assert "ML Engineer" in text
        assert "NLP" in text
        assert " | " in text

    def test_with_skills_and_interests(self):
        """Skills and interests should appear as labeled lists."""
        agent = {
            "name": "Bob",
            "skills": ["Python", "React", "Docker"],
            "interests": ["open source", "gaming"],
        }
        text = profile_to_text(agent)
        assert "skills: Python, React, Docker" in text
        assert "interests: open source, gaming" in text

    def test_with_optional_fields(self):
        """Extra fields like can_teach, work_style should be included."""
        agent = {
            "name": "Carol",
            "role": "Designer",
            "can_teach": ["UI design", "Figma"],
            "want_to_learn": "backend development",
            "work_style": "Night owl, async communication",
            "values": ["creativity", "empathy"],
        }
        text = profile_to_text(agent)
        assert "Carol" in text
        assert "can_teach: UI design, Figma" in text
        assert "want_to_learn: backend development" in text
        assert "work_style: Night owl" in text
        assert "values: creativity, empathy" in text

    def test_empty_agent(self):
        """Empty agent dict should produce empty string."""
        assert profile_to_text({}) == ""

    def test_occupation_as_role_fallback(self):
        """'occupation' should be used when 'role' is absent."""
        agent = {"name": "Dave", "occupation": "Data Scientist"}
        text = profile_to_text(agent)
        assert "Data Scientist" in text

    def test_separator_format(self):
        """Parts should be separated by ' | '."""
        agent = {"name": "Eve", "role": "PM", "bio": "Product leader"}
        text = profile_to_text(agent)
        parts = text.split(" | ")
        assert len(parts) == 3
        assert parts[0] == "Eve"
        assert parts[1] == "PM"
        assert parts[2] == "Product leader"


class TestLoadProfilesFromJson:
    """Tests for load_profiles_from_json() with real data files."""

    def test_load_hackathon_agents(self):
        """Load real hackathon agents.json and verify structure."""
        filepath = _PROJECT_ROOT / "apps" / "S1_hackathon" / "data" / "agents.json"
        if not filepath.exists():
            pytest.skip(f"Test data not found: {filepath}")

        profiles = load_profiles_from_json(filepath)

        assert len(profiles) > 0
        # All values should be non-empty strings
        for key, text in profiles.items():
            assert isinstance(key, str)
            assert isinstance(text, str)
            assert len(text) > 0

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file should return empty dict."""
        profiles = load_profiles_from_json("/nonexistent/path/agents.json")
        assert profiles == {}


class TestLoadAllProfiles:
    """Tests for load_all_profiles() with default directories."""

    def test_load_all_default(self):
        """Load from all default scene directories."""
        # Check at least one scene directory exists
        hackathon = _PROJECT_ROOT / "apps" / "S1_hackathon" / "data" / "agents.json"
        if not hackathon.exists():
            pytest.skip("Agent data files not found")

        profiles = load_all_profiles()

        assert len(profiles) > 0

        # Verify prefixes exist
        prefixes_found = set()
        for key in profiles:
            prefix = key[:2]
            if prefix in ("h_", "s_", "r_", "m_"):
                prefixes_found.add(prefix)

        # Should find at least the hackathon prefix
        assert "h_" in prefixes_found

        # Verify all values are non-empty strings
        for key, text in profiles.items():
            assert isinstance(text, str)
            assert len(text) > 0

    def test_load_with_explicit_dirs(self):
        """Load from explicitly provided directories."""
        hackathon_dir = _PROJECT_ROOT / "apps" / "S1_hackathon"
        if not (hackathon_dir / "data" / "agents.json").exists():
            pytest.skip("Hackathon data not found")

        profiles = load_all_profiles(data_dirs=[hackathon_dir])

        assert len(profiles) > 0
        # With explicit dirs, keys should NOT have scene prefix
        for key in profiles:
            assert not key.startswith("h_")
