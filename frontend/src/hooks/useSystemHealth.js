import { useEffect, useRef, useState } from "react";

import { getHealth } from "../services/apiClient";

/**
 * Poll the gateway's /health endpoint and expose real system state.
 *
 * One hook instance owns one interval, so call it ONCE near the top of the
 * tree and pass the result down. Mounting it in several components would
 * mean several independent pollers hitting the gateway.
 *
 * Deliberately HTTP polling, not WebSocket/SSE: health is a slow-moving,
 * pull-shaped value and the gateway exposes no event stream. Ten seconds is
 * frequent enough to notice an outage during a demo without adding traffic.
 */
export const HEALTH_POLL_INTERVAL_MS = 10_000;

/** Services the UI reports on, in display order. */
const SERVICE_ORDER = ["memory", "ai", "command"];

/**
 * Overall state, derived from what the gateway actually returns.
 *
 *   offline   gateway unreachable        — never claim ONLINE here
 *   degraded  gateway up, a service down
 *   online    gateway up, all services ok
 *   loading   no response yet
 */
function deriveOverall(payload) {
  if (!payload) return "loading";
  if (payload.status === "unreachable") return "offline";

  const services = payload.services ?? {};
  const statuses = SERVICE_ORDER.map((name) => services[name]?.status);

  if (statuses.some((status) => status !== "ok")) return "degraded";
  return payload.status === "ok" ? "online" : "degraded";
}

/**
 * Ollama's availability is exactly what the AI service's health check
 * measures — services.ai IS an Ollama probe (check_ollama_health in
 * services/ai/ai_service/main.py). So this is a relabelling of real data,
 * not a second, invented signal.
 */
function deriveOllama(payload) {
  const ai = payload?.services?.ai;
  if (!ai) return { status: "unknown", detail: "", model: "", modelCount: 0 };

  return {
    status: ai.status === "ok" ? "ok" : ai.status ?? "unknown",
    detail: ai.detail ?? "",
    model: ai.model ?? "",
    modelCount: Array.isArray(ai.models) ? ai.models.length : 0,
  };
}

export default function useSystemHealth(intervalMs = HEALTH_POLL_INTERVAL_MS) {
  const [payload, setPayload] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Guards against setting state after unmount, and against a slow response
  // from a previous interval landing after a newer one.
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;

    async function poll() {
      const result = await getHealth();
      if (!isMounted.current) return;

      setPayload(result);
      setLastUpdated(new Date());
      setIsLoading(false);
    }

    poll();
    const timer = setInterval(poll, intervalMs);

    return () => {
      isMounted.current = false;
      clearInterval(timer);
    };
  }, [intervalMs]);

  const overall = isLoading && payload === null ? "loading" : deriveOverall(payload);
  const services = payload?.services ?? {};

  return {
    /** "loading" | "online" | "degraded" | "offline" */
    overall,
    isLoading,
    /** Reason string when the gateway could not be reached. */
    detail: payload?.detail ?? "",
    lastUpdated,
    /** Per-service status, straight from the gateway. */
    memory: services.memory?.status ?? "unknown",
    ai: services.ai?.status ?? "unknown",
    command: services.command?.status ?? "unknown",
    ollama: deriveOllama(payload),
    /** Untouched response, for anything that needs more than the above. */
    raw: payload,
  };
}
