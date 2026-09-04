/**
 * Session identity and owner name for gateway requests.
 *
 * DESIGN ONLY IN PHASE 2 — nothing imports this yet. It exists so Phase 3
 * can wire chat without also having to decide session semantics.
 */

const SESSION_STORAGE_KEY = "jarvis.sessionId";

/**
 * One id per browser tab session.
 *
 * sessionStorage (not localStorage) gives exactly the semantics wanted:
 *   - a page refresh keeps the same id
 *   - closing the tab ends the session
 *   - two tabs are two independent sessions
 *
 * This mirrors the Python client, which generates a uuid4 per run, so a
 * voice session and a browser session group separately in the conversations
 * table rather than interleaving.
 */
export function getSessionId() {
  try {
    const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;

    const id = crypto.randomUUID().replace(/-/g, "");
    sessionStorage.setItem(SESSION_STORAGE_KEY, id);
    return id;
  } catch {
    // Private windows and blocked site data can throw on access. A session
    // id is a nice-to-have for grouping, never a reason to break a turn, so
    // fall back to a per-page-load id.
    return crypto.randomUUID().replace(/-/g, "");
  }
}

/**
 * Owner name sent to the gateway, which uses it to personalise AI replies.
 *
 * Configured via VITE_OWNER_NAME rather than hardcoded, so the component
 * tree carries no personal data. Empty string is a valid value: the gateway
 * defaults owner_name to "" and simply skips personalisation.
 */
export function getOwnerName() {
  return import.meta.env?.VITE_OWNER_NAME ?? "";
}
