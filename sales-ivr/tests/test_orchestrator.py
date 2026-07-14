from pathlib import Path

from sales_ivr.fixtures.loader import build_initial_state, list_fixtures, load_session_fixture
from sales_ivr.llm import reset_llm_client
from sales_ivr.models import IVRState
from sales_ivr.models.enums import SessionStatus
from sales_ivr.orchestrator import compile_graph, run_session
from sales_ivr.runtime import clear_resource_cache


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "sales_ivr" / "fixtures" / "sessions"


def _coerce(result: IVRState | dict) -> IVRState:
    if isinstance(result, IVRState):
        return result
    return IVRState.model_validate(result)


def _run(name: str) -> IVRState:
    clear_resource_cache()
    reset_llm_client()
    fixture = _fixtures_dir() / name
    return _coerce(run_session(build_initial_state(load_session_fixture(fixture))))


def test_graph_compiles():
    assert compile_graph() is not None


def test_auto_quote_happy_path():
    result = _run("auto_quote_ca.json")
    assert result.session.status == SessionStatus.QUOTE_ACCEPTED
    assert result.session.intent.value == "new_quote"
    assert result.session.quote is not None
    assert result.session.quote.quote_amount_monthly > 0
    assert result.session.compliance is not None
    assert result.session.compliance.compliance_passed is True
    assert len(result.llm_usage) >= 1
    nodes = [e.node.value for e in result.audit_trail]
    assert "call_intake" in nodes
    assert "quote_generation" in nodes
    assert "compliance" in nodes


def test_handoff_fixture_routes_to_handoff_node():
    result = _run("speak_to_agent_tx.json")
    assert result.session.status == SessionStatus.HANDOFF
    assert result.session.handoff is not None
    nodes = [e.node.value for e in result.audit_trail]
    assert "handoff" in nodes
    assert "product_recommendation" not in nodes


def test_claims_routes_to_claims_queue():
    result = _run("claims_tx.json")
    assert result.session.status == SessionStatus.HANDOFF
    assert result.session.handoff.recommended_queue.value == "claims"


def test_price_objection_recalculates_or_handoffs():
    result = _run("auto_price_objection_ca.json")
    assert result.objection_loop_count >= 1 or result.session.status == SessionStatus.HANDOFF
    assert result.session.quote is not None


def test_verification_failure_handoff():
    result = _run("verification_fail_ca.json")
    assert result.session.status == SessionStatus.HANDOFF
    assert result.verification_failed is True


def test_list_fixtures():
    fixtures = list_fixtures(_fixtures_dir())
    assert len(fixtures) >= 8
