"""QuoteGenerationAgent — LLM agent that collects factors and calls pricing tool."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from sales_ivr.agents.context import session_snapshot
from sales_ivr.llm import run_structured_agent
from sales_ivr.models import AgentHandoff, IVRResponse, IVRState, QuoteResult
from sales_ivr.models.enums import OrchestratorNode, ProductLine


class QuoteAgentResult(BaseModel):
    product_id: str
    product_line: ProductLine
    tier_id: str
    quote_amount_monthly: float
    quote_amount_annual: float
    coverage_summary: str
    ivr_script: str
    collected_factors: dict[str, float] = Field(default_factory=dict)
    route_to_handoff: bool = False
    notes: str = ""


SYSTEM = """You are QuoteGenerationAgent for an insurance sales IVR.
1) Use list_products to inspect the selected product and its tiers.
2) Infer risk factors from utterances (vehicle year, mileage, age, etc.).
3) If recalculate_quote is true, choose a cheaper/basic tier and slightly lower multipliers.
4) Call calculate_premium with product_id, tier_id, and factors.
5) Write an IVR-friendly spoken script under ~60 seconds, including monthly and annual amounts,
   and a non-binding disclaimer.
Return JSON with the calculated amounts and script. Do not invent premiums — use calculate_premium.
"""


def quote_generation(state: IVRState) -> IVRState:
    session = state.session
    result = run_structured_agent(
        agent_name="QuoteGenerationAgent",
        system_prompt=SYSTEM,
        user_payload=session_snapshot(state),
        output_model=QuoteAgentResult,
        state=state,
        enable_tools=True,
        use_capable_model=True,
    )

    if result.route_to_handoff:
        state.route_to_handoff = True
        state.append_audit(
            OrchestratorNode.QUOTE_GENERATION,
            "failed",
            result.notes or "quote failed",
        )
        state.handoffs.append(
            AgentHandoff(
                from_node=OrchestratorNode.QUOTE_GENERATION,
                to_node=OrchestratorNode.HANDOFF,
                reason="quote_failed",
            )
        )
        return state

    session.selected_product_id = result.product_id
    session.quote = QuoteResult(
        product_id=result.product_id,
        product_line=result.product_line,
        quote_amount_monthly=result.quote_amount_monthly,
        quote_amount_annual=result.quote_amount_annual,
        coverage_summary=result.coverage_summary,
        ivr_script=result.ivr_script,
        collected_factors=result.collected_factors,
    )
    state.recalculate_quote = False
    session.ivr_responses.append(
        IVRResponse(
            text=result.ivr_script,
            node=OrchestratorNode.QUOTE_GENERATION,
            prompt_type="quote",
        )
    )
    state.append_audit(
        OrchestratorNode.QUOTE_GENERATION,
        "success",
        result.notes
        or f"Quote ${result.quote_amount_monthly:.2f}/mo for {result.product_id}",
        monthly=result.quote_amount_monthly,
        annual=result.quote_amount_annual,
    )
    state.handoffs.append(
        AgentHandoff(
            from_node=OrchestratorNode.QUOTE_GENERATION,
            to_node=OrchestratorNode.COMPLIANCE,
            reason="quote_ready",
        )
    )
    return state
