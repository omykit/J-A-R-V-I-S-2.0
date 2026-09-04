import { motion } from "framer-motion";
import {
  Grid2X2,
  Zap,
  Brain,
  Settings,
  Cpu,
  MemoryStick,
  Activity,
  Wifi,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const commands = [
  {
    label: "DASHBOARD",
    icon: Grid2X2,
  },
  {
    label: "ACTIONS",
    icon: Zap,
  },
  {
    label: "INTELLIGENCE",
    icon: Brain,
  },
  {
    label: "SETTINGS",
    icon: Settings,
  },
];

// The previous CORE LOAD / MEMORY / PROCESSING bars were hardcoded to
// 84 / 62 / 91. Two of those had no backend source at all -- there is no
// core-load or processing metric anywhere in JARVIS. They are replaced with
// the service statuses the gateway genuinely reports via GET /health, rather
// than with invented percentages.

/** Map a gateway status string to how it should read and colour in the UI. */
function presentStatus(status) {
  if (status === "ok") {
    return { label: "ONLINE", tone: "text-cyan-300", dot: "bg-cyan-400 shadow-[0_0_8px_#00cfef]" };
  }
  if (status === "unknown" || status === undefined) {
    return { label: "—", tone: "text-[#43545f]", dot: "bg-[#2a3a44]" };
  }
  if (status === "degraded") {
    return { label: "DEGRADED", tone: "text-amber-400", dot: "bg-amber-400 shadow-[0_0_8px_#ffb020]" };
  }
  // unreachable / unavailable / error
  return { label: status.toUpperCase(), tone: "text-red-400", dot: "bg-red-400 shadow-[0_0_8px_#ff3b3b]" };
}

function ServiceRow({ label, status, icon: Icon, note }) {
  const { label: statusLabel, tone, dot } = presentStatus(status);

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-[8px] tracking-[0.17em] text-[#667985]">
        <Icon size={12} strokeWidth={1.4} />
        <span>{label}</span>
      </div>

      <div className={`flex items-center gap-1.5 text-[8px] tracking-[0.12em] ${tone}`}>
        {note ? <span className="text-[7px] text-[#43545f]">{note}</span> : null}
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
        {statusLabel}
      </div>
    </div>
  );
}

export default function ControlPanel({ isOpen, onToggle, health }) {
  const isOffline = health?.overall === "offline";
  const isLoading = health?.overall === "loading";

  const panelStatusLabel = isLoading
    ? "CHECKING"
    : { online: "ONLINE", degraded: "DEGRADED", offline: "OFFLINE" }[health?.overall] ?? "UNKNOWN";

  const panelStatusTone = isLoading
    ? "text-[#3f505c]"
    : { online: "text-[#3f505c]", degraded: "text-amber-400", offline: "text-red-400" }[
        health?.overall
      ] ?? "text-[#3f505c]";

  return (
    <>
      {/* CONTROL PANEL */}
      <motion.aside
        initial={false}
        animate={{
          x: isOpen ? 0 : -300,
          opacity: isOpen ? 1 : 0,
        }}
        transition={{
          duration: 0.35,
          ease: [0.22, 1, 0.36, 1],
        }}
        className="
          absolute
          bottom-7
          left-6
          z-30
          w-[320px]
          overflow-hidden
          border
          border-cyan-400/15
          bg-[#050b13]/90
          shadow-[0_0_35px_rgba(0,207,239,0.04)]
          backdrop-blur-md
        "
      >
        {/* HEADER */}
        <div className="flex h-[52px] items-center justify-between border-b border-cyan-400/10 px-4">
          <div className="flex items-center gap-3">
            <span
              className={`h-2 w-2 rounded-full ${
                isOffline
                  ? "bg-red-400 shadow-[0_0_8px_#ff3b3b]"
                  : health?.overall === "degraded"
                  ? "bg-amber-400 shadow-[0_0_8px_#ffb020]"
                  : "bg-cyan-400 shadow-[0_0_8px_#00cfef]"
              }`}
            />

            <span className="text-[9px] tracking-[0.22em] text-cyan-300">
              JARVIS CONTROL
            </span>
          </div>

          <span className={`text-[7px] tracking-[0.16em] ${panelStatusTone}`}>
            {panelStatusLabel}
          </span>
        </div>

        {/* COMMANDS */}
        <section className="px-5 py-4">
          <div className="mb-2 text-[7px] tracking-[0.2em] text-[#43545f]">
            COMMAND
          </div>

          <div className="grid grid-cols-2 gap-2">
            {commands.map(({ label, icon: Icon }) => (
              <button
                key={label}
                type="button"
                className="
                  flex
                  h-[44px]
                  items-center
                  gap-2.5
                  rounded-sm
                  border
                  border-transparent
                  px-3
                  text-slate-500
                  transition
                  hover:border-cyan-400/20
                  hover:bg-cyan-400/[0.04]
                  hover:text-cyan-300
                "
              >
                <Icon size={14} strokeWidth={1.4} />

                <span className="text-[8px] tracking-[0.14em]">
                  {label}
                </span>
              </button>
            ))}
          </div>
        </section>

        {/* DIVIDER */}
        <div className="mx-4 border-t border-cyan-400/10" />

        {/* SYSTEM STATUS */}
        <section className="px-4 py-3">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-[9px] tracking-[0.2em] text-cyan-300">
                SYSTEM STATUS
              </div>

              <div className="mt-1 text-[7px] tracking-[0.14em] text-[#43545f]">
                {isOffline
                  ? "GATEWAY UNREACHABLE"
                  : isLoading
                  ? "CONTACTING GATEWAY"
                  : "LIVE SERVICE HEALTH"}
              </div>
            </div>
          </div>

          <div className="space-y-3.5">
            <ServiceRow
              label="MEMORY SERVICE"
              status={isOffline ? "unreachable" : health?.memory}
              icon={MemoryStick}
            />

            <ServiceRow
              label="AI SERVICE"
              status={isOffline ? "unreachable" : health?.ai}
              icon={Cpu}
            />

            <ServiceRow
              label="COMMAND SERVICE"
              status={isOffline ? "unreachable" : health?.command}
              icon={Activity}
            />

            <ServiceRow
              label="OLLAMA"
              status={isOffline ? "unreachable" : health?.ollama?.status}
              icon={Brain}
              note={!isOffline && health?.ollama?.model ? health.ollama.model : ""}
            />
          </div>
        </section>

        {/* NETWORK */}
        <div className="mx-4 border-t border-cyan-400/10" />

        <section className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2 text-[8px] tracking-[0.17em] text-[#667985]">
            <Wifi size={12} strokeWidth={1.4} />
            NETWORK
          </div>

          <div
            className={`flex items-center gap-1.5 text-[8px] tracking-[0.12em] ${
              isOffline ? "text-red-400" : isLoading ? "text-[#43545f]" : "text-cyan-300"
            }`}
          >
            {isOffline ? (
              <XCircle size={11} strokeWidth={1.5} />
            ) : (
              <CheckCircle2 size={11} strokeWidth={1.5} />
            )}
            {isOffline ? "DISCONNECTED" : isLoading ? "CHECKING" : "CONNECTED"}
          </div>
        </section>

        {/* FOOTER */}
        <div className="border-t border-cyan-400/10 px-4 py-2.5 text-[7px] tracking-[0.15em] text-[#3f505c]">
          {isOffline
            ? "JARVIS CORE • UNREACHABLE"
            : health?.overall === "degraded"
            ? "JARVIS CORE • DEGRADED"
            : health?.lastUpdated
            ? `JARVIS CORE • STABLE • ${health.lastUpdated.toLocaleTimeString()}`
            : "JARVIS CORE • STABLE"}
        </div>

        {/* CLOSE BUTTON */}
        <button
          type="button"
          onClick={onToggle}
          aria-label="Collapse JARVIS control panel"
          className="
            absolute
            right-0
            top-1/2
            flex
            h-9
            w-7
            -translate-y-1/2
            items-center
            justify-center
            border-l
            border-cyan-400/10
            bg-[#050b13]
            text-slate-500
            transition
            hover:text-cyan-300
          "
        >
          <ChevronLeft size={14} />
        </button>
      </motion.aside>

      {/* REOPEN HANDLE */}
      <motion.button
        type="button"
        onClick={onToggle}
        aria-label="Open JARVIS control panel"
        initial={false}
        animate={{
          opacity: isOpen ? 0 : 1,
        }}
        transition={{
          duration: 0.15,
        }}
        className="
          absolute
          bottom-7
          left-0
          z-30
          flex
          h-[52px]
          w-[20px]
          items-center
          justify-center
          border
          border-l-0S
          border-cyan-400/20
          bg-[#050b13]/90
          text-slate-500
          backdrop-blur-md
          transition
          hover:text-cyan-300
        "
        style={{
          pointerEvents: isOpen ? "none" : "auto",
        }}
      >
        <ChevronRight size={13} />
      </motion.button>
    </>
  );
}