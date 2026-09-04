/**
 * JARVIS Gateway API client.
 *
 * The single place in the frontend that knows how to talk to the gateway.
 * Nothing else should call fetch against :8080 directly.
 *
 * This deliberately mirrors client/api_client.py so both clients speak the
 * same contract: same request fields, same response fields, and failures
 * reported as a populated `error` string rather than a thrown exception. The
 * Python voice client and this browser client are peers against one gateway.
 *
 * Endpoints implemented here are only the two needed next:
 *   GET  /health
 *   POST /chat
 */

/**
 * Base URL for the gateway.
 *
 * The gateway's CORS allow-list (services/gateway/gateway/config.py) permits
 * localhost:3000, so the dev server is pinned to that port in vite.config.js.
 * Override with VITE_GATEWAY_URL if the gateway ever moves.
 */
export const GATEWAY_URL = (
  import.meta.env?.VITE_GATEWAY_URL ?? "http://localhost:8080"
).replace(/\/+$/, "");

/**
 * Timeouts, in milliseconds.
 *
 * These sit at the outer edge of the existing timeout ladder, which the
 * backend enforces with a test (services/ai/tests/test_timeout_budget.py):
 *
 *     AI total 25s  <  gateway 35s  <  client 45s
 *
 * Every layer outward must be strictly larger, or the outer one discards an
 * answer the inner one was still producing. 45s matches what the Python
 * client already uses, so both clients wait the same amount.
 */
const CHAT_TIMEOUT_MS = 45_000;
const HEALTH_TIMEOUT_MS = 5_000;

/**
 * @typedef {Object} GatewayResponse
 * @property {string}  source        "command" | "ai" | "fallback"
 * @property {string}  spoken_text   what JARVIS says
 * @property {string}  full_text     unabridged text; may differ from spoken
 * @property {?string} action        "launch" | "file_op" | "music" | null
 * @property {?string} action_target target of that action
 * @property {?Object} action_data   payload for that action
 * @property {?string} focus_text    short status line, e.g. "Timezone: Asia/Tokyo"
 * @property {?string} model_used    set on AI turns, e.g. "jarvis"
 * @property {string}  error         "" on success; a reason on failure
 */

/** Shape returned when a request could not complete. */
function failedResponse(error) {
  return {
    source: "fallback",
    spoken_text: "",
    full_text: "",
    action: null,
    action_target: null,
    action_data: null,
    focus_text: null,
    model_used: null,
    error,
  };
}

/** Normalise a thrown fetch/abort error into a readable reason. */
function describeError(error, timeoutMs) {
  if (error?.name === "AbortError") {
    return `Request timed out after ${timeoutMs / 1000}s`;
  }
  // A CORS rejection or a dead gateway both surface as an opaque TypeError.
  if (error instanceof TypeError) {
    return `Cannot reach the gateway at ${GATEWAY_URL}`;
  }
  return String(error?.message ?? error);
}

/** fetch with a timeout, since fetch has no native one. */
async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * GET /health — status of the gateway and every service behind it.
 *
 * Mirrors check_gateway_health() in client/api_client.py: on failure it
 * returns status "unreachable" with a detail string rather than throwing, so
 * a health poll can never crash the UI.
 *
 * @returns {Promise<{status: string, services?: Object, detail?: string}>}
 */
export async function getHealth() {
  try {
    const response = await fetchWithTimeout(
      `${GATEWAY_URL}/health`,
      { headers: { Accept: "application/json" } },
      HEALTH_TIMEOUT_MS,
    );

    if (!response.ok) {
      return { status: "unreachable", detail: `HTTP ${response.status}` };
    }
    return await response.json();
  } catch (error) {
    return { status: "unreachable", detail: describeError(error, HEALTH_TIMEOUT_MS) };
  }
}

/**
 * POST /chat — send one turn and get JARVIS's reply.
 *
 * The request body matches GatewayRequest in services/gateway/gateway/main.py.
 * Only `text` is required; the rest carry the gateway's own defaults so the
 * body is always complete and explicit.
 *
 * Note the gateway returns HTTP 200 even when a turn fails internally, with
 * source "fallback" and an apology in spoken_text. So a caller must check
 * `source`, not just the absence of `error`.
 *
 * @param {string} text
 * @param {Object} [options]
 * @param {Array<{role: string, content: string}>} [options.chatHistory]
 * @param {string} [options.selectedAction]
 * @param {string} [options.lastAction]
 * @param {string} [options.ownerName]
 * @param {string} [options.sessionId]
 * @returns {Promise<GatewayResponse>}
 */
export async function sendChat(text, options = {}) {
  const {
    chatHistory = [],
    selectedAction = "chrome",
    lastAction = "chrome",
    ownerName = "",
    sessionId = "",
  } = options;

  const body = JSON.stringify({
    text,
    chat_history: chatHistory,
    selected_action: selectedAction,
    last_action: lastAction,
    owner_name: ownerName,
    session_id: sessionId,
  });

  try {
    const response = await fetchWithTimeout(
      `${GATEWAY_URL}/chat`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body,
      },
      CHAT_TIMEOUT_MS,
    );

    if (!response.ok) {
      return failedResponse(`HTTP ${response.status}`);
    }

    const data = await response.json();

    // Read only the fields the gateway actually returns. Absent optionals are
    // null rather than undefined, so consumers can rely on the key existing.
    return {
      source: data.source ?? "fallback",
      spoken_text: data.spoken_text ?? "",
      full_text: data.full_text ?? "",
      action: data.action ?? null,
      action_target: data.action_target ?? null,
      action_data: data.action_data ?? null,
      focus_text: data.focus_text ?? null,
      model_used: data.model_used ?? null,
      error: "",
    };
  } catch (error) {
    return failedResponse(describeError(error, CHAT_TIMEOUT_MS));
  }
}
