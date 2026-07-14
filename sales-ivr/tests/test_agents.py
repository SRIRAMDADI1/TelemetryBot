from pathlib import Path

from sales_ivr.agents.call_intake import call_intake
from sales_ivr.agents.intent_router import intent_router
from sales_ivr.fixtures.loader import build_initial_state, load_session_fixture
from sales_ivr.llm import reset_llm_client
from sales_ivr.models import CallSession, CallerUtterance
from sales_ivr.models.enums import Intent, ProductLine
from sales_ivr.runtime import clear_resource_cache


def test_call_intake_sets_caller_type():
    clear_resource_cache()
    reset_llm_client()
    session = CallSession(
        session_id="t1",
        caller_phone="15551234001",
        utterances=[CallerUtterance(turn=0, text="I need a quote for auto insurance")],
        dtmf_digits="1",
    )
    state = call_intake(build_initial_state(session))
    assert state.session.caller_type.value != "unknown"
    assert any(e.node.value == "call_intake" for e in state.audit_trail)
    assert any(u.agent_name == "CallIntakeAgent" for u in state.llm_usage)


def test_intent_router_classifies_new_quote():
    clear_resource_cache()
    reset_llm_client()
    session = CallSession(
        session_id="t2",
        caller_phone="15551234001",
        utterances=[CallerUtterance(turn=0, text="I'd like an auto insurance quote please")],
    )
    state = intent_router(build_initial_state(session))
    assert state.session.intent == Intent.NEW_QUOTE
    assert state.session.product_line_hint == ProductLine.AUTO
    assert state.route_to_handoff is False


def test_intent_router_speak_to_agent_dtmf():
    clear_resource_cache()
    reset_llm_client()
    session = CallSession(
        session_id="t3",
        caller_phone="15551234001",
        utterances=[CallerUtterance(turn=0, text="hello")],
        dtmf_digits="0",
    )
    state = intent_router(build_initial_state(session))
    assert state.session.intent == Intent.SPEAK_TO_AGENT
    assert state.route_to_handoff is True


def test_fixture_loads():
    path = (
        Path(__file__).resolve().parent.parent
        / "sales_ivr"
        / "fixtures"
        / "sessions"
        / "auto_quote_ca.json"
    )
    session = load_session_fixture(path)
    assert session.session_id.startswith("sess-")
