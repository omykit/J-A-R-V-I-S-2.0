import { useCallback, useEffect, useRef, useState } from "react";

import JarvisOrb from "./components/orb/JarvisOrb";
import VoiceVisualizer from "./components/orb/VoiceVisualizer";
import MicControl from "./components/controls/MicControl";

import ControlPanel from "./components/panels/ControlPanel";
import ActivityPanel from "./components/panels/ActivityPanel";
import ConversationPanel from "./components/panels/ConversationPanel";

import useSystemHealth from "./hooks/useSystemHealth";

import "./App.css";

/**
 * How long a finished reply is presented before the orb settles.
 *
 * There is no browser TTS in this phase, so "speaking" means "the response
 * has arrived and is being presented". The window scales with the length of
 * the answer -- a one-line time reply and a paragraph about RAG should not
 * hold the same beat -- but is clamped so it is never an arbitrary long
 * timer. A new request cancels it immediately.
 */
const SPEAKING_MIN_MS = 1500;
const SPEAKING_MAX_MS = 4000;
const ERROR_PRESENT_MS = 3000;
const MAX_ACTIVITY_EVENTS = 8;

function speakingDurationFor(text) {
  const estimated = (text?.length ?? 0) * 28;
  return Math.min(SPEAKING_MAX_MS, Math.max(SPEAKING_MIN_MS, estimated));
}

/** How the real health state reads in the header. */
const HEADER_STATUS = {
  loading: { label: "CONNECTING", color: "#4a5a66" },
  online: { label: "SYSTEM ONLINE", color: "#00cfef" },
  degraded: { label: "SYSTEM DEGRADED", color: "#ffb020" },
  offline: { label: "SYSTEM OFFLINE", color: "#ff3b3b" },
};

export default function App() {
  const [jarvisState, setJarvisState] = useState("standby");
  const [micActive, setMicActive] = useState(false);

  const [controlPanelOpen, setControlPanelOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [conversationOpen, setConversationOpen] = useState(false);

  // Polled once here and passed down, so the app has a single poller and a
  // single source of truth for backend health.
  const health = useSystemHealth();
  const headerStatus = HEADER_STATUS[health.overall] ?? HEADER_STATUS.loading;

  // Events shown in the ActivityPanel. Only things the browser genuinely
  // observed -- the backend emits no event stream, so nothing here is
  // invented.
  const [activityEvents, setActivityEvents] = useState([]);
  const activityId = useRef(1);

  // Pending "settle back to standby" timer. Held in a ref so a new request
  // can cancel it: starting a second message while the first is still being
  // presented must go straight to thinking, never linger on speaking.
  const settleTimer = useRef(null);
  const clearSettleTimer = () => {
    if (settleTimer.current) {
      clearTimeout(settleTimer.current);
      settleTimer.current = null;
    }
  };

  useEffect(() => clearSettleTimer, []);

  const pushActivity = useCallback((entry) => {
    setActivityEvents((current) =>
      [
        ...current,
        {
          id: activityId.current++,
          time: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          }),
          ...entry,
        },
      ].slice(-MAX_ACTIVITY_EVENTS),
    );
  }, []);

  /**
   * Translate what ConversationPanel reports into global visual state.
   *
   * App coordinates the orb and the activity feed; it never makes the
   * request itself. That stays entirely in ConversationPanel.
   */
  const handleLifecycleEvent = useCallback(
    (event) => {
      clearSettleTimer();

      if (event.type === "request") {
        setJarvisState("thinking");
        pushActivity({ kind: "request", label: "COMMAND SENT", detail: event.text });
        return;
      }

      if (event.type === "response") {
        setJarvisState("speaking");
        pushActivity({
          kind: "response",
          label:
            event.source === "ai"
              ? "AI RESPONSE"
              : event.source === "fallback"
              ? "FALLBACK RESPONSE"
              : "COMMAND RESOLVED",
          detail: event.focusText || event.text,
        });

        settleTimer.current = setTimeout(
          () => setJarvisState("standby"),
          speakingDurationFor(event.text),
        );
        return;
      }

      if (event.type === "error") {
        setJarvisState("error");
        pushActivity({ kind: "error", label: "REQUEST FAILED", detail: event.text });

        // The orb settles, but the readable error stays in the conversation.
        settleTimer.current = setTimeout(() => setJarvisState("standby"), ERROR_PRESENT_MS);
      }
    },
    [pushActivity],
  );

  // The mic button no longer drives jarvisState. React has no authoritative
  // knowledge of the Python client's Vosk listening state, so putting the
  // orb into "listening" here would be asserting something we cannot know.
  // The button still reflects its own on/off state; genuine voice state
  // arrives in a later phase.
  const toggleMic = () => setMicActive((current) => !current);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#02040a] text-[#dceef5]">

      {/* BACKGROUND GRID */}
      <div className="pointer-events-none absolute inset-0 opacity-30">
        <div
          className="h-full w-full"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0,207,239,.045) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0,207,239,.045) 1px, transparent 1px)
            `,
            backgroundSize: "64px 64px",
          }}
        />
      </div>

      {/* HEADER */}
      <header className="relative z-10 flex items-start justify-between px-9 py-7">
        <div>
          <div className="text-[19px] tracking-[0.34em] text-[#dceef5]">
            J.A.R.V.I.S
          </div>

          <div className="mt-2 text-[10px] tracking-[0.16em] text-[#4a5a66]">
            JUST A RATHER VERY INTELLIGENT SYSTEM
          </div>
        </div>

        <div
          className="flex items-center gap-2 text-[11px] tracking-[0.24em]"
          style={{ color: headerStatus.color }}
          title={health.detail || undefined}
        >
          <span
            className="h-[7px] w-[7px] rounded-full"
            style={{
              background: headerStatus.color,
              boxShadow: `0 0 10px ${headerStatus.color}`,
            }}
          />
          {headerStatus.label}
        </div>
      </header>

      {/* LEFT CONTROL PANEL */}
      <ControlPanel
        isOpen={controlPanelOpen}
        onToggle={() => setControlPanelOpen(!controlPanelOpen)}
        health={health}
      />

      {/* MAIN CENTER */}
      <main
        className="
          relative
          z-10
          flex
          h-[calc(100vh-100px)]
          flex-col
          items-center
          justify-center
          -mt-5
        "
      >
        {/* VOICE VISUALIZER */}
        <VoiceVisualizer active={micActive} />

        {/* JARVIS ORB */}
        <div className="mt-8">
          <JarvisOrb state={jarvisState} />
        </div>

        {/* MIC CONTROL */}
        <div className="relative z-20 mt-8">
          <MicControl
            isMicActive={micActive}
            onToggle={toggleMic}
            status={jarvisState.toUpperCase()}
          />
        </div>
      </main>

      {/* RIGHT ACTIVITY PANEL */}
      <ActivityPanel
        isOpen={activityOpen}
        onToggle={() => setActivityOpen(!activityOpen)}
        events={activityEvents}
      />

      {/* CONVERSATION PANEL */}
      <ConversationPanel
        isOpen={conversationOpen}
        onToggle={() => setConversationOpen(!conversationOpen)}
        onLifecycleEvent={handleLifecycleEvent}
      />
    </div>
  );
}