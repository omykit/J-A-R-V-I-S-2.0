import { motion } from "framer-motion";
import {
  Activity,
  CheckCircle2,
  Circle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const activities = [
  {
    label: "SYSTEM READY",
    time: "NOW",
    status: "active",
  },
  {
    label: "VOICE ENGINE",
    time: "READY",
    status: "complete",
  },
  {
    label: "MEMORY SERVICE",
    time: "READY",
    status: "complete",
  },
  {
    label: "COMMAND GATEWAY",
    time: "READY",
    status: "complete",
  },
];

export default function ActivityPanel({ isOpen, onToggle }) {
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
          <div className="space-y-2 px-5 py-4">
            {activities.map((item) => (
              <div
                key={item.label}
                className="
                  flex
                  items-center
                  justify-between
                  border
                  border-cyan-400/10
                  bg-cyan-400/[0.02]
                  px-4
                  py-3.5
                "
              >
                <div className="flex items-center gap-3">
                  {item.status === "active" ? (
                    <Circle
                      size={8}
                      fill="currentColor"
                      strokeWidth={1.5}
                      className="text-cyan-400"
                    />
                  ) : (
                    <CheckCircle2
                      size={13}
                      strokeWidth={1.4}
                      className="text-slate-600"
                    />
                  )}

                  <span className="whitespace-nowrap text-[9px] tracking-[0.12em] text-slate-400">
                    {item.label}
                  </span>
                </div>

                <span className="whitespace-nowrap text-[8px] tracking-[0.1em] text-slate-600">
                  {item.time}
                </span>
              </div>
            ))}
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