"""Sales IVR agent-building backlog (Epics E2-E7).

Only agent-building work is tracked in Azure DevOps. Platform foundation (E1)
lives in code under sales-ivr/ and is intentionally excluded.

Hierarchy: Epic -> Feature -> User Story -> Task
User Stories carry the `agent-buildable` tag and acceptance criteria so the
future ADO pipeline can pick them up via WIQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field

STORY_TAG = "agent-buildable"


@dataclass
class Story:
    ref: str  # e.g. "US-201" (kept in title for traceability)
    title: str
    description: str
    acceptance_criteria: list[str]
    tasks: list[str] = field(default_factory=list)


@dataclass
class Feature:
    ref: str
    title: str
    description: str
    stories: list[Story] = field(default_factory=list)


@dataclass
class Epic:
    ref: str
    title: str
    description: str
    features: list[Feature] = field(default_factory=list)


BACKLOG: list[Epic] = [
    Epic(
        ref="E2",
        title="Call Intake and Caller Identification",
        description="Agents that parse simulated caller input and identify/verify the caller.",
        features=[
            Feature(
                ref="F2.1",
                title="Call Intake Agent",
                description="Parse simulated speech + DTMF into a structured CallSession.",
                stories=[
                    Story(
                        ref="US-201",
                        title="Parse simulated caller input into structured session fields",
                        description="As the IVR, I want to parse simulated caller input (speech transcript + DTMF) into structured session fields.",
                        acceptance_criteria=[
                            "Extracts caller_phone, channel, language, utterances[], dtmf_digits",
                            "Handles silence and malformed input gracefully",
                            "Populates CallSession model without validation errors",
                        ],
                        tasks=[
                            "Create agents/call_intake.py CallIntakeAgent",
                            "Implement utterance and DTMF parsing",
                            "Add unit tests for intake",
                            "Add fixture coverage for malformed input",
                        ],
                    ),
                    Story(
                        ref="US-202",
                        title="Detect call-start context (new prospect vs returning vs policyholder)",
                        description="As the IVR, I want to detect call-start context so downstream agents adapt.",
                        acceptance_criteria=[
                            "Sets caller_type enum",
                            "Flags after-hours calls",
                            "Unit tests for 5 fixture variants",
                        ],
                        tasks=[
                            "Implement caller_type detection",
                            "Implement after-hours flagging using config window",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
            Feature(
                ref="F2.2",
                title="Caller Identification Agent",
                description="Identify and verify callers against the mock CRM.",
                stories=[
                    Story(
                        ref="US-203",
                        title="Identify callers by phone plus verification data",
                        description="As the IVR, I want to identify callers by phone + verification data (ZIP, last 4 SSN, policy number).",
                        acceptance_criteria=[
                            "Looks up mock CRM by phone",
                            "Returns customer_id, verified, existing_policies[]",
                            "Fails verification after 2 attempts",
                        ],
                        tasks=[
                            "Create agents/caller_id.py CallerIdentificationAgent",
                            "Implement mock CRM lookup tool",
                            "Implement verification retry logic (max 2)",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-204",
                        title="Enrich caller profile with demographics and risk geography",
                        description="As the IVR, I want caller profile enriched with demographics and risk geography.",
                        acceptance_criteria=[
                            "Populates state, age_band, household_size when available",
                            "Handles unverified new prospects",
                        ],
                        tasks=[
                            "Implement profile enrichment from CRM",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
        ],
    ),
    Epic(
        ref="E3",
        title="Intent Routing and Product Catalog",
        description="Agents that classify caller intent and recommend eligible products.",
        features=[
            Feature(
                ref="F3.1",
                title="Intent Router Agent",
                description="Classify intent and choose the next orchestrator node.",
                stories=[
                    Story(
                        ref="US-301",
                        title="Classify caller intent into supported categories",
                        description="As the IVR, I want to classify caller intent into new_quote, policy_change, claims_inquiry, billing, or speak_to_agent.",
                        acceptance_criteria=[
                            ">= 90% accuracy on 20 fixture tickets",
                            "Outputs intent, confidence, product_line_hint",
                        ],
                        tasks=[
                            "Create agents/intent_router.py IntentRouterAgent",
                            "Author few-shot classification prompt",
                            "Build accuracy eval harness over fixtures",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-302",
                        title="Select next agent path based on intent and caller type",
                        description="As the IVR, I want the router to select the next agent path based on intent and urgency/caller type.",
                        acceptance_criteria=[
                            "Returns next_node enum",
                            "Fast-path to handoff for speak_to_agent or failed verification",
                        ],
                        tasks=[
                            "Implement routing decision logic",
                            "Add unit tests for each path",
                        ],
                    ),
                ],
            ),
            Feature(
                ref="F3.2",
                title="Product Catalog and Recommendation",
                description="Index the catalog and recommend eligible products.",
                stories=[
                    Story(
                        ref="US-303",
                        title="Index local insurance product catalog for lookup",
                        description="As the IVR, I want a local insurance product catalog indexed for agent lookup.",
                        acceptance_criteria=[
                            "Catalog exposes >= 8 products (auto, home, life, renters, umbrella, etc.)",
                            "Each product has coverage tiers and eligibility rules",
                            "Lookup/index is consumable by the recommendation agent",
                        ],
                        tasks=[
                            "Build catalog index/lookup helper",
                            "Integrate with catalog loader",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-304",
                        title="Recommend products based on caller profile and needs",
                        description="As the IVR, I want product recommendations based on caller profile and stated needs.",
                        acceptance_criteria=[
                            "Returns ranked recommended_products[] with rationale",
                            "Filters by state eligibility",
                        ],
                        tasks=[
                            "Create agents/product_recommendation.py ProductRecommendationAgent",
                            "Implement ranking and rationale generation",
                            "Implement state eligibility filter",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
        ],
    ),
    Epic(
        ref="E4",
        title="Quote Generation",
        description="Agent that collects risk factors and produces preliminary quotes.",
        features=[
            Feature(
                ref="F4.1",
                title="Quote Generation Agent",
                description="Collect factors, price via the deterministic engine, and produce an IVR script.",
                stories=[
                    Story(
                        ref="US-401",
                        title="Collect risk factors via conversational prompts",
                        description="As the IVR, I want to collect risk factors via conversational prompts for the selected product.",
                        acceptance_criteria=[
                            "Gathers required fields per product (e.g. auto: vehicle year, mileage, driver age)",
                            "Tracks collected_factors{}",
                        ],
                        tasks=[
                            "Create agents/quote_generation.py QuoteGenerationAgent",
                            "Implement per-product required-factor maps",
                            "Implement factor collection loop",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-402",
                        title="Calculate preliminary premium from risk factors",
                        description="As the IVR, I want to calculate a preliminary premium quote from risk factors.",
                        acceptance_criteria=[
                            "Returns quote_amount, quote_term, coverage_summary",
                            "Uses the deterministic pricing engine in pricing/",
                        ],
                        tasks=[
                            "Integrate pricing engine",
                            "Assemble QuoteResult",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-403",
                        title="Present quote in IVR-friendly spoken format",
                        description="As the IVR, I want to present the quote in IVR-friendly spoken response format.",
                        acceptance_criteria=[
                            "Output ivr_script under 60 seconds read time",
                            "Includes monthly and annual options",
                        ],
                        tasks=[
                            "Implement IVR script generator",
                            "Add read-time length check",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
        ],
    ),
    Epic(
        ref="E5",
        title="Compliance and Objection Handling",
        description="Agents that enforce disclosures and handle sales objections.",
        features=[
            Feature(
                ref="F5.1",
                title="Compliance Disclosure Agent",
                description="Deliver state-specific disclosures and validate scripts.",
                stories=[
                    Story(
                        ref="US-501",
                        title="Deliver state-specific regulatory disclosures before quote acceptance",
                        description="As the IVR, I want to deliver state-specific regulatory disclosures before quote acceptance.",
                        acceptance_criteria=[
                            "Loads rules from compliance/disclosures/",
                            "Returns disclosures_read[]",
                            "Blocks quote acceptance if disclosures skipped",
                        ],
                        tasks=[
                            "Create agents/compliance.py ComplianceDisclosureAgent",
                            "Integrate disclosure loader",
                            "Implement acceptance-blocking logic",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-502",
                        title="Run compliance checks on generated IVR scripts",
                        description="As the IVR, I want compliance checks on generated IVR scripts.",
                        acceptance_criteria=[
                            "Returns compliance_passed, violations[]",
                            "Flags unauthorized guarantees or missing disclaimers",
                        ],
                        tasks=[
                            "Implement prohibited-phrase checker",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
            Feature(
                ref="F5.2",
                title="Objection Handling Agent",
                description="Handle price/coverage/competitor objections with a recalculation loop.",
                stories=[
                    Story(
                        ref="US-503",
                        title="Handle common sales objections",
                        description="As the IVR, I want to handle common sales objections (price, coverage, competitor).",
                        acceptance_criteria=[
                            "Returns objection_handled, response_script",
                            "Uses knowledge/objections/ corpus",
                        ],
                        tasks=[
                            "Create agents/objection_handling.py ObjectionHandlingAgent",
                            "Implement objection corpus retrieval",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-504",
                        title="Loop back to quote adjustment when appropriate",
                        description="As the IVR, I want objection handling to loop back to quote adjustment when appropriate.",
                        acceptance_criteria=[
                            "On price objection, triggers quote recalculation path",
                            "Enforces max 2 loops",
                        ],
                        tasks=[
                            "Wire recalculation loop to quote agent",
                            "Implement loop guard (max 2)",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
        ],
    ),
    Epic(
        ref="E6",
        title="Human Handoff and Session Completion",
        description="Handoff agent plus orchestration wiring and the demo harness.",
        features=[
            Feature(
                ref="F6.1",
                title="Human Handoff Agent",
                description="Warm-transfer to a licensed agent with a full session summary.",
                stories=[
                    Story(
                        ref="US-601",
                        title="Warm-transfer to a licensed agent with a structured handoff summary",
                        description="As the IVR, I want to warm-transfer to a licensed agent with a structured handoff summary.",
                        acceptance_criteria=[
                            "Produces handoff_summary, recommended_queue (sales, service, claims)",
                            "Sets priority",
                        ],
                        tasks=[
                            "Create agents/handoff.py HumanHandoffAgent",
                            "Implement summary generation",
                            "Implement queue routing",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-602",
                        title="Preserve full session context in handoff",
                        description="As the IVR, I want the handoff to preserve full session context.",
                        acceptance_criteria=[
                            "Summary includes caller profile, intent, products discussed, quote, compliance status, objections",
                        ],
                        tasks=[
                            "Implement session context serialization",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
            Feature(
                ref="F6.2",
                title="Session Orchestration and Demo Harness",
                description="Replace stub nodes with real agents and finalize the batch harness.",
                stories=[
                    Story(
                        ref="US-603",
                        title="Wire orchestrator to all 8 agents with conditional edges",
                        description="As the system, I want the LangGraph orchestrator to wire all 8 agents with conditional edges.",
                        acceptance_criteria=[
                            "Compliance fail -> objection handling",
                            "Objection price loop -> quote (max 2)",
                            "speak_to_agent -> handoff",
                            "Happy path -> quote_accepted or handoff",
                        ],
                        tasks=[
                            "Replace stub nodes with real agents",
                            "Implement conditional edges",
                            "Add end-to-end integration test",
                        ],
                    ),
                    Story(
                        ref="US-604",
                        title="Log every handoff in the session audit trail",
                        description="As the system, I want every handoff logged in IVRState.audit_trail.",
                        acceptance_criteria=[
                            "Each node appends a timestamped entry",
                            "Audit trail survives a full run",
                        ],
                        tasks=[
                            "Instrument nodes for audit logging",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-605",
                        title="Replay fixtures and output run summaries",
                        description="As a developer, I want run_batch.py to replay fixture sessions and output run summaries.",
                        acceptance_criteria=[
                            "Processes N sessions",
                            "Outputs JSON report with status, agent path, duration, quote amount",
                        ],
                        tasks=[
                            "Extend batch report with quote amount and outcome",
                            "Add tests",
                        ],
                    ),
                    Story(
                        ref="US-606",
                        title="Author 30+ synthetic call fixtures covering all categories",
                        description="As a developer, I want 30+ synthetic call fixtures covering all intent and product categories.",
                        acceptance_criteria=[
                            "Fixtures in fixtures/sessions/",
                            "Categories: new_quote_auto(8), new_quote_home(6), policy_change(6), claims(4), handoff(6)",
                        ],
                        tasks=[
                            "Author fixtures per category",
                            "Add category coverage validation",
                        ],
                    ),
                ],
            ),
        ],
    ),
    Epic(
        ref="E7",
        title="Azure DevOps Pipeline Infrastructure",
        description="Meta-agent integration layer that reads stories and writes status back to ADO.",
        features=[
            Feature(
                ref="F7.1",
                title="Azure DevOps Integration Layer",
                description="ADO REST client used by the build-pipeline agents.",
                stories=[
                    Story(
                        ref="US-701",
                        title="Authenticate and query Azure DevOps for agent-ready stories",
                        description="As the pipeline, I want to authenticate and query Azure DevOps REST API for agent-ready stories.",
                        acceptance_criteria=[
                            "WIQL fetches stories tagged agent-buildable in state Approved",
                            "Returns story + child tasks + acceptance criteria",
                        ],
                        tasks=[
                            "Implement ado/client.py REST wrapper",
                            "Implement WIQL query templates",
                            "Fetch work item with $expand=relations",
                            "Add unit tests",
                        ],
                    ),
                    Story(
                        ref="US-702",
                        title="Post implementation context and status updates back to Azure DevOps",
                        description="As the pipeline, I want to post implementation context and status updates back to Azure DevOps.",
                        acceptance_criteria=[
                            "Appends to System.History",
                            "Transitions state to Active / Closed / Blocked",
                            "Links implementation branch in a comment",
                        ],
                        tasks=[
                            "Implement History comment posting",
                            "Implement state transition helper",
                            "Add unit tests",
                        ],
                    ),
                ],
            ),
        ],
    ),
]


def counts() -> dict[str, int]:
    epics = len(BACKLOG)
    features = sum(len(e.features) for e in BACKLOG)
    stories = sum(len(f.stories) for e in BACKLOG for f in e.features)
    tasks = sum(len(s.tasks) for e in BACKLOG for f in e.features for s in f.stories)
    return {"epics": epics, "features": features, "stories": stories, "tasks": tasks}
