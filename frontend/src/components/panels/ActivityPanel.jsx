import { motion } from "framer-motion";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Circle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

// The previous static list (SYSTEM READY / VOICE ENGINE / ...) was invented:
// the backend emits no event stream, so nothing could have produced it. The
// panel now shows only events the browser actually observed -- a request it
// sent, a response it received, a failure it hit.

/** Icon and colour per event kind. */
function eventStyle(kind) {
  if (kind === "request") {
    return { tone: "text-slate-400", icon: Circle, iconClass: "text-cyan-400" };
  }
  if (kind === "error") {
    return { tone: "text-red-300", icon: AlertCircle, iconClass: "text-red-400" };
  }
  return { tone: "text-slate-400", icon: CheckCircle2, iconClass: "text-slate-600" };
}

export default function ActivityPanel({ isOpen, onToggle, events = [] }) {
  return (
    <>
      {/* ACTIVITY PANEL */}
      <motion.aside
        initial={false}
        animate={{
          x: isOpen ? 0 : 330,
          opacity: isOpen ? 1 : 0,
        }}
        transition={{
          duration: 0.35,
          ease: [0.22, 1, 0.36, 1],
        }}
        className="
          absolute
          right-6
          top-1/2
          z-30
          w-[310px]
          -translate-y-1/2
          overflow-hidden
          border
          border-cyan-400/15
          bg-[#050b13]/90
          shadow-[0_0_35px_rgba(0,207,239,0.04)]
          backdrop-blur-md
        "
      >
        <div className="relative">

          {/* HEADER */}
          <div className="flex h-[58px] items-center gap-3 border-b border-cyan-400/10 px-5">
            <Activity
              size={16}
              strokeWidth={1.4}
              className="text-cyan-400"
            />

            <div>
              <div className="text-[9px] tracking-[0.22em] text-cyan-300">
                ACTIVITY
              </div>

              <div className="mt-1 text-[7px] tracking-[0.15em] text-[#43545f]">
                LIVE SYSTEM FEED
              </div>
            </div>
          </div>

          {/* ACTIVITY LIST */}
          <div className="max-h-[300px] space-y-2 overflow-y-auto px-5 py-4">
            {events.length === 0 ? (
              <div className="px-1 py-6 text-center text-[8px] tracking-[0.18em] text-[#3f505c]">
                NO ACTIVITY YET
              </div>
            ) : null}

            {events.map((item) => {
              const { tone, icon: Icon, iconClass } = eventStyle(item.kind);

              return (
                <div
                  key={item.id}
                  className="
                    border
                    border-cyan-400/10
                    bg-cyan-400/[0.02]
                    px-4
                    py-3
                  "
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon
                        size={item.kind === "request" ? 8 : 13}
                        fill={item.kind === "request" ? "currentColor" : "none"}
                        strokeWidth={1.4}
                        className={iconClass}
                      />

                      <span
                        className={`whitespace-nowrap text-[9px] tracking-[0.12em] ${tone}`}
                      >
                        {item.label}
                      </span>
                    </div>

                    <span className="whitespace-nowrap text-[8px] tracking-[0.1em] text-slate-600">
                      {item.time}
                    </span>
                  </div>

                  {item.detail ? (
                    <div className="mt-1.5 truncate pl-6 text-[8px] tracking-[0.08em] text-[#50606d]">
                      {item.detail}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>

          {/* FOOTER */}
          <div className="border-t border-cyan-400/10 px-5 py-3">
            <div className="flex items-center justify-between">
              <span className="text-[7px] tracking-[0.16em] text-[#3f505c]">
                EVENT STREAM
              </span>

              <span className="text-[7px] tracking-[0.12em] text-cyan-400/60">
                LIVE
              </span>
            </div>
          </div>

          {/* CLOSE HANDLE */}
          <button
            type="button"
            onClick={onToggle}
            aria-label="Collapse activity panel"
            className="
              absolute
              left-0
              top-1/2
              flex
              h-9
              w-7
              -translate-y-1/2
              items-center
              justify-center
              border-r
              border-cyan-400/10
              bg-[#050b13]
              text-slate-500
              transition
              hover:text-cyan-300
            "
          >
            <ChevronRight size={14} />
          </button>

        </div>
      </motion.aside>

      {/* REOPEN HANDLE */}
      <motion.button
        type="button"
        onClick={onToggle}
        aria-label="Open activity panel"
        initial={false}
        animate={{
          opacity: isOpen ? 0 : 1,
        }}
        transition={{
          duration: 0.15,
        }}
        className="
          absolute
          right-0
          top-1/2
          z-30
          flex
          h-[54px]
          w-[20px]
          -translate-y-1/2
          items-center
          justify-center
          border
          border-r-0
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
        <ChevronLeft size={13} />
      </motion.button>
    </>
  );
}