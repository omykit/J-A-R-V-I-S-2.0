import { motion } from "framer-motion";

export default function JarvisOrb({ state = "standby" }) {
  const states = {
    standby: {
      color: "#00cfeF",
      glow: "rgba(0,207,239,0.25)",
      speed: 25,
      label: "STANDBY",
    },

    listening: {
      color: "#4dffff",
      glow: "rgba(77,255,255,0.45)",
      speed: 8,
      label: "LISTENING",
    },

    thinking: {
      color: "#7a8cff",
      glow: "rgba(122,140,255,0.45)",
      speed: 4,
      label: "PROCESSING",
    },

    speaking: {
      color: "#00cfeF",
      glow: "rgba(0,207,239,0.6)",
      speed: 6,
      label: "SPEAKING",
    },

    // Deliberately restrained: the rotation nearly stalls and the glow dims,
    // so failure reads as the system losing power rather than as an alarm.
    // #ff3b3b is the error red already defined in the design reference.
    error: {
      color: "#ff5f5f",
      glow: "rgba(255,59,59,0.22)",
      speed: 60,
      label: "ERROR",
    },
  };

  const current = states[state] || states.standby;

  return (
    <div className="relative flex flex-col items-center justify-center">

      {/* ORB CONTAINER */}
      <div className="relative w-[440px] h-[440px] flex items-center justify-center">

        {/* OUTER GLOW */}
        <motion.div
          className="absolute w-[440px] h-[440px] rounded-full"
          animate={{
            scale: [1, 1.03, 1],
            opacity: [0.45, 0.8, 0.45],
          }}
          transition={{
            duration:
              state === "listening"
                ? 1.5
                : state === "thinking"
                ? 2
                : state === "error"
                ? 6
                : 5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          style={{
            background: `radial-gradient(circle, ${current.glow} 0%, transparent 68%)`,
          }}
        />

        {/* OUTER RING */}
        <motion.div
          className="absolute w-[430px] h-[430px] rounded-full border"
          animate={{ rotate: 360 }}
          transition={{
            duration: current.speed,
            repeat: Infinity,
            ease: "linear",
          }}
          style={{
            borderColor: `${current.color}55`,
          }}
        />

        {/* DASHED ROTATING RING */}
        <motion.div
          className="absolute w-[390px] h-[390px] rounded-full border border-dashed"
          animate={{ rotate: -360 }}
          transition={{
            duration: current.speed * 1.5,
            repeat: Infinity,
            ease: "linear",
          }}
          style={{
            borderColor: `${current.color}88`,
          }}
        />

        {/* INNER RING */}
        <motion.div
          className="absolute w-[330px] h-[330px] rounded-full border"
          animate={{
            rotate: state === "thinking" ? 360 : 0,
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "linear",
          }}
          style={{
            borderColor: `${current.color}55`,
          }}
        />

        {/* CORE */}
        <motion.div
          className="relative z-10 w-[240px] h-[240px] rounded-full flex items-center justify-center"
          animate={{
            scale:
              state === "listening"
                ? [1, 1.08, 1]
                : state === "speaking"
                ? [1, 1.05, 1]
                : state === "thinking"
                ? [1, 1.045, 1]
                : state === "error"
                ? [1, 1.006, 1]
                : [1, 1.02, 1],
          }}
          transition={{
            duration:
              state === "listening"
                ? 1
                : state === "speaking"
                ? 1.3
                : state === "thinking"
                ? 0.9
                : state === "error"
                ? 5
                : 4,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          style={{
            background:
              "radial-gradient(circle at 50% 50%, rgba(0,207,239,0.22), rgba(2,18,25,0.9) 65%)",

            boxShadow: `0 0 60px ${current.glow}`,
          }}
        >
          <div
            className="text-[20px] tracking-[0.32em] text-center"
            style={{
              color: current.color,
              textShadow: `0 0 20px ${current.color}`,
            }}
          >
            J.A.R.V.I.S
          </div>
        </motion.div>

        {/* ORBITING DOT */}
        <motion.div
          className="absolute w-[8px] h-[8px] rounded-full"
          animate={{ rotate: 360 }}
          transition={{
            duration: current.speed / 2,
            repeat: Infinity,
            ease: "linear",
          }}
        >
          <div
            className="absolute top-0 left-1/2 w-[6px] h-[6px] rounded-full"
            style={{
              background: current.color,
              boxShadow: `0 0 14px ${current.color}`,
            }}
          />
        </motion.div>

      </div>

      {/* STATUS */}
      <motion.div
        key={current.label}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-6 text-[12px] tracking-[0.32em]"
        style={{ color: current.color }}
      >
        {"{"} {current.label} {"}"}
      </motion.div>

    </div>
  );
}