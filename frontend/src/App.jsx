import { useState } from "react";

import JarvisOrb from "./components/orb/JarvisOrb";
import VoiceVisualizer from "./components/orb/VoiceVisualizer";
import MicControl from "./components/controls/MicControl";

import ControlPanel from "./components/panels/ControlPanel";
import ActivityPanel from "./components/panels/ActivityPanel";
import ConversationPanel from "./components/panels/ConversationPanel";

import "./App.css";

export default function App() {
  const [jarvisState, setJarvisState] = useState("standby");
  const [micActive, setMicActive] = useState(false);

  const [controlPanelOpen, setControlPanelOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [conversationOpen, setConversationOpen] = useState(false);

  const toggleMic = () => {
    const nextState = !micActive;

    setMicActive(nextState);
    setJarvisState(nextState ? "listening" : "standby");
  };

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

        <div className="flex items-center gap-2 text-[11px] tracking-[0.24em] text-[#00cfef]">
          <span className="h-[7px] w-[7px] rounded-full bg-[#00cfef] shadow-[0_0_10px_#00cfef]" />
          SYSTEM ONLINE
        </div>
      </header>

      {/* LEFT CONTROL PANEL */}
      <ControlPanel
        isOpen={controlPanelOpen}
        onToggle={() => setControlPanelOpen(!controlPanelOpen)}
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

      {/* TEMPORARY STATE TESTER */}
      <div className="absolute bottom-6 right-6 z-30 flex gap-2">
        {["standby", "listening", "thinking", "speaking"].map(
          (state) => (
            <button
              key={state}
              type="button"
              onClick={() => setJarvisState(state)}
              className={`rounded border px-3 py-2 text-[10px] tracking-wider transition ${
                jarvisState === state
                  ? "border-cyan-400 text-cyan-300"
                  : "border-slate-700 text-slate-500"
              }`}
            >
              {state.toUpperCase()}
            </button>
          )
        )}
      </div>

      {/* RIGHT ACTIVITY PANEL */}
      <ActivityPanel
        isOpen={activityOpen}
        onToggle={() => setActivityOpen(!activityOpen)}
      />

      {/* CONVERSATION PANEL */}
      <ConversationPanel
        isOpen={conversationOpen}
        onToggle={() => setConversationOpen(!conversationOpen)}
      />
    </div>
  );
}