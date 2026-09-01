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

const metrics = [
  {
    label: "CORE LOAD",
    value: 84,
    icon: Cpu,
  },
  {
    label: "MEMORY",
    value: 62,
    icon: MemoryStick,
  },
  {
    label: "PROCESSING",
    value: 91,
    icon: Activity,
  },
];

function MetricBar({ label, value, icon: Icon }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[8px] tracking-[0.17em] text-[#667985]">
          <Icon size={12} strokeWidth={1.4} />
          <span>{label}</span>
        </div>

        <span className="text-[8px] tracking-[0.12em] text-cyan-300">
          {value}%
        </span>
      </div>

      <div className="h-[3px] w-full overflow-hidden bg-[#0b1822]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{
            duration: 0.8,
            ease: "easeOut",
          }}
          className="h-full bg-cyan-400 shadow-[0_0_8px_rgba(0,207,239,0.65)]"
        />
      </div>
    </div>
  );
}

export default function ControlPanel({ isOpen, onToggle }) {
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
            <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00cfef]" />

            <span className="text-[9px] tracking-[0.22em] text-cyan-300">
              JARVIS CONTROL
            </span>
          </div>

          <span className="text-[7px] tracking-[0.16em] text-[#3f505c]">
            ONLINE
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
                REAL-TIME CORE MONITORING
              </div>
            </div>
          </div>

          <div className="space-y-3.5">
            {metrics.map((metric) => (
              <MetricBar
                key={metric.label}
                label={metric.label}
                value={metric.value}
                icon={metric.icon}
              />
            ))}
          </div>
        </section>

        {/* NETWORK */}
        <div className="mx-4 border-t border-cyan-400/10" />

        <section className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2 text-[8px] tracking-[0.17em] text-[#667985]">
            <Wifi size={12} strokeWidth={1.4} />
            NETWORK
          </div>

          <div className="flex items-center gap-1.5 text-[8px] tracking-[0.12em] text-cyan-300">
            <CheckCircle2 size={11} strokeWidth={1.5} />
            CONNECTED
          </div>
        </section>

        {/* FOOTER */}
        <div className="border-t border-cyan-400/10 px-4 py-2.5 text-[7px] tracking-[0.15em] text-[#3f505c]">
          JARVIS CORE • STABLE
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