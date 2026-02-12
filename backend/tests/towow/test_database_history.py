"""Tests for NegotiationHistory + NegotiationOffer persistence (ADR-007).

Covers:
- Schema creation (auto via get_engine)
- CRUD functions: save_negotiation, update_negotiation, save_offers,
  get_user_history, get_negotiation_detail, save_assist_output
- Edge cases: duplicate negotiation_id, missing records, scene filtering
"""

import pytest
from datetime import datetime

# Use in-memory SQLite for test isolation
import database as db


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Each test gets a fresh in-memory database."""
    # Reset module-level singletons
    db._engine = None
    db._SessionLocal = None
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.get_engine()
    yield
    db._engine = None
    db._SessionLocal = None


class TestSaveNegotiation:
    def test_creates_record(self):
        h = db.save_negotiation(
            negotiation_id="neg_001",
            user_id="user_a",
            demand_text="I need a frontend developer",
            scene_id="hackathon",
            demand_mode="manual",
            scope="scene:hackathon",
            agent_count=5,
        )
        assert h.negotiation_id == "neg_001"
        assert h.user_id == "user_a"
        assert h.status == "pending"
        assert h.agent_count == 5

    def test_with_assist_output(self):
        h = db.save_negotiation(
            negotiation_id="neg_002",
            user_id="user_b",
            demand_text="raw text",
            assist_output="enhanced text from SecondMe",
        )
        assert h.assist_output == "enhanced text from SecondMe"

    def test_duplicate_id_raises(self):
        db.save_negotiation(negotiation_id="neg_dup", user_id="u", demand_text="a")
        with pytest.raises(Exception):
            db.save_negotiation(negotiation_id="neg_dup", user_id="u", demand_text="b")


class TestUpdateNegotiation:
    def test_updates_fields(self):
        db.save_negotiation(negotiation_id="neg_upd", user_id="u", demand_text="d")
        updated = db.update_negotiation(
            "neg_upd",
            status="completed",
            formulated_text="enriched demand",
            plan_output="plan text here",
            center_rounds=2,
            agent_count=3,
        )
        assert updated is not None
        assert updated.status == "completed"
        assert updated.formulated_text == "enriched demand"
        assert updated.plan_output == "plan text here"
        assert updated.center_rounds == 2
        assert updated.agent_count == 3

    def test_nonexistent_returns_none(self):
        result = db.update_negotiation("nonexistent", status="failed")
        assert result is None


class TestSaveOffers:
    def test_saves_multiple_offers(self):
        db.save_negotiation(negotiation_id="neg_off", user_id="u", demand_text="d")
        db.save_offers("neg_off", [
            {
                "agent_id": "agent_1",
                "agent_name": "Alice",
                "resonance_score": 0.85,
                "offer_text": "I can help with frontend",
                "confidence": 0.9,
                "agent_state": "offered",
                "source": "Claude",
            },
            {
                "agent_id": "agent_2",
                "agent_name": "Bob",
                "resonance_score": 0.72,
                "offer_text": "I specialize in React",
                "agent_state": "offered",
                "source": "SecondMe",
            },
        ])

        _, offers = db.get_negotiation_detail("neg_off")
        assert len(offers) == 2
        # Ordered by resonance_score desc
        assert offers[0].agent_name == "Alice"
        assert offers[0].resonance_score == 0.85
        assert offers[1].agent_name == "Bob"

    def test_empty_offers(self):
        db.save_negotiation(negotiation_id="neg_empty", user_id="u", demand_text="d")
        db.save_offers("neg_empty", [])
        _, offers = db.get_negotiation_detail("neg_empty")
        assert offers == []


class TestGetUserHistory:
    def test_returns_all_by_user(self):
        db.save_negotiation(negotiation_id="neg_h1", user_id="user_x", demand_text="d1")
        db.save_negotiation(negotiation_id="neg_h2", user_id="user_x", demand_text="d2")
        db.save_negotiation(negotiation_id="neg_h3", user_id="user_y", demand_text="d3")

        history = db.get_user_history("user_x")
        assert len(history) == 2
        # Ordered by created_at desc — h2 is newer
        ids = [h.negotiation_id for h in history]
        assert "neg_h1" in ids
        assert "neg_h2" in ids
        assert "neg_h3" not in ids

    def test_filters_by_scene(self):
        db.save_negotiation(negotiation_id="s1", user_id="u", demand_text="d", scene_id="hackathon")
        db.save_negotiation(negotiation_id="s2", user_id="u", demand_text="d", scene_id="recruitment")
        db.save_negotiation(negotiation_id="s3", user_id="u", demand_text="d", scene_id="hackathon")

        history = db.get_user_history("u", scene_id="hackathon")
        assert len(history) == 2
        ids = [h.negotiation_id for h in history]
        assert "s1" in ids
        assert "s3" in ids

    def test_empty_result(self):
        history = db.get_user_history("nonexistent_user")
        assert history == []


class TestGetNegotiationDetail:
    def test_returns_history_and_offers(self):
        db.save_negotiation(negotiation_id="neg_det", user_id="u", demand_text="demand")
        db.update_negotiation("neg_det", status="completed", plan_output="the plan")
        db.save_offers("neg_det", [
            {"agent_id": "a1", "agent_name": "Alice", "resonance_score": 0.9,
             "offer_text": "my offer", "agent_state": "offered"},
        ])

        history, offers = db.get_negotiation_detail("neg_det")
        assert history is not None
        assert history.plan_output == "the plan"
        assert len(offers) == 1
        assert offers[0].offer_text == "my offer"

    def test_nonexistent_returns_none(self):
        history, offers = db.get_negotiation_detail("nonexistent")
        assert history is None
        assert offers == []


class TestSaveAssistOutput:
    def test_creates_draft_record(self):
        h = db.save_assist_output(
            user_id="user_assist",
            scene_id="hackathon",
            demand_mode="surprise",
            assist_output="generated demand from SecondMe",
            raw_text="",
        )
        assert h.status == "draft"
        assert h.demand_mode == "surprise"
        assert h.assist_output == "generated demand from SecondMe"
        assert h.user_id == "user_assist"
        assert h.negotiation_id.startswith("assist_")

    def test_polish_mode_with_raw_text(self):
        h = db.save_assist_output(
            user_id="user_p",
            scene_id="network",
            demand_mode="polish",
            assist_output="polished text",
            raw_text="original rough text",
        )
        assert h.demand_text == "original rough text"
        assert h.assist_output == "polished text"


class TestToDict:
    def test_negotiation_to_dict(self):
        h = db.save_negotiation(
            negotiation_id="neg_dict",
            user_id="u",
            demand_text="test demand",
            scene_id="hack",
        )
        d = h.to_dict()
        assert d["negotiation_id"] == "neg_dict"
        assert d["demand_text"] == "test demand"
        assert "created_at" in d
        assert "updated_at" in d

    def test_offer_to_dict(self):
        db.save_negotiation(negotiation_id="neg_od", user_id="u", demand_text="d")
        db.save_offers("neg_od", [
            {"agent_id": "a1", "agent_name": "Alice", "resonance_score": 0.8,
             "offer_text": "my offer", "agent_state": "offered", "source": "Claude"},
        ])
        _, offers = db.get_negotiation_detail("neg_od")
        d = offers[0].to_dict()
        assert d["agent_name"] == "Alice"
        assert d["resonance_score"] == 0.8
        assert d["source"] == "Claude"
