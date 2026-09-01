import { motion } from "framer-motion";

export default function VoiceVisualizer({ active = false }) {
  const bars = [0.3, 0.5, 0.8, 0.45, 0.9, 0.6, 0.35, 0.7, 0.5, 0.85, 0.4];

  return (
    <div className="flex flex-col items-center gap-2">

      <span className="text-[9px] tracking-[0.35em] text-cyan-400/50">
        VOICE INPUT
      </span>

      <div className="flex items-center gap-[3px] h-7">

        {bars.map((height, index) => (
          <motion.div
            key={index}
            className="w-[3px] rounded-full bg-cyan-400"
            animate={{
              height: active
                ? [`${height * 12}px`, `${height * 30}px`, `${height * 12}px`]
                : "4px",
              opacity: active ? [0.5, 1, 0.5] : 0.3,
            }}
            transition={{
              duration: 0.5 + index * 0.08,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{
              boxShadow: active
                ? "0 0 8px rgba(0,207,239,0.8)"
                : "none",
            }}
          />
        ))}

      </div>

    </div>
  );
}