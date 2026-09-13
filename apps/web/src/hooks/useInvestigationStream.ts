"use client";

import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { loadSession } from "@/lib/auth-storage";
import type { AgentStepEvent } from "@/lib/types";

interface StreamState {
  steps: AgentStepEvent[];
  connected: boolean;
  done: boolean;
  failed: boolean;
}

/** Live agent-run progress via SSE (GET /api/v1/agent/runs/{id}/events).
 * The endpoint requires a Bearer header, which the browser's native
 * EventSource cannot send — this uses fetch-event-source instead, which
 * streams a normal authenticated fetch() and replays from step 0 on
 * connect (the backend's `Last-Event-ID` catch-up behavior), so a
 * reconnect after a tab sleep/network blip resumes rather than skipping
 * steps that already happened. */
export function useInvestigationStream(runId: string | undefined, projectId: string | undefined) {
  const [state, setState] = useState<StreamState>({ steps: [], connected: false, done: false, failed: false });
  const lastStepRef = useRef(0);

  const reset = useCallback(() => {
    lastStepRef.current = 0;
    setState({ steps: [], connected: false, done: false, failed: false });
  }, []);

  useEffect(() => {
    if (!runId || !projectId) return;
    const controller = new AbortController();
    lastStepRef.current = 0;
    setState({ steps: [], connected: false, done: false, failed: false });

    fetchEventSource(api.agentRunEventsUrl(runId, projectId), {
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${loadSession()?.accessToken ?? ""}`,
      },
      async onopen(response) {
        if (response.ok) {
          setState((s) => ({ ...s, connected: true }));
          return;
        }
        throw new Error(`unexpected status ${response.status}`);
      },
      onmessage(event) {
        if (event.event === "heartbeat") return;
        if (!event.data) return;
        try {
          const payload = JSON.parse(event.data) as AgentStepEvent;
          lastStepRef.current = payload.step_no;
          setState((s) => ({
            ...s,
            steps: [...s.steps.filter((step) => step.step_no !== payload.step_no), payload].sort(
              (a, b) => a.step_no - b.step_no,
            ),
            done: payload.state_name === "COMPLETE",
            failed: payload.status === "FAILED",
          }));
        } catch {
          // malformed event — ignore rather than crash the stream handler
        }
      },
      onerror(err) {
        setState((s) => ({ ...s, connected: false }));
        // Throwing stops fetch-event-source from retrying forever once the
        // run has already reached a terminal state client-side.
        if (state.done || state.failed) throw err;
      },
      openWhenHidden: true,
    }).catch(() => {
      setState((s) => ({ ...s, connected: false }));
    });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, projectId]);

  return { ...state, reset };
}
