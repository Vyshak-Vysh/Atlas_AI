import { describe, expect, it } from "vitest";

import {
  AGENT_STATE_LABELS,
  AGENT_STEP_ORDER,
  TASK_PRIORITIES,
  TASK_STATUS_COLUMNS,
  actionStatusDisplay,
  agentRunStatusDisplay,
  findingStatusDisplay,
  requirementStatusDisplay,
  taskPriorityDisplay,
  taskStatusDisplay,
} from "./status";

// These maps are the seam between backend enums and what a user actually
// reads on screen. When someone adds a status server-side and forgets the
// mapping, nothing throws — the badge just renders a raw enum string like
// DELIVERED_VERIFIED at the user. These tests make that failure loud, and
// pin the fallback behaviour so an unmapped value degrades predictably
// instead of rendering "undefined".

describe("finding status display", () => {
  it("maps every status the agent can produce", () => {
    // Mirrors FindingStatus in packages/domain/src/atlasai_domain/enums.py.
    const backendStatuses = [
      "IN_SCOPE_SUPPORTED",
      "OUT_OF_SCOPE_SUPPORTED",
      "CONFLICTING",
      "AMBIGUOUS",
      "NOT_VERIFIED",
      "DELIVERED_VERIFIED",
      "PARTIAL",
      "SUPERSEDED",
      "PENDING_APPROVAL",
    ];

    for (const status of backendStatuses) {
      const display = findingStatusDisplay(status);
      expect(display.label, `${status} has no label`).toBeTruthy();
      expect(display.label).not.toBe(status);
      expect(display.className, `${status} has no badge class`).toMatch(/^status-/);
    }
  });

  it("degrades gracefully for a status it has never seen", () => {
    const display = findingStatusDisplay("SOME_FUTURE_STATUS");
    expect(display.label).toBeTruthy();
    expect(display.className).toBeTruthy();
  });

  it("gives NOT_VERIFIED its own visual treatment", () => {
    // NOT_VERIFIED is the answer the product returns instead of guessing,
    // so it must never look like a supported positive result.
    expect(findingStatusDisplay("NOT_VERIFIED").className).not.toBe(
      findingStatusDisplay("IN_SCOPE_SUPPORTED").className,
    );
  });

  it("distinguishes in-scope from out-of-scope", () => {
    expect(findingStatusDisplay("IN_SCOPE_SUPPORTED").className).not.toBe(
      findingStatusDisplay("OUT_OF_SCOPE_SUPPORTED").className,
    );
  });
});

describe("requirement and action status display", () => {
  it("maps the requirement lifecycle", () => {
    for (const status of ["PROPOSED", "APPROVED", "IN_PROGRESS", "DELIVERED_VERIFIED", "SUPERSEDED", "REJECTED"]) {
      expect(requirementStatusDisplay(status).label).toBeTruthy();
    }
  });

  it("maps the approval lifecycle including terminal failures", () => {
    for (const status of ["PROPOSED", "WAITING_APPROVAL", "APPROVED", "EXECUTED", "REJECTED", "EXPIRED", "FAILED"]) {
      expect(actionStatusDisplay(status).label).toBeTruthy();
    }
  });

  it("marks a rejected action differently from an approved one", () => {
    expect(actionStatusDisplay("REJECTED").className).not.toBe(actionStatusDisplay("APPROVED").className);
  });
});

describe("agent run status and step labels", () => {
  it("maps every run status the API can return", () => {
    for (const status of ["RECEIVED", "RUNNING", "WAITING_APPROVAL", "COMPLETED", "FAILED", "CANCELLED"]) {
      expect(agentRunStatusDisplay(status).label).toBeTruthy();
    }
  });

  it("labels every state in the agent state machine", () => {
    // Mirrors AgentState in packages/domain/src/atlasai_domain/agent/states.py.
    // INVESTIGATE is the tool-calling loop and must be visible in the
    // run timeline like any other state.
    const states = [
      "RECEIVED",
      "CLASSIFY",
      "PLAN",
      "INVESTIGATE",
      "RETRIEVE",
      "RERANK",
      "ANALYZE",
      "VERIFY",
      "FINDING",
      "ACTION_DECISION",
      "PROPOSE_ACTION",
      "WAIT_APPROVAL",
      "EXECUTE",
      "COMPLETE",
      "FAILED",
    ];
    for (const state of states) {
      expect(AGENT_STATE_LABELS[state], `${state} has no label`).toBeTruthy();
    }
  });

  it("orders steps consistently with the labels it knows", () => {
    for (const state of AGENT_STEP_ORDER) {
      expect(AGENT_STATE_LABELS[state], `${state} is ordered but unlabelled`).toBeTruthy();
    }
    expect(new Set(AGENT_STEP_ORDER).size).toBe(AGENT_STEP_ORDER.length);
  });
});

describe("task board", () => {
  it("exposes unique column values with labels", () => {
    const values = TASK_STATUS_COLUMNS.map((column) => column.value);
    expect(new Set(values).size).toBe(values.length);
    for (const column of TASK_STATUS_COLUMNS) {
      expect(column.label).toBeTruthy();
      expect(taskStatusDisplay(column.value).label).toBeTruthy();
    }
  });

  it("maps every priority to a distinct-enough variant", () => {
    for (const priority of TASK_PRIORITIES) {
      const display = taskPriorityDisplay(priority);
      expect(display.label).toBeTruthy();
      expect(["danger", "warning", "info", "neutral"]).toContain(display.variant);
    }
    expect(taskPriorityDisplay("URGENT").variant).not.toBe(taskPriorityDisplay("LOW").variant);
  });
});
