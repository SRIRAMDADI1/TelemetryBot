"""Deterministic mock LLM responses so tests run without Azure credentials."""

from __future__ import annotations

import json
from typing import Any

from sales_ivr.llm.client import ChatMessage, LLMResult, LLMUsage
from sales_ivr.llm.tools import run_tool
from sales_ivr.models.enums import CallerType, Intent, ProductLine


def _extract_payload(messages: list[ChatMessage]) -> dict[str, Any]:
    for msg in reversed(messages):
        if msg.role == "user" and msg.content and "Session context (JSON):" in msg.content:
            marker = "Session context (JSON):\n"
            idx = msg.content.find(marker)
            if idx < 0:
                continue
            blob = msg.content[idx + len(marker) :]
            try:
                payload, _ = json.JSONDecoder().raw_decode(blob)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                continue
    return {}


def _usage(agent_name: str) -> LLMUsage:
    return LLMUsage(
        agent_name=agent_name,
        model="mock-gpt",
        prompt_tokens=50,
        completion_tokens=40,
        total_tokens=90,
        latency_ms=5,
    )


def default_mock_responder(
    *,
    agent_name: str,
    messages: list[ChatMessage],
    tools: list[dict[str, Any]] | None = None,
    response_format: dict[str, Any] | None = None,
    model: str | None = None,
) -> LLMResult:
    payload = _extract_payload(messages)
    utterances = " ".join(u.get("text", "") for u in payload.get("utterances", []))
    lower = utterances.lower()
    phone = payload.get("caller_phone", "")
    profile = payload.get("caller_profile") or {}
    dtmf = payload.get("dtmf_digits", "")

    if agent_name == "CallIntakeAgent":
        ctype = CallerType.NEW_PROSPECT.value
        if "policy" in lower:
            ctype = CallerType.POLICYHOLDER.value
        body = {
            "caller_type": ctype,
            "after_hours": False,
            "ivr_message": "Thanks for calling. Let me pull up your information.",
            "notes": "mock intake",
        }
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    if agent_name == "CallerIdentificationAgent":
        # May request tool first if no tool results yet
        has_tool = any(m.role == "tool" for m in messages)
        if tools and not has_tool:
            return LLMResult(
                content=None,
                tool_calls=[
                    {
                        "id": "call_crm",
                        "type": "function",
                        "function": {
                            "name": "lookup_crm",
                            "arguments": json.dumps({"phone": phone}),
                        },
                    }
                ],
                usage=_usage(agent_name),
                finish_reason="tool_calls",
            )
        crm_raw = run_tool("lookup_crm", json.dumps({"phone": phone}))
        crm = json.loads(crm_raw)
        if crm.get("found") is False or "customer_id" not in crm:
            body = {
                "verified": False,
                "verification_failed": False,
                "customer_id": None,
                "caller_type": CallerType.NEW_PROSPECT.value,
                "state": profile.get("state"),
                "zip_code": profile.get("zip_code"),
                "age_band": None,
                "household_size": profile.get("household_size"),
                "policies": [],
                "ivr_message": "I don't see an existing account.",
                "notes": "new prospect",
            }
        else:
            zip_ok = not profile.get("zip_code") or profile.get("zip_code") == crm.get("zip_code")
            if not zip_ok:
                body = {
                    "verified": False,
                    "verification_failed": True,
                    "customer_id": crm.get("customer_id"),
                    "caller_type": CallerType.UNKNOWN.value,
                    "state": crm.get("state"),
                    "zip_code": profile.get("zip_code"),
                    "policies": [],
                    "ivr_message": "I was unable to verify your account.",
                    "notes": "zip mismatch",
                }
            else:
                policies = crm.get("policies") or []
                body = {
                    "verified": True,
                    "verification_failed": False,
                    "customer_id": crm["customer_id"],
                    "caller_type": (
                        CallerType.POLICYHOLDER.value
                        if policies
                        else CallerType.RETURNING_CUSTOMER.value
                    ),
                    "state": crm.get("state"),
                    "zip_code": crm.get("zip_code"),
                    "age_band": crm.get("age_band"),
                    "household_size": crm.get("household_size"),
                    "policies": policies,
                    "ivr_message": f"Welcome back. Account {crm['customer_id']}.",
                    "notes": "verified",
                }
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    if agent_name == "IntentRouterAgent":
        if payload.get("verification_failed") or dtmf == "0":
            intent = Intent.SPEAK_TO_AGENT.value if dtmf == "0" else Intent.UNKNOWN.value
            if "claim" in lower:
                intent = Intent.CLAIMS_INQUIRY.value
            body = {
                "intent": Intent.SPEAK_TO_AGENT.value if dtmf == "0" else intent,
                "confidence": 0.99 if dtmf == "0" else 0.9,
                "product_line_hint": None,
                "route_to_handoff": True,
                "next_node": "handoff",
                "ivr_message": "I'll connect you with someone who can help.",
                "notes": "handoff route",
            }
            if "claim" in lower and dtmf != "0":
                body["intent"] = Intent.CLAIMS_INQUIRY.value
            if "billing" in lower or "payment" in lower:
                body["intent"] = Intent.BILLING.value
            if "change" in lower and "policy" in lower:
                body["intent"] = Intent.POLICY_CHANGE.value
            if payload.get("verification_failed"):
                body["intent"] = Intent.UNKNOWN.value
            return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

        hint = None
        for line in ProductLine:
            if line.value in lower or (line.value == "home" and "homeowner" in lower):
                hint = line.value
                break
        if "auto" in lower or "sedan" in lower or "suv" in lower:
            hint = ProductLine.AUTO.value
        if "renters" in lower:
            hint = ProductLine.RENTERS.value
        if "life" in lower:
            hint = ProductLine.LIFE.value

        body = {
            "intent": Intent.NEW_QUOTE.value,
            "confidence": 0.9,
            "product_line_hint": hint,
            "route_to_handoff": False,
            "next_node": "product_recommendation",
            "ivr_message": "I can help you with a quote.",
            "notes": "sales path",
        }
        if "claim" in lower:
            body.update(
                {
                    "intent": Intent.CLAIMS_INQUIRY.value,
                    "route_to_handoff": True,
                    "next_node": "handoff",
                }
            )
        if "billing" in lower or "payment" in lower:
            body.update(
                {
                    "intent": Intent.BILLING.value,
                    "route_to_handoff": True,
                    "next_node": "handoff",
                }
            )
        if "change" in lower and "policy" in lower:
            body.update(
                {
                    "intent": Intent.POLICY_CHANGE.value,
                    "route_to_handoff": True,
                    "next_node": "handoff",
                }
            )
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    if agent_name == "ProductRecommendationAgent":
        has_tool = any(m.role == "tool" for m in messages)
        state_code = profile.get("state") or "CA"
        hint = payload.get("product_line_hint")
        if tools and not has_tool:
            args = {"state": state_code}
            if hint:
                args["product_line"] = hint
            return LLMResult(
                content=None,
                tool_calls=[
                    {
                        "id": "call_list",
                        "type": "function",
                        "function": {
                            "name": "list_products",
                            "arguments": json.dumps(args),
                        },
                    }
                ],
                usage=_usage(agent_name),
                finish_reason="tool_calls",
            )
        products = json.loads(
            run_tool(
                "list_products",
                json.dumps({"state": state_code, **({"product_line": hint} if hint else {})}),
            )
        )
        if not products:
            body = {
                "recommended_products": [],
                "selected_product_id": None,
                "route_to_handoff": True,
                "ivr_message": "No eligible products.",
                "notes": "none",
            }
        else:
            top = products[0]
            body = {
                "recommended_products": [
                    {
                        "product_id": top["product_id"],
                        "product_line": top["product_line"],
                        "name": top["name"],
                        "score": 0.95,
                        "rationale": f"Matches needs in {state_code}",
                    }
                ],
                "selected_product_id": top["product_id"],
                "route_to_handoff": False,
                "ivr_message": f"I recommend {top['name']}.",
                "notes": "selected",
            }
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    if agent_name == "QuoteGenerationAgent":
        has_calc = any(
            m.role == "tool" and m.name == "calculate_premium" for m in messages
        )
        product_id = payload.get("selected_product_id") or "auto-personal"
        # Infer product from recommendations if needed
        recs = payload.get("recommended_products") or []
        if recs and not payload.get("selected_product_id"):
            product_id = recs[0].get("product_id", product_id)
        line = ProductLine.AUTO.value
        for rec in recs:
            if rec.get("product_id") == product_id:
                line = rec.get("product_line", line)
        if "home" in product_id:
            line = ProductLine.HOME.value
        if "life" in product_id:
            line = ProductLine.LIFE.value
        if "renters" in product_id:
            line = ProductLine.RENTERS.value

        products = json.loads(run_tool("list_products", json.dumps({})))
        product = next((p for p in products if p["product_id"] == product_id), products[0])
        tiers = product["tiers"]
        lower = bool(payload.get("recalculate_quote"))
        tier = tiers[0] if lower else (tiers[1] if len(tiers) > 1 else tiers[0])
        factors = {"driver_age": 1.0, "vehicle_year": 1.0, "annual_mileage": 1.0, "coverage_tier": 0.85 if lower else 1.0}
        if not has_calc and tools:
            return LLMResult(
                content=None,
                tool_calls=[
                    {
                        "id": "call_price",
                        "type": "function",
                        "function": {
                            "name": "calculate_premium",
                            "arguments": json.dumps(
                                {
                                    "product_id": product["product_id"],
                                    "tier_id": tier["tier_id"],
                                    "factors": factors,
                                }
                            ),
                        },
                    }
                ],
                usage=_usage(agent_name),
                finish_reason="tool_calls",
            )
        priced = json.loads(
            run_tool(
                "calculate_premium",
                json.dumps(
                    {
                        "product_id": product["product_id"],
                        "tier_id": tier["tier_id"],
                        "factors": factors,
                    }
                ),
            )
        )
        monthly = priced["quote_amount_monthly"]
        annual = priced["quote_amount_annual"]
        summary = priced["coverage_summary"]
        script = (
            f"Your estimated premium is {monthly} dollars per month or {annual} dollars annually. "
            f"{summary}. This is a preliminary estimate and not a binding offer. Would you like to proceed?"
        )
        body = {
            "product_id": product["product_id"],
            "product_line": product["product_line"],
            "tier_id": tier["tier_id"],
            "quote_amount_monthly": monthly,
            "quote_amount_annual": annual,
            "coverage_summary": summary,
            "ivr_script": script,
            "collected_factors": factors,
            "route_to_handoff": False,
            "notes": "quoted",
        }
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    if agent_name == "ComplianceDisclosureAgent":
        state_code = (profile.get("state") or "CA").upper()
        has_tool = any(m.role == "tool" for m in messages)
        if tools and not has_tool:
            return LLMResult(
                content=None,
                tool_calls=[
                    {
                        "id": "call_comp",
                        "type": "function",
                        "function": {
                            "name": "load_compliance",
                            "arguments": json.dumps({"state": state_code}),
                        },
                    }
                ],
                usage=_usage(agent_name),
                finish_reason="tool_calls",
            )
        pack = json.loads(run_tool("load_compliance", json.dumps({"state": state_code})))
        disclosures = [d["text"] for d in pack.get("disclosures", [])]
        body = {
            "disclosures_read": disclosures,
            "compliance_passed": bool(disclosures) and "error" not in pack,
            "violations": [],
            "spoken_disclosure": " Important notice: " + " ".join(disclosures),
            "route_to_handoff": "error" in pack,
            "notes": "compliance checked",
        }
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    if agent_name == "ObjectionHandlingAgent":
        accepted = any(
            k in lower for k in ("yes", "proceed", "sounds good", "i'll take it", "take it")
        )
        price = any(k in lower for k in ("too expensive", "too much", "cheaper", "can't afford"))
        max_loops = int(payload.get("max_objection_loops") or 2)
        loop = int(payload.get("objection_loop_count") or 0)
        if accepted and not price:
            body = {
                "objection_type": None,
                "quote_accepted": True,
                "recalculate_quote": False,
                "route_to_handoff": False,
                "ivr_message": "Wonderful. I've recorded your preliminary quote acceptance.",
                "notes": "accepted",
            }
        elif price and loop < max_loops:
            body = {
                "objection_type": "price",
                "quote_accepted": False,
                "recalculate_quote": True,
                "route_to_handoff": False,
                "ivr_message": "I understand. Let me check a more affordable option.",
                "notes": "price recalc",
            }
        elif price:
            body = {
                "objection_type": "price",
                "quote_accepted": False,
                "recalculate_quote": False,
                "route_to_handoff": True,
                "ivr_message": "Let me connect you to a specialist.",
                "notes": "price escalate",
            }
        else:
            body = {
                "objection_type": None,
                "quote_accepted": True,
                "recalculate_quote": False,
                "route_to_handoff": False,
                "ivr_message": "Wonderful. I've recorded your preliminary quote acceptance.",
                "notes": "no objection",
            }
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    if agent_name == "HumanHandoffAgent":
        intent = payload.get("intent", "unknown")
        queue = "service"
        if intent == "claims_inquiry" or "claim" in lower:
            queue = "claims"
        elif intent == "billing":
            queue = "billing"
        elif payload.get("quote"):
            queue = "sales"
        body = {
            "summary": (
                f"Caller {phone}; intent={intent}; "
                f"verified={profile.get('verified')}; "
                f"customer={profile.get('customer_id')}"
            ),
            "recommended_queue": queue,
            "priority": 2 if queue == "claims" else 3,
            "ivr_message": f"Please stay on the line while I connect you to our {queue} team.",
            "notes": "handoff ready",
        }
        return LLMResult(content=json.dumps(body), usage=_usage(agent_name), finish_reason="stop")

    return LLMResult(content="{}", usage=_usage(agent_name), finish_reason="stop")
