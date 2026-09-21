# ADR 0009: A bounded tool-calling loop for evidence gathering

Status: accepted

## Context

The original agent runner executed a fixed sequence: `PLAN` produced the
question as a single subquery, `RETRIEVE` ran exactly one hybrid search per
subquery, and `RERANK` ordered the result. This is cheap, replayable and
easy to reason about, but it answers every question with the same single
search, which is wrong for the questions this product exists to answer.

Scope questions are rarely settled by one lookup. "Is the notification
centre in Phase 1?" is answered correctly only by finding the original
commitment *and* checking whether a later amendment changed it. A single
search ranked by relevance to the question will surface the original SOW
clause and can easily miss an amendment that never repeats the feature's
name. The fixed pipeline had no way to go and look again.

We also described the system as agentic in its own documentation while the
model had no tool access at all, which was inaccurate.

## Decision

Introduce an `INVESTIGATE` state that runs a real tool-calling loop against
the Gemini function-calling API. The model is given a closed registry of
read-only, project-scoped tools and decides which to call and with what
arguments until it stops asking or a budget is spent.

`RETRIEVE` is kept as the deterministic alternative rather than deleted.
A run selects between them via `agent_runs.model_policy.retrieval_mode`;
both transition to `RERANK`, so everything downstream is unchanged.

## Why the loop is safe to run

The objection to agent loops is that they are unbounded. This one is
bounded in four independent ways, none of which is a prompt instruction:

1. **Closed registry.** `_REGISTRY` in `apps/ai_atlas/agent_runner/tools.py`
   is the dispatch table. A name outside it is refused at dispatch and
   returned to the model as an error, never executed.
2. **Server-side scope.** No tool accepts a tenant or project argument.
   Scope comes from the run's `ToolExecutionContext`, so a prompt-injected
   instruction cannot widen it.
3. **Per-tool budget.** `max_calls_per_tool` is counted per tool name in
   `ToolExecutionContext.execute`. The call past the budget is refused with
   a message telling the model to answer with what it has.
4. **Iteration cap.** `max_iterations` is a hard `for` bound in the loop, so
   a model that never stops requesting tools simply runs out of turns.

Refusals are returned as `is_error` tool results rather than raised, so the
model can recover by trying a different query — but refusals still consume
budget, so recovery cannot buy extra turns.

## The loop is not the system of record

This is the part that preserves the product's core rule. The loop's closing
prose is **not** the answer. Its only durable output is the set of
`EvidenceCandidate` rows it accumulated in `ToolExecutionContext.collected`,
read from the database by the tools themselves. `RERANK` orders those rows
and `ANALYZE` builds the finding from them, with every citation reconciled
against authoritative data and `VERIFY` re-checking the result.

So the model chooses *what to look at*. It still never decides what is true,
and it still cannot cite a chunk that was not retrieved.

## Consequences

- Multi-hop questions (original commitment plus later amendment) become
  answerable, which is what the SUPERSEDED and CONFLICTING evaluation
  categories test.
- Cost and latency rise: several model turns per run instead of one. The
  `deterministic` mode exists for cost-sensitive traffic, and the evaluation
  harness can measure whether the loop earns its cost per category.
- The run transcript is richer. Each tool call is its own `agent_steps` row,
  so a reviewer sees exactly what the agent searched for and what came back,
  rather than one opaque retrieval step.
- `AgentState` gained a member, so the frontend's state labels and step
  ordering had to learn `INVESTIGATE`. Both paths appear in
  `AGENT_STEP_ORDER` and the timeline skips whichever the run did not take.

## Alternatives considered

**Keep the fixed pipeline and add more hardcoded searches.** We would be
guessing at query decomposition in code. It handles the cases we thought of
and nothing else, and every new question shape is a code change.

**Use the SDK's tool runner helper.** It would remove the loop code, but the
budget enforcement, per-call checkpointing and project scoping are the parts
that matter here, and all of them live in the executor we would still have
to write. Owning the loop is about thirty lines and makes the bounds
explicit and testable.

**Let the model write its own retrieval query as structured output, then run
it.** A half-measure: it gets query rewriting without multi-hop, and it still
cannot decide to look a second time after seeing the first result.
