import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronUp,
  ChevronDown,
  Send,
  X,
} from "lucide-react";

import { sendChat } from "../../services/apiClient";
import { getOwnerName, getSessionId } from "../../services/session";

/**
 * How many turns of history to send to the gateway.
 *
 * The Python client keeps the last 20 entries (client/desktop_app.py trims
 * with `del self.chat_history[:-20]`), so both clients bound history the
 * same way. Unbounded history would grow the prompt on every turn until the
 * model's context is exhausted.
 */
const MAX_HISTORY_MESSAGES = 20;

/** Roles used in the local message list. "error" is UI-only, never sent. */
const ROLE = { USER: "user", JARVIS: "jarvis", ERROR: "error" };

/** Turn the local message list into the gateway's chat_history contract. */
function toChatHistory(messages) {
  return messages
    .filter((item) => item.role === ROLE.USER || item.role === ROLE.JARVIS)
    .slice(-MAX_HISTORY_MESSAGES)
    .map((item) => ({
      role: item.role === ROLE.USER ? "user" : "assistant",
      content: item.text,
    }));
}

/** Small metadata line under a JARVIS reply: where the answer came from. */
function ResponseMeta({ source, modelUsed, focusText }) {
  const sourceLabel =
    { command: "COMMAND", ai: "AI", fallback: "FALLBACK" }[source] ?? source?.toUpperCase();

  if (!sourceLabel && !focusText) return null;

  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[8px] tracking-[0.16em]">
      {sourceLabel ? (
        <span
          className={
            source === "ai"
              ? "border border-cyan-400/25 px-1.5 py-0.5 text-cyan-300"
              : source === "fallback"
              ? "border border-red-400/25 px-1.5 py-0.5 text-red-400"
              : "border border-slate-600/50 px-1.5 py-0.5 text-[#70808d]"
          }
        >
          {sourceLabel}
        </span>
      ) : null}

      {modelUsed ? (
        <span className="text-[#50606d]">{modelUsed}</span>
      ) : null}

      {focusText ? (
        <span className="text-[#50606d]">{focusText}</span>
      ) : null}
    </div>
  );
}

/**
 * @param {(event: {type: "request"|"response"|"error", text: string,
 *   source?: string, modelUsed?: string, focusText?: string}) => void}
 *   [props.onLifecycleEvent]
 *   Reports what the chat request is doing so App can drive the global
 *   visual state. This panel still owns the request itself -- it only
 *   announces start, success and failure.
 */
