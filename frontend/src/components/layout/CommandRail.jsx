import { motion } from "framer-motion";
import {
  Grid2X2,
  Zap,
  Brain,
  Settings,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";

const railItems = [
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

export default function CommandRail({ isOpen, onToggle }) {
  return (
    <>
      {/* COMMAND RAIL */}
      <motion.aside
        initial={false}
        animate={{
          x: isOpen ? 0 : -235,
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
          h-[340px]
          w-[210px]
          overflow-hidden
          border
          border-cyan-400/15
          bg-[#050b13]/90
          shadow-[0_0_30px_rgba(0,207,239,0.04)]
          backdrop-blur-md
        "
      >
        {/* HEADER */}
        <div
          className="
            flex
            h-[58px]
            items-center
            border-b
            border-cyan-400/10
            px-5
          "
        >
          <div className="flex items-center gap-3">
            <div
              className="
                h-2
                w-2
                rounded-full
                bg-cyan-400
                shadow-[0_0_8px_#00cfef]
              "
            />

            <span
              className="
                whitespace-nowrap
                text-[9px]
                tracking-[0.2em]
                text-cyan-300
              "
            >
              COMMAND
            </span>
          </div>
        </div>

        {/* COMMAND ITEMS */}
        <div className="flex flex-col gap-2 p-3">
          {railItems.map(({ label, icon: Icon }) => (
            <button
              key={label}
              type="button"
              className="
                flex
                h-[46px]
                w-full
                items-center
                rounded-sm
                border
                border-transparent
                text-slate-500
                transition
                hover:border-cyan-400/20
                hover:bg-cyan-400/[0.04]
                hover:text-cyan-300
              "
            >
              <div className="flex items-center gap-4 px-3">
                <Icon
                  size={18}
                  strokeWidth={1.4}
                  className="shrink-0"
                />

                <span
                  className="
                    whitespace-nowrap
                    text-[9px]
                    tracking-[0.18em]
                  "
                >
                  {label}
                </span>
              </div>
            </button>
          ))}
        </div>

        {/* CLOSE HANDLE */}
        <button
          type="button"
          onClick={onToggle}
          aria-label="Collapse command rail"
          className="
            absolute
            right-0
            top-32%
            flex
            h-10
            w-8
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
          <ChevronLeft size={15} />
        </button>
      </motion.aside>

      {/* CLOSED STATE HANDLE */}
      <motion.button
        type="button"
        onClick={onToggle}
        aria-label="Open command rail"
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
          h-[54px]
          w-[22px]
          items-center
          justify-center
          border
          border-l-0
          border-cyan-400/20
          bg-[#050b13]/90
          text-slate-500
          backdrop-blur-md
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