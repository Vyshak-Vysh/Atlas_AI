"""Single-shot grounded-answer pipeline: evidence packet -> one structured
LLM call -> citation-reconciled, per-status-contract-validated FindingOutput.

This is deliberately NOT the full agent state machine (that's Release 3 —
apps/ai_atlas/agent_runner) — it satisfies the master spec's literal
vertical-slice acceptance script (ATLASAI_MASTER_SPEC.md §15 steps 1-10):
retrieve evidence for a question, generate a structured cited answer,
validate the citations.
"""

from __future__ import annotations

import uuid

from atlasai_domain.contracts.evidence import CitationRef, EvidenceCandidate
from atlasai_domain.contracts.findings import ContradictionEntry, FindingDraft, FindingOutput, TimelineEntry
from atlasai_llm_gateway.client import AnthropicGateway, StructuredCompletion
from atlasai_llm_gateway.framing import SYSTEM_PROMPT_V1, build_evidence_block
from atlasai_llm_gateway.schemas import CitationDraft, FindingLLMOutput


class CitationValidationError(Exception):
    """Raised when the model cites an evidence_chunk_id that was never
    part of the evidence packet it was given — i.e. a hallucinated
    citation. VERIFY-step behavior (TD_v2.md §5): this is never silently
    dropped or repaired, it fails the answer outright."""


def _resolve_citation(draft: CitationDraft, by_id: dict[uuid.UUID, EvidenceCandidate]) -> CitationRef:
    candidate = by_id.get(draft.evidence_chunk_id)
    if candidate is None:
        raise CitationValidationError(
            f"model cited evidence_chunk_id={draft.evidence_chunk_id} which is not present "
            "in the retrieved evidence packet"
        )
    return candidate.to_citation(citation_label=draft.citation_label, quote=draft.quote)


def _reconcile(llm_output: FindingLLMOutput, candidates: list[EvidenceCandidate]) -> FindingDraft:
    """Rebuilds every citation from authoritative EvidenceCandidate data
    (see schemas.py's module docstring for why), then constructs the real
    `FindingDraft` — whose own validator enforces BD_v2.md §6's
    per-status required-field contract on the reconciled result."""
    by_id = {c.evidence_chunk_id: c for c in candidates}

    citations = [_resolve_citation(c, by_id) for c in llm_output.citations]
    contradictions = [
        ContradictionEntry(
            side_a_summary=c.side_a_summary,
            side_a_citation=_resolve_citation(c.side_a_citation, by_id),
            side_b_summary=c.side_b_summary,
            side_b_citation=_resolve_citation(c.side_b_citation, by_id),
            why_it_matters=c.why_it_matters,
        )
        for c in llm_output.contradictions
    ]
    timeline = [
        TimelineEntry(
            at=t.at, label=t.label, citation=_resolve_citation(t.citation, by_id) if t.citation else None
        )
        for t in llm_output.timeline
    ]

    return FindingDraft(
        status=llm_output.status,
        summary=llm_output.summary,
        facts=llm_output.facts,
        inferences=llm_output.inferences,
        contradictions=contradictions,
        missing_evidence=llm_output.missing_evidence,
        timeline=timeline,
        citations=citations,
        confidence=llm_output.confidence,
        recommended_next_step=llm_output.recommended_next_step,
        requires_human_review=llm_output.requires_human_review,
    )


def _build_user_content(question: str, candidates: list[EvidenceCandidate]) -> str:
    evidence_block = build_evidence_block(candidates)
    return (
        f"Question: {question}\n\n"
        f"Evidence packet ({len(candidates)} chunk(s) below, each tagged with its citation_label "
        "like E1/E2 and its evidence_chunk_id):\n\n"
        f"{evidence_block if evidence_block else '(no evidence was retrieved for this question)'}\n\n"
        "For every citation you produce, set `evidence_chunk_id` to the exact evidence_chunk_id "
        "attribute of the <untrusted_evidence> tag you are citing (copy it verbatim), `citation_label` "
        "to that tag's citation_label (e.g. \"E1\"), and `quote` to the exact short excerpt from that "
        "chunk that supports your claim."
    )


async def generate_grounded_answer(
    *,
    question: str,
    project_id: uuid.UUID,
    candidates: list[EvidenceCandidate],
    model: str | None = None,
) -> tuple[FindingOutput, StructuredCompletion]:
    gateway = AnthropicGateway()
    try:
        completion = await gateway.complete_structured(
            system=SYSTEM_PROMPT_V1,
            user_content=_build_user_content(question, candidates),
            output_format=FindingLLMOutput,
            model=model or gateway.model_for_default(),
        )
        llm_output: FindingLLMOutput = completion.parsed  # type: ignore[assignment]

        draft = _reconcile(llm_output, candidates)
        finding = FindingOutput.from_draft(draft, question=question, project_id=project_id)
        return finding, completion
    finally:
        await gateway.aclose()