export default function ConversationPanel({ isOpen, onToggle, onLifecycleEvent }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);

  // The gateway accepts these for desktop-action routing. The browser cannot
  // execute launch/file/music actions, so selected_action stays at the
  // gateway's own default and last_action just echoes what came back --
  // enough to stay contract-compatible without pretending to act.
  const [lastAction, setLastAction] = useState("chrome");

  // Resolved once per mount. getSessionId() reads sessionStorage, so a
  // refresh keeps the id and a new tab gets its own.
  const [sessionId] = useState(() => getSessionId());
  const ownerName = getOwnerName();

  const messagesEndRef = useRef(null);
  const nextId = useRef(1);

  const appendMessage = (entry) => {
    setMessages((current) => [...current, { id: nextId.current++, ...entry }]);
  };

  // Keep the newest turn in view as the list grows.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  const handleSend = async () => {
    const text = message.trim();

    // Guard both empty input and a second submit while one is in flight.
    if (!text || isSending) return;

    const chatHistory = toChatHistory(messages);

    appendMessage({ role: ROLE.USER, text });
    setMessage("");
    setIsSending(true);
    onLifecycleEvent?.({ type: "request", text });

    const response = await sendChat(text, {
      chatHistory,
      selectedAction: "chrome",
      lastAction,
      ownerName,
      sessionId,
    });

    // apiClient never throws: failures arrive as a populated `error` string,
    // already made readable there. The user's message stays on screen either
    // way, so they can simply send again.
    if (response.error) {
      appendMessage({ role: ROLE.ERROR, text: response.error });
      onLifecycleEvent?.({ type: "error", text: response.error });
    } else {
      const replyText = response.spoken_text || response.full_text || "(no response)";

      appendMessage({
        role: ROLE.JARVIS,
        text: replyText,
        source: response.source,
        modelUsed: response.model_used,
        focusText: response.focus_text,
      });

      onLifecycleEvent?.({
        type: "response",
        text: replyText,
        source: response.source,
        modelUsed: response.model_used,
        focusText: response.focus_text,
      });

      if (response.action_target) setLastAction(response.action_target);
    }

    setIsSending(false);
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
              {messages.length === 0 && !isSending ? (
                <div className="flex h-full items-center justify-center text-[9px] tracking-[0.2em] text-[#3f505c]">
                  AWAITING YOUR COMMAND
                </div>
              ) : null}

              {messages.map((item) => {
                if (item.role === ROLE.ERROR) {
                  return (
                    <div key={item.id} className="flex flex-col items-start">
                      <span className="text-[9px] tracking-[0.2em] text-red-400">
                        CONNECTION ERROR
                      </span>

                      <div
                        className="
                          mt-2
                          max-w-[80%]
                          border
                          border-red-400/25
                          bg-red-400/[0.04]
                          px-4
                          py-3
                          text-[12px]
                          text-red-300
                        "
                      >
                        {item.text}
                      </div>
                    </div>
                  );
                }

                const isUser = item.role === ROLE.USER;

                return (
                  <div
                    key={item.id}
                    className={
                      isUser
                        ? "flex flex-col items-end"
                        : "flex flex-col items-start"
                    }
                  >
                    {/* SENDER */}
                    <span
                      className={
                        isUser
                          ? "text-[9px] tracking-[0.2em] text-[#70808d]"
                          : "text-[9px] tracking-[0.2em] text-cyan-400"
                      }
                    >
                      {isUser ? "USER" : "J.A.R.V.I.S"}
                    </span>

                    {/* MESSAGE */}
                    <div
                      className={
                        isUser
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
                      {item.text}
                    </div>

                    {!isUser ? (
                      <ResponseMeta
                        source={item.source}
                        modelUsed={item.modelUsed}
                        focusText={item.focusText}
                      />
                    ) : null}
                  </div>
                );
              })}

              {/* PROCESSING INDICATOR */}
              {isSending ? (
                <div className="flex flex-col items-start">
                  <span className="text-[9px] tracking-[0.2em] text-cyan-400">
                    J.A.R.V.I.S
                  </span>

                  <div
                    className="
                      mt-2
                      flex
                      items-center
                      gap-2
                      border
                      border-cyan-400/15
                      bg-cyan-400/[0.03]
                      px-4
                      py-3
                      text-[11px]
                      tracking-[0.18em]
                      text-cyan-300/70
                    "
                  >
                    {[0, 1, 2].map((index) => (
                      <motion.span
                        key={index}
                        className="h-[4px] w-[4px] rounded-full bg-cyan-400"
                        animate={{ opacity: [0.25, 1, 0.25] }}
                        transition={{
                          duration: 1.1,
                          repeat: Infinity,
                          delay: index * 0.18,
                          ease: "easeInOut",
                        }}
                      />
                    ))}

                    PROCESSING
                  </div>
                </div>
              ) : null}

              <div ref={messagesEndRef} />
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
                disabled={isSending}
                placeholder={isSending ? "AWAITING RESPONSE..." : "TYPE A COMMAND..."}
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
                  disabled:text-slate-600
                "
              />

              <button
                onClick={handleSend}
                disabled={isSending || !message.trim()}
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
                  disabled:cursor-not-allowed
                  disabled:border-slate-700/60
                  disabled:text-slate-600
                  disabled:hover:bg-transparent
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
