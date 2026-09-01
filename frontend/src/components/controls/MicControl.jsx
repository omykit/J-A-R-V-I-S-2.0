import { Mic, MicOff } from "lucide-react";
import { motion } from "framer-motion";

export default function MicControl({
  isMicActive,
  onToggle,
  status,
}) {
  const isListening = status === "LISTENING";

  return (
    <div className="flex flex-col items-center gap-4">
      <motion.button
        type="button"
        onClick={onToggle}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.94 }}
        animate={{
          boxShadow: isListening
            ? [
                "0 0 10px rgba(0,207,239,0.25)",
                "0 0 30px rgba(0,207,239,0.75)",
                "0 0 10px rgba(0,207,239,0.25)",
              ]
            : "0 0 0px rgba(0,207,239,0)",
        }}
        transition={{
          duration: 1.5,
          repeat: isListening ? Infinity : 0,
        }}
        className={`
          w-[90px]
          h-[90px]
          rounded-full
          flex
          items-center
          justify-center
          border
          transition-colors
          duration-300
          ${
            isMicActive
              ? "border-cyan-400 bg-cyan-400/10 text-cyan-300"
              : "border-cyan-400/30 bg-[#06101a] text-slate-400"
          }
        `}
      >
        {isMicActive ? (
          <Mic size={30} strokeWidth={1.5} />
        ) : (
          <MicOff size={30} strokeWidth={1.5} />
        )}
      </motion.button>

      <div className="font-mono text-[10px] tracking-[0.35em] text-slate-500">
        {isMicActive ? "MIC ACTIVE" : "MIC OFF"}
      </div>
    </div>
  );
}