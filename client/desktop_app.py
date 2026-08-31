"""JARVIS Desktop Client — Gateway-connected voice assistant.

Minimal, GUI-less voice loop: listens via Vosk, sends recognized text to the
JARVIS Gateway, speaks the response via Piper, and dispatches any action
intents (launch/file_op/music) the command-service emits. This intentionally
has no Tkinter UI — a React Native/Expo desktop client is the planned
long-term UI, so no GUI code is invested here.

jarvis_desktop.py (the original Tkinter app, talking to the in-process
ai_module/command_handler/memory_module) remains the working fallback.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pygame

from api_client import check_gateway_health, send_chat
from voice_engine import VoiceEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("jarvis.client")

CONFIG_PATH = ROOT_DIR / "jarvis_config.json"

# Wake matching (3a). Session 1 took 1 minute 37 seconds and six attempts to
# wake, and two of those failures were NOT speech-recognition errors: Vosk
# returned "jarvis" at 0.88 confidence and "hello jarvis" at 0.81, cleanly,
# and the matcher rejected both -- because it compared against five exact
# phrases and neither was one of them. Matching the wake WORD anywhere in a
# normalized utterance subsumes all five phrases and every reasonable
# variant ("hello jarvis", bare "jarvis", "jarvis are you there").
WAKE_WORD = "jarvis"

# Kept only for phrases that do not contain the wake word itself. The five
# original phrases all did, so the wake-word rule already covers them.
WAKE_PHRASES: list[str] = []

EXIT_PHRASE = "thank you jarvis"
REMINDER_POLL_SECONDS = 30.0
MUSIC_VOLUME = 0.3
MUSIC_BASE_NAME = "theme"
MUSIC_EXTENSIONS = [".mp3", ".wav", ".ogg"]

# ── Post-STT correction map (3b) ────────────────────────────────────────
# Vosk ships a fixed lexicon, so a word outside it can never be transcribed
# correctly no matter how clearly it is spoken -- "Omair" is not in the
# en-us model's vocabulary, and neither is "Jarvis" reliably. This is not a
# pronunciation problem and cannot be fixed by speaking more clearly.
# Every entry below was observed in the session 1 log.
#
# Two groups, deliberately applied differently:
#
#   WAKE_MISHEARINGS are corrected only at the START or END of an utterance,
#   because that is where a wake word is spoken. Applying them everywhere
#   would corrupt ordinary dictation -- "remember that John is my manager"
#   must not become "remember that jarvis is my manager".
#
#   NAME_CORRECTIONS are corrected anywhere, because a name legitimately
#   appears mid-sentence ("call me omar", "my name is omer").
WAKE_MISHEARINGS = ("joe was", "journal", "journalists", "john", "jarvos", "dervis")

NAME_CORRECTIONS = {
    "omar": "Omair",
    "omer": "Omair",
    "olmert": "Omair",
    "almond": "Omair",
}

_PUNCTUATION_RE = re.compile(r"[^a-z0-9' ]+")

_wake_alternatives = "|".join(sorted(WAKE_MISHEARINGS, key=len, reverse=True))
_WAKE_MISHEARING_RE = re.compile(
    rf"^(?:{_wake_alternatives})\b|\b(?:{_wake_alternatives})$", re.IGNORECASE
)

_NAME_CORRECTION_RE = re.compile(
    r"\b(?:" + "|".join(sorted(NAME_CORRECTIONS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def apply_stt_corrections(text: str) -> str:
    """Repair known Vosk misrecognitions before routing."""
    corrected = _NAME_CORRECTION_RE.sub(
        lambda m: NAME_CORRECTIONS[m.group(0).lower()], text
    )
    return _WAKE_MISHEARING_RE.sub(WAKE_WORD, corrected)


def normalize_utterance(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return " ".join(_PUNCTUATION_RE.sub(" ", text.lower()).split())


def is_wake_utterance(text: str) -> bool:
    """True when the wake word appears anywhere in the utterance.

    Token membership, not substring: "jarvis" must be a word of its own so
    that an unrelated word merely containing it cannot wake the assistant.
    """
    normalized = normalize_utterance(text)
    if not normalized:
        return False
    if WAKE_WORD in normalized.split():
        return True
    return any(phrase in normalized for phrase in WAKE_PHRASES)


DEFAULT_CONFIG = {
    "assistant_name": "Jarvis",
    "owner_name": "Omair",
    "workspace_dir": "",
    "voice": {
        "energy_threshold": 250,
        "pause_threshold": 0.8,
        "tts_rate": 175,
        "vosk_model_path": "vosk-model-en-us-0.22",
        "allow_google_fallback": False,
        "google_fallback_cooldown_seconds": 90,
    },
}

# Duplicated from command_handler.py rather than imported: this client must
# not depend on the legacy in-process ai_module/memory_module import chain —
# it only knows how to execute the launch intents the gateway hands back.
APP_TARGETS = {
    "chrome": {
        "label": "Google Chrome",
        "targets": [
            Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LocalAppData", "")) / "Google/Chrome/Application/chrome.exe",
        ],
    },
    "whatsapp": {
        "label": "WhatsApp",
        "targets": [
            Path(os.environ.get("LocalAppData", "")) / "WhatsApp/WhatsApp.exe",
            "whatsapp:",
            "https://web.whatsapp.com/",
        ],
    },
    "notepad": {"label": "Notepad", "targets": [Path(r"C:/Windows/System32/notepad.exe")]},
    "calculator": {"label": "Calculator", "targets": ["calc.exe"]},
    "explorer": {"label": "File Explorer", "targets": [Path(r"C:/Windows/explorer.exe")]},
    "settings": {"label": "Windows Settings", "targets": ["ms-settings:"]},
    "youtube": {"label": "YouTube", "targets": ["https://www.youtube.com/"]},
}


def deep_merge(base: dict, incoming: dict) -> dict:
    merged = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError("Config root must be a JSON object")
    except Exception as exc:
        logger.warning(f"config_load_error:{exc}")
        return dict(DEFAULT_CONFIG)
    return deep_merge(DEFAULT_CONFIG, raw)


class JarvisClient:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.owner_name = str(config.get("owner_name") or "Omair")
        self.assistant_name = str(config.get("assistant_name") or "Jarvis")
        self.workspace_dir = Path(config.get("workspace_dir") or ROOT_DIR)
        self.notes_dir = self.workspace_dir / "notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.music_file = self._find_music_file()

        # One id per client run, so a session's turns can be grouped (and
        # read back) in the conversations table. Voice and text mode both
        # use it; a restart starts a new session.
        self.session_id = uuid.uuid4().hex

        self.active = False
        self.selected_action = "chrome"
        self.last_action = "chrome"
        self.chat_history: list[dict[str, str]] = []
        self._busy = threading.Event()
        self._stop_event = threading.Event()

        self.voice_engine = VoiceEngine(config=config, logger=logger.info)

    # ── Music ──

    def _find_music_file(self) -> Path | None:
        for extension in MUSIC_EXTENSIONS:
            candidate = ROOT_DIR / f"{MUSIC_BASE_NAME}{extension}"
            if candidate.exists():
                return candidate
        return None

    def _ensure_audio_ready(self) -> bool:
        if pygame.mixer.get_init():
            return True
        try:
            pygame.mixer.init()
            return True
        except pygame.error as exc:
            logger.warning(f"audio_engine_error:{exc}")
            return False

    def _execute_music_action(self, action_target: str | None) -> None:
        if not self._ensure_audio_ready():
            return
        if action_target == "stop":
            pygame.mixer.music.stop()
        elif action_target in ("play", "restart") and self.music_file is not None:
            busy = pygame.mixer.music.get_busy()
            if action_target == "restart" or not busy:
                pygame.mixer.music.load(str(self.music_file))
                pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)

    # ── Launch / file-op dispatch ──

    def _execute_launch(self, action_target: str | None) -> None:
        if not action_target:
            return
        action = APP_TARGETS.get(action_target)
        if action is None:
            logger.warning(f"unknown_launch_target:{action_target}")
            return
        for target in action["targets"]:
            try:
                if isinstance(target, Path):
                    if target.exists():
                        os.startfile(str(target))
                        break
                    continue
                if isinstance(target, str) and target.startswith("http"):
                    webbrowser.open(target)
                    break
                os.startfile(target)
                break
            except OSError:
                continue
        else:
            logger.warning(f"launch_failed:{action_target}")
            return
        self.selected_action = action_target
        self.last_action = action_target

    def _execute_file_op(self, action_target: str | None, action_data: dict | None) -> None:
        data = action_data or {}
        name = data.get("name")
        if not name:
            return
        path = self.notes_dir / name
        try:
            if action_target == "create_folder":
                path.mkdir(parents=True, exist_ok=True)
                os.startfile(str(path.parent))
            elif action_target == "create_file":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)
                os.startfile(str(path))
            elif action_target == "write_file":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(data.get("content", "")) + "\n", encoding="utf-8")
                os.startfile(str(path))
        except OSError as exc:
            logger.warning(f"file_op_failed:{action_target}:{exc}")

    def _dispatch_action(self, action: str | None, action_target: str | None, action_data: dict | None) -> None:
        if action == "launch":
            self._execute_launch(action_target)
        elif action == "file_op":
            self._execute_file_op(action_target, action_data)
        elif action == "music":
            self._execute_music_action(action_target)

    # ── Speech I/O ──

    def _is_wake_phrase(self, text: str) -> bool:
        return is_wake_utterance(text)

    def speak(self, text: str) -> None:
        if text:
            self.voice_engine.speak_async(text)

    def on_recognized_text(self, text: str) -> None:
        # Repair known misrecognitions first, so both wake matching and the
        # gateway see the corrected text. This runs downstream of the voice
        # engine's TTS echo guard (_looks_like_tts_echo / interrupt check in
        # voice_engine._listen_loop), which has already dropped anything
        # that was JARVIS hearing itself -- so widening the wake rule here
        # cannot reopen that path.
        corrected = apply_stt_corrections(text)
        if corrected != text:
            logger.info(f"stt_corrected:{text!r}->{corrected!r}")

        normalized = normalize_utterance(corrected)
        if not normalized:
            return

        # Only match the wake word while asleep. Once awake, "jarvis what
        # time is it" is a command, not another wake -- matching the word
        # anywhere would otherwise swallow every command that says the name.
        if not self.active:
            if not self._is_wake_phrase(normalized):
                return
            self.active = True
            logger.info(f"wake_phrase_detected:{normalized!r}")
            self.speak(f"I'm online, {self.owner_name}.")
            return

        if EXIT_PHRASE in normalized:
            self.active = False
            self.speak(f"Alright {self.owner_name}, call me if you need anything.")
            return

        if self._busy.is_set():
            logger.info(f"ignored_busy:{normalized}")
            return

        threading.Thread(target=self._handle_text, args=(corrected,), daemon=True).start()

    def _handle_text(self, text: str) -> None:
        self._busy.set()
        try:
            logger.info(f"user:{text}")
            response = send_chat(
                text,
                chat_history=self.chat_history,
                selected_action=self.selected_action,
                last_action=self.last_action,
                owner_name=self.owner_name,
                session_id=self.session_id,
            )
            if response.error:
                logger.warning(f"gateway_error:{response.error}")
                self.speak("I'm having trouble reaching my services right now.")
                return

            self._dispatch_action(response.action, response.action_target, response.action_data)

            self.chat_history.append({"role": "user", "content": text})
            self.chat_history.append({"role": "assistant", "content": response.spoken_text})
            del self.chat_history[:-20]

            logger.info(f"jarvis[{response.source}]:{response.full_text or response.spoken_text}")
            self.speak(response.spoken_text)
        finally:
            self._busy.clear()

    # ── Reminders ──

    def _poll_reminders_loop(self) -> None:
        gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8080").rstrip("/")
        import urllib.request

        while not self._stop_event.is_set():
            try:
                request = urllib.request.Request(
                    f"{gateway_url}/reminders/pending", headers={"Accept": "application/json"}
                )
                with urllib.request.urlopen(request, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                for reminder in data.get("reminders", []):
                    self.speak(f"Reminder: {reminder.get('text', '')}")
            except Exception as exc:
                logger.debug(f"reminder_poll_error:{exc}")
            self._stop_event.wait(REMINDER_POLL_SECONDS)

    # ── Lifecycle ──

    def start(self) -> None:
        threading.Thread(target=self._poll_reminders_loop, daemon=True).start()
        self.voice_engine.listen_continuously(
            on_text=self.on_recognized_text,
            on_error=lambda message: logger.warning(f"voice_error:{message}"),
        )

    def start_text_mode(self) -> None:
        """Text fallback: same gateway call, same action dispatch, no mic.

        Demo insurance in case STT struggles under interview conditions.
        The voice path above is the feature and is untouched -- this only
        replaces where the text comes from. Reminders still poll, and typing
        is an explicit act, so no wake word is required.
        """
        threading.Thread(target=self._poll_reminders_loop, daemon=True).start()
        self.active = True

    def handle_typed_text(self, text: str) -> None:
        """Route typed input exactly as recognised speech is routed.

        Deliberately does NOT run apply_stt_corrections: those repair Vosk
        misrecognitions, and typed text has none to repair -- correcting it
        would rewrite a deliberately typed "john".
        """
        self._handle_text(text)

    def stop(self) -> None:
        self._stop_event.set()
        self.voice_engine.stop()


def run_text_mode(client: JarvisClient) -> int:
    """Typed REPL over the same gateway call and action dispatch as voice."""
    client.start_text_mode()
    print(f"\n{client.assistant_name} is in TEXT mode. Type a command and press Enter.")
    print("No wake word is needed. Type 'exit' or press Ctrl+C to quit.\n")

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        normalized = normalize_utterance(line)
        if normalized in {"exit", "quit"} or EXIT_PHRASE in normalized:
            break
        client.handle_typed_text(line)

    client.stop()
    return 0


def main() -> int:
    text_mode = "--text" in sys.argv[1:]

    print("JARVIS Desktop Client (Gateway Mode)")
    print(f"Gateway URL: {os.environ.get('GATEWAY_URL', 'http://localhost:8080')}")

    health = check_gateway_health()
    print(f"Gateway health: {health.get('status', 'unknown')}")
    if health.get("status") == "unreachable":
        print("\nERROR: Cannot reach the JARVIS Gateway.")
        print("Make sure the gateway and services are running:")
        print("  docker-compose up")
        return 1

    print("\nServices:")
    for name, status in health.get("services", {}).items():
        print(f"  {name}: {status.get('status', 'unknown')}")

    config = load_config()
    client = JarvisClient(config)

    if text_mode:
        return run_text_mode(client)

    client.start()

    print(f"\n{client.assistant_name} is listening. Just say '{WAKE_WORD}' to begin.")
    print("Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        client.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
