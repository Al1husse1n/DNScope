"""LangGraph workflow for orchestrating domain threat investigations.

Parallelism mechanism:
This workflow uses LangGraph's standard multi-edge fan-out pattern from the `fan_out`
node to `dns`, `registration`, and `reputation`. LangGraph executes all outgoing targets
from a single step in parallel via asyncio concurrency, joining the results at the
`supervisor` node. (Tested and verified with LangGraph 1.2.24).
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from dnscope.agents.dns import DNSAgent
from dnscope.agents.registration import RegistrationAgent
from dnscope.agents.reputation import ReputationAgent
from dnscope.graph.state import GraphState
from dnscope.schemas.common import AgentStatus
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.supervisor.agent import SupervisorAgent
from dnscope.validation import validate_domain


def build_investigation_graph(
    dns_agent: DNSAgent | None = None,
    registration_agent: RegistrationAgent | None = None,
    reputation_agent: ReputationAgent | None = None,
    supervisor: SupervisorAgent | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Build and compile a new investigation graph instance.

    Node responsibilities:
      - "validate": call validate_domain(state["domain"]). On success, set
        normalized_domain. On failure, returns normalized_domain="" and
        assessment=None; conditional edge routes directly to END.
      - "fan_out": passthrough anchor for LangGraph's multi-edge parallel dispatch.
      - "dns", "registration", "reputation": invoke respective agents with defense-in-depth
        exception handling, falling back to *Finding(status=ERROR, errors=[repr(exc)]).
      - "supervisor": calls supervisor.assess(...) with the collected findings.

    Graph edges:
      START -> validate
      validate -> fan_out (if valid) or END (if invalid)
      fan_out -> dns, fan_out -> registration, fan_out -> reputation (parallel)
      dns, registration, reputation -> supervisor (join)
      supervisor -> END
    """
    active_dns = dns_agent or DNSAgent()
    active_reg = registration_agent or RegistrationAgent()
    active_rep = reputation_agent or ReputationAgent()
    active_sup = supervisor or SupervisorAgent()

    builder: StateGraph[GraphState, Any, Any, Any] = StateGraph(GraphState)

    def validate_node(state: GraphState) -> dict[str, Any]:
        raw = state.get("domain", "")
        try:
            validated = validate_domain(raw)
            return {"normalized_domain": validated.normalized}
        except Exception:
            return {"normalized_domain": "", "assessment": None}

    def route_after_validate(state: GraphState) -> str:
        if not state.get("normalized_domain"):
            return END
        return "fan_out"

    def fan_out_node(state: GraphState) -> dict[str, Any]:
        return {}

    async def dns_node(state: GraphState) -> dict[str, Any]:
        norm = state.get("normalized_domain", "")
        try:
            finding = await active_dns.investigate(norm)
            return {"dns": finding}
        except Exception as exc:
            return {
                "dns": DNSFinding(
                    status=AgentStatus.ERROR,
                    errors=[repr(exc)],
                )
            }

    async def registration_node(state: GraphState) -> dict[str, Any]:
        norm = state.get("normalized_domain", "")
        try:
            finding = await active_reg.investigate(norm)
            return {"registration": finding}
        except Exception as exc:
            return {
                "registration": RegistrationFinding(
                    status=AgentStatus.ERROR,
                    errors=[repr(exc)],
                )
            }

    async def reputation_node(state: GraphState) -> dict[str, Any]:
        norm = state.get("normalized_domain", "")
        try:
            finding = await active_rep.investigate(norm)
            return {"reputation": finding}
        except Exception as exc:
            return {
                "reputation": ReputationFinding(
                    status=AgentStatus.ERROR,
                    errors=[repr(exc)],
                )
            }

    async def supervisor_node(state: GraphState) -> dict[str, Any]:
        domain = state.get("domain", "")
        assessment = await active_sup.assess(
            domain=domain,
            dns=state.get("dns"),
            registration=state.get("registration"),
            reputation=state.get("reputation"),
        )
        return {"assessment": assessment}

    # Add nodes
    builder.add_node("validate", validate_node)
    builder.add_node("fan_out", fan_out_node)
    builder.add_node("dns", dns_node)
    builder.add_node("registration", registration_node)
    builder.add_node("reputation", reputation_node)
    builder.add_node("supervisor", supervisor_node)

    # Add edges
    builder.add_edge(START, "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {"fan_out": "fan_out", END: END},
    )
    builder.add_edge("fan_out", "dns")
    builder.add_edge("fan_out", "registration")
    builder.add_edge("fan_out", "reputation")

    builder.add_edge("dns", "supervisor")
    builder.add_edge("registration", "supervisor")
    builder.add_edge("reputation", "supervisor")

    builder.add_edge("supervisor", END)

    return builder.compile()
