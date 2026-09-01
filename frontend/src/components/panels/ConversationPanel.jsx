import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronUp,
  ChevronDown,
  Send,
  X,
} from "lucide-react";

export default function ConversationPanel({ isOpen, onToggle }) {
  const [message, setMessage] = useState("");

  const conversations = [
    {
      id: 1,
      sender: "USER",
      message: "Good evening, JARVIS.",
    },
    {
      id: 2,
      sender: "J.A.R.V.I.S",
      message: "Good evening. All systems are operational.",
    },
    {
      id: 3,
      sender: "USER",
      message: "What is the current system status?",
    },
    {
      id: 4,
      sender: "J.A.R.V.I.S",
      message:
        "Core systems are online. Voice interface is standing by.",
    },
  ];

  const handleSend = () => {
    if (!message.trim()) return;

    console.log("Message:", message);

    setMessage("");
  };

  return (
    <div
      className="
        absolute
        bottom-0
        left-1/2
        z-30
        w-[620px]
        -translate-x-1/2
      "
    >
      {/* CONVERSATION TAB */}
      <button
        onClick={onToggle}
        className="
          absolute
          left-1/2
          top-0
          z-40
          flex
          -translate-x-1/2
          -translate-y-full
          items-center
          gap-3
          rounded-t-md
          border
          border-b-0
          border-cyan-400/25
          bg-[#07111b]
          px-6
          py-3
          text-[10px]
          tracking-[0.22em]
          text-cyan-300
          shadow-[0_-4px_20px_rgba(0,207,239,0.04)]
          transition
          hover:border-cyan-400
          hover:bg-[#091722]
        "
      >
        {isOpen ? (
          <ChevronDown size={14} />
        ) : (
          <ChevronUp size={14} />
        )}

        CONVERSATION
      </button>

      {/* CONVERSATION PANEL */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{
              height: 0,
              opacity: 0,
            }}
            animate={{
              height: 420,
              opacity: 1,
            }}
            exit={{
              height: 0,
              opacity: 0,
            }}
            transition={{
              duration: 0.35,
              ease: "easeOut",
            }}
            className="
              relative
              overflow-hidden
              border
              border-cyan-400/20
              bg-[#050b13]/95
              shadow-[0_-10px_40px_rgba(0,207,239,0.06)]
              backdrop-blur-xl
            "
          >
            {/* PANEL HEADER */}
            <div
              className="
                flex
                items-center
                justify-between
                border-b
                border-cyan-400/10
                px-6
                py-4
              "
            >
              <div>
                <div className="text-[10px] tracking-[0.25em] text-cyan-300">
                  CONVERSATION STREAM
                </div>

                <div className="mt-1 text-[9px] tracking-[0.18em] text-[#50606d]">
                  JARVIS INTERACTION HISTORY
                </div>
              </div>

              <button
                onClick={onToggle}
                className="
                  text-slate-500
                  transition
                  hover:text-cyan-300
                "
              >
                <X size={16} />
              </button>
            </div>

            {/* MESSAGES */}
            <div
              className="
                h-[290px]
                space-y-5
                overflow-y-auto
                px-6
                py-5
              "
            >
              {conversations.map((item) => (
                <div
                  key={item.id}
                  className={
                    item.sender === "USER"
                      ? "flex flex-col items-end"
                      : "flex flex-col items-start"
                  }
                >
                  {/* SENDER */}
                  <span
                    className={
                      item.sender === "USER"
                        ? "text-[9px] tracking-[0.2em] text-[#70808d]"
                        : "text-[9px] tracking-[0.2em] text-cyan-400"
                    }
                  >
                    {item.sender}
                  </span>

                  {/* MESSAGE */}
                  <div
                    className={
                      item.sender === "USER"
                        ? `
                          mt-2
                          max-w-[80%]
                          border
                          border-slate-700/60
                          bg-[#0a111a]
                          px-4
                          py-3
                          text-[12px]
                          text-slate-300
                        `
                        : `
                          mt-2
                          max-w-[80%]
                          border
                          border-cyan-400/15
                          bg-cyan-400/[0.03]
                          px-4
                          py-3
                          text-[12px]
                          text-[#b7cbd5]
                        `
                    }
                  >
                    {item.message}
                  </div>
                </div>
              ))}
            </div>

            {/* INPUT AREA */}
            <div
              className="
                flex
                items-center
                gap-3
                border-t
                border-cyan-400/10
                px-5
                py-4
              "
            >
              <input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSend();
                  }
                }}
                placeholder="TYPE A COMMAND..."
                className="
                  flex-1
                  bg-transparent
                  px-3
                  py-2
                  text-[11px]
                  tracking-[0.12em]
                  text-slate-300
                  outline-none
                  placeholder:text-slate-600
                "
              />

              <button
                onClick={handleSend}
                className="
                  flex
                  items-center
                  gap-2
                  border
                  border-cyan-400/30
                  px-4
                  py-2
                  text-[10px]
                  tracking-[0.18em]
                  text-cyan-300
                  transition
                  hover:border-cyan-300
                  hover:bg-cyan-400/10
                "
              >
                <Send size={13} />
                SEND
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}