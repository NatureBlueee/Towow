"""
End-to-end tests for ToWow system.

T10 E2E Test Suite:
- test_full_negotiation.py - Complete negotiation flow tests (AC-1, AC-2)
- test_force_finalize.py - Force finalization scenario tests (AC-3)
- test_threshold_decision.py - Three-tier threshold decision tests (AC-4)
- test_sse_events.py - SSE event sequence tests (AC-5, AC-6)
- test_recovery.py - State recovery mechanism tests
- test_circuit_breaker_e2e.py - Circuit breaker integration tests (AC-7)

Run all E2E tests:
    pytest tests/e2e -v -m e2e

Run specific test file:
    pytest tests/e2e/test_full_negotiation.py -v
"""
