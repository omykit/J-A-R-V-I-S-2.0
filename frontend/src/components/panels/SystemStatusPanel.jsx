import { motion } from "framer-motion";
import {
  Cpu,
  MemoryStick,
  Activity,
  Wifi,
  CheckCircle2,
} from "lucide-react";

function StatusBar({ label, value, icon: Icon, status }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[9px] tracking-[0.18em] text-[#6d7f8c]">
          <Icon size={13} strokeWidth={1.5} />
          {label}
        </div>

        <span className="text-[9px] tracking-[0.12em] text-cyan-300">
          {status}
        </span>
      </div>

      <div className="h-[4px] w-full overflow-hidden bg-[#0b1822]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{
            duration: 1,
            ease: "easeOut",
          }}
          className="h-full bg-cyan-400 shadow-[0_0_10px_rgba(0,207,239,0.8)]"
        />
      </div>
    </div>
  );
}

export default function SystemStatusPanel() {
  const metrics = [
    {
      label: "CORE LOAD",
      value: 84,
      status: "84%",
      icon: Cpu,
    },
    {
      label: "MEMORY",
      value: 62,
      status: "62%",
      icon: MemoryStick,
    },
    {
      label: "PROCESSING",
      value: 91,
      status: "91%",
      icon: Activity,
    },
  ];

  return (
    <motion.div
      initial={{
        opacity: 0,
        x: -20,
      }}
      animate={{
        opacity: 1,
        x: 0,
      }}
      transition={{
        duration: 0.5,
        ease: "easeOut",
      }}
      className="
        absolute
        bottom-7
        left-[240px]
        z-10
        w-[240px]
        border
        border-cyan-400/15
        bg-[#050b13]/85
        p-5
        shadow-[0_0_30px_rgba(0,207,239,0.03)]
        backdrop-blur-md
      "
    >
      {/* HEADER */}
      <div className="mb-6">
        <div className="text-[10px] tracking-[0.25em] text-cyan-300">
          SYSTEM METRICS
        </div>

        <div className="mt-2 text-[8px] tracking-[0.18em] text-[#4d5d68]">
          REAL-TIME CORE MONITORING
        </div>
      </div>

      {/* METRICS */}
      <div className="space-y-5">
        {metrics.map((metric) => (
          <StatusBar
            key={metric.label}
            label={metric.label}
            value={metric.value}
            status={metric.status}
            icon={metric.icon}
          />
        ))}
      </div>

      {/* NETWORK */}
      <div className="mt-6 border-t border-cyan-400/10 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[9px] tracking-[0.18em] text-[#6d7f8c]">
            <Wifi size={13} strokeWidth={1.5} />
            NETWORK
          </div>

          <div className="flex items-center gap-2 text-[9px] tracking-[0.12em] text-cyan-300">
            <CheckCircle2 size={12} />
            CONNECTED
          </div>
        </div>
      </div>

      {/* FOOTER */}
      <div className="mt-5 border-t border-cyan-400/10 pt-3 text-[8px] tracking-[0.16em] text-[#3f505c]">
        JARVIS CORE • STABLE
      </div>
    </motion.div>
  );
}