import re
from datetime import datetime, timedelta
from pydantic import BaseModel
import httpx
from typing import Optional

from command_service.intents import (
    APP_TARGETS,
    EMAIL_UNCONFIGURED_RESPONSE,
    choose_variant,
    match_action,
    matches_date,
    matches_email_action,
    matches_location,
    matches_time,
    matches_weather,
    normalize,
)
from command_service.timeloc import build_time_response
from command_service.weather import get_local_timezone, get_location_response, get_weather_response
from command_service.config import settings

class CommandResult(BaseModel):
    handled: bool
    response: str
    full_response: Optional[str] = None
    status: str = "Jarvis Activated"
    focus_text: Optional[str] = None
    action: Optional[str] = None
    action_target: Optional[str] = None
    action_data: Optional[dict] = None

class CommandHandler:
    def __init__(self, memory_client: httpx.AsyncClient):
        self.memory_client = memory_client

    def describe_capabilities(self) -> str:
        return (
            "I can open desktop apps, tell you the time and date, estimate your location, fetch weather, "
            "create folders and files, write text into files, control the ambient theme music, remember personal details, manage reminders, "
            "and route open-ended questions to my AI brain."
        )

    def _sanitize_name(self, value: str) -> str:
        cleaned = value.strip().strip('"').strip("'")
        cleaned = cleaned.replace("\\", " ").replace("/", " ")
        cleaned = re.sub(r"[^a-zA-Z0-9._\- ]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(". ")
        if len(cleaned) > 64:
            cleaned = cleaned[:64].strip(". ")
        return cleaned or "note"

    def _ensure_text_extension(self, file_name: str) -> str:
        if "." in file_name:
            return file_name
        return f"{file_name}.txt"

    def _memory_list_to_dict(self, memories: list[dict] | dict) -> dict:
        if isinstance(memories, dict):
            return memories
        if not isinstance(memories, list):
            return {}
        converted: dict = {}
        for memory in memories:
            if not isinstance(memory, dict):
                continue
            key = memory.get("key")
            if key:
                converted[str(key)] = memory.get("value")
        return converted

    def _parse_reminder_time(self, value: str) -> datetime | None:
        text = " ".join(str(value or "").strip().split()).lower()
        if not text:
            return None

        reference = datetime.now()
        day_offset = 0
        if text.startswith("tomorrow "):
            day_offset = 1
            text = text.removeprefix("tomorrow ").strip()
        if text.startswith("today "):
            text = text.removeprefix("today ").strip()
        if text.startswith("at "):
            text = text.removeprefix("at ").strip()

        parsed_time = None
        for fmt in ("%I %p", "%I:%M %p", "%H:%M"):
            try:
                parsed_time = datetime.strptime(text.upper(), fmt)
                break
            except ValueError:
                continue
        if parsed_time is None:
            return None

        scheduled = reference.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=0,
            microsecond=0,
        ) + timedelta(days=day_offset)
        if day_offset == 0 and scheduled <= reference:
            scheduled += timedelta(days=1)
        return scheduled

    async def _handle_memory_and_reminders(self, raw_text: str, text: str) -> Optional[CommandResult]:
        if "what do you remember about me" in text or "what do you remember" in text:
            try:
                resp = await self.memory_client.get("/memories")
                memories = self._memory_list_to_dict(resp.json())
            except Exception:
                memories = {}
            if not memories:
                return CommandResult(handled=True, response="I have not stored anything personal about you yet.")
            return CommandResult(handled=True, response=self._format_memory_summary(memories), focus_text="Memory snapshot refreshed.")

        if "show my reminders" in text or "list my reminders" in text:
            try:
                resp = await self.memory_client.get("/reminders")
                reminders = resp.json()
            except Exception:
                reminders = []
            if not reminders:
                return CommandResult(handled=True, response="You do not have any active reminders right now.")
            return CommandResult(handled=True, response=self._format_reminder_summary(reminders), focus_text="Reminder list refreshed.")

        remind_to_match = re.search(r"remind me to (.+?) at (.+)$", raw_text, re.IGNORECASE)
        remind_at_match = re.search(r"remind me at (.+?)(?: to (.+))?$", raw_text, re.IGNORECASE)
        if remind_to_match or remind_at_match:
            reminder_text = ""
            reminder_time_text = ""
            if remind_to_match:
                reminder_text = remind_to_match.group(1).strip()
                reminder_time_text = remind_to_match.group(2).strip()
            else:
                reminder_time_text = remind_at_match.group(1).strip()
                reminder_text = (remind_at_match.group(2) or "check in with you").strip()

            try:
                scheduled = self._parse_reminder_time(reminder_time_text)
                if scheduled is None:
                    return CommandResult(handled=True, response="Tell me the reminder time more clearly, for example 5 PM or 5:30 PM.")
                resp = await self.memory_client.post(
                    "/reminders",
                    json={"text": reminder_text, "scheduled_at": scheduled.isoformat()},
                )
                if resp.status_code == 201:
                    data = resp.json()
                    when = datetime.fromisoformat(data["scheduled_at"]).strftime("%I:%M %p").lstrip("0")
                    return CommandResult(handled=True, response=f"Reminder set for {when}: {reminder_text}.", focus_text="Reminder saved.")
                return CommandResult(handled=True, response="Tell me the reminder time more clearly, for example 5 PM or 5:30 PM.")
            except Exception:
                return CommandResult(handled=True, response="I couldn't save that reminder.")

        name_match = re.search(r"\bmy name is (.+)$", raw_text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip().strip(".").strip()
            if not name:
                return CommandResult(handled=True, response="I didn't catch your name clearly.")
            try:
                await self.memory_client.post("/memories", json={"key": "name", "value": name})
                return CommandResult(handled=True, response=f"I'll remember that. Your name is {name}.", focus_text="Stored personal memory.")
            except Exception:
                return CommandResult(handled=True, response="I couldn't save your name.")

        remember_match = re.search(r"\bremember that (.+)$", raw_text, re.IGNORECASE)
        dont_forget_match = re.search(r"\bdon't forget (.+)$", raw_text, re.IGNORECASE)
        note_match = remember_match or dont_forget_match
        if note_match:
            note = note_match.group(1).strip().strip(".").strip()
            if not note:
                return CommandResult(handled=True, response="Tell me what you want me to remember.")
            try:
                resp = await self.memory_client.get("/memories")
                memories = self._memory_list_to_dict(resp.json())
                notes = memories.get("notes", [])
                if not isinstance(notes, list):
                    notes = []
                notes.append(note)
                await self.memory_client.post("/memories", json={"key": "notes", "value": notes})
                return CommandResult(handled=True, response="Understood. I'll remember that.", focus_text="Stored personal note.")
            except Exception:
                return CommandResult(handled=True, response="I couldn't save that note.")

        return None

    def _format_memory_summary(self, memories: list[dict] | dict) -> str:
        memories = self._memory_list_to_dict(memories)
        parts = []
        name = memories.get("name")
        if name:
            parts.append(f"Your name is {name}.")
        notes = memories.get("notes", [])
        if isinstance(notes, list) and notes:
            parts.append(f"I remember: {'; '.join(notes[:3])}.")
        if not parts:
            return "I have not stored anything personal about you yet."
        return " ".join(parts)

    def _format_reminder_summary(self, reminders: list[dict]) -> str:
        entries = []
        for reminder in reminders[:3]:
            try:
                when = datetime.fromisoformat(str(reminder.get("scheduled_at"))).strftime("%I:%M %p").lstrip("0")
            except Exception:
                when = "an unknown time"
            entries.append(f"{when}: {reminder.get('text', 'Reminder')}")
        return "Here are your reminders: " + " | ".join(entries) + "."

    def _handle_music_commands(self, text: str) -> Optional[CommandResult]:
        has_music_target = any(term in text for term in ("theme music", "theme song", "theme", "music", "song"))
        if not has_music_target:
            return None

        if any(phrase in text for phrase in ("restart the theme", "restart theme", "restart the music", "restart music", "restart the song")):
            return CommandResult(handled=True, response="Restarting the theme music.", focus_text="Ambient theme restarting.", action="music", action_target="restart")
        if any(phrase in text for phrase in ("stop the theme", "stop the music", "stop music", "pause the music", "pause music", "turn off the music", "mute the music", "stop the song")):
            return CommandResult(handled=True, response="Stopping the theme music.", focus_text="Ambient theme paused.", action="music", action_target="stop")
        if any(phrase in text for phrase in ("play the theme", "play theme", "play the music", "play music", "play the song", "start the music", "start music", "resume the music", "resume music", "turn on the music")):
            return CommandResult(handled=True, response="Playing the theme music.", focus_text="Ambient theme engaged.", action="music", action_target="play")
        return None

    def _handle_file_operations(self, text: str) -> Optional[CommandResult]:
        folder_patterns = [
            r"create (?:a )?folder(?: named| called)? (.+)$",
            r"create (?:a )?folder in files(?: named| called)? (.+)$",
            r"create the folder(?: named| called)? (.+)$",
            r"make (?:a )?folder(?: named| called)? (.+)$",
        ]
        for pattern in folder_patterns:
            folder_match = re.search(pattern, text)
            if folder_match:
                folder_name = self._sanitize_name(folder_match.group(1))
                if not folder_name:
                    return CommandResult(handled=True, response="Tell me the folder name you want me to create.")
                return CommandResult(handled=True, response=f"Creating the folder {folder_name}.", action="file_op", action_target="create_folder", action_data={"name": folder_name})

        file_patterns = [
            r"create (?:a )?file(?: named| called)? (.+)$",
            r"create (?:a )?note(?: in notepad)?(?: named| called)? (.+)$",
            r"create the note(?: in notepad)?(?: named| called)? (.+)$",
            r"make (?:a )?note(?: in notepad)?(?: named| called)? (.+)$",
        ]
        for pattern in file_patterns:
            file_match = re.search(pattern, text)
            if file_match:
                file_name = self._ensure_text_extension(self._sanitize_name(file_match.group(1)))
                if not file_name:
                    return CommandResult(handled=True, response="Tell me the file name you want me to create.")
                return CommandResult(handled=True, response=f"Creating the note called {file_name}.", action="file_op", action_target="create_file", action_data={"name": file_name})

        write_match = re.search(r"write (.+?) into ([^\n]+)$", text)
        if write_match:
            content = write_match.group(1).strip()
            file_name = self._ensure_text_extension(self._sanitize_name(write_match.group(2)))
            if not file_name:
                return CommandResult(handled=True, response="Tell me which file should receive that text.")
            return CommandResult(handled=True, response=f"Writing your text into {file_name}.", action="file_op", action_target="write_file", action_data={"name": file_name, "content": content})

        type_match = re.search(r"type (.+?) in (?:the )?notepad$", text)
        if type_match:
            content = type_match.group(1).strip()
            file_name = "jarvis_notepad_note.txt"
            return CommandResult(handled=True, response=f"Writing that into {file_name}.", action="file_op", action_target="write_file", action_data={"name": file_name, "content": content})

        return None

    def _open_action(self, action_key: str) -> CommandResult:
        action = APP_TARGETS.get(action_key, APP_TARGETS["chrome"])
        label = action["label"]
        return CommandResult(handled=True, response=f"Opening {label}.", focus_text=f"Focused action: {label}", action="launch", action_target=action_key)

    async def handle(self, user_input: str, selected_action: str = "", last_action: str = "") -> CommandResult:
        text = normalize(user_input)
        if not text:
            return CommandResult(handled=True, response="I didn't catch anything to act on.")

        if matches_email_action(raw_text=user_input, text=text):
            return CommandResult(handled=True, response=EMAIL_UNCONFIGURED_RESPONSE, focus_text="Email delivery is not configured.")

        if re.fullmatch(r"(?:hi|hello|hey)(?:\s+jarvis)?", text) or any(
            phrase in text for phrase in ("good morning", "good afternoon", "good evening")
        ):
            return CommandResult(handled=True, response=choose_variant("greeting"))
        if text in {"always ready", "always ready sir", "always ready for you", "always ready for you sir"}:
            return CommandResult(handled=True, response=choose_variant("acknowledgement"))
        if "how are you" in text:
            return CommandResult(handled=True, response=choose_variant("how_are_you"))
        if re.search(r"\binteresting\b", text) or "tell me something" in text:
            return CommandResult(handled=True, response=choose_variant("interesting_fact"))
        if re.search(r"\b(joke|funny)\b", text):
            return CommandResult(handled=True, response=choose_variant("joke"))
        if re.search(r"\b(riddle|brain teaser|puzzle)\b", text):
            return CommandResult(handled=True, response=choose_variant("riddle"))
        if "who are you talking to" in text or "who are you speaking to" in text:
            return CommandResult(handled=True, response="I'm talking to you. No one else is part of this conversation through me.")
        if "somebody listening" in text or "someone listening" in text or "anybody listening" in text:
            return CommandResult(handled=True, response="I only process what your microphone sends to Jarvis. I cannot tell whether another app or device is listening.")
        if text in {"who are you", "jarvis who are you"} or text.startswith("jarvis who are you"):
            return CommandResult(handled=True, response="I'm Jarvis, your local assistant on this laptop.")
        if text in {"help", "help me"} or "what can you do" in text:
            return CommandResult(handled=True, response=self.describe_capabilities(), focus_text="Ask for apps, weather, files, or open-ended AI questions.")
        if "what is this" in text:
            label = APP_TARGETS.get(selected_action, APP_TARGETS["chrome"])["label"]
            return CommandResult(handled=True, response=f"This is your Jarvis command center. The current highlighted action is {label}.", focus_text=f"Focused action: {label}")

        memory_result = await self._handle_memory_and_reminders(user_input, text)
        if memory_result is not None:
            return memory_result

        if matches_location(text):
            return CommandResult(handled=True, response=get_location_response())
        if matches_weather(text):
            weather_resp = get_weather_response(user_input, text, settings.weather_api_key, settings.openweather_api_key)
            return CommandResult(handled=True, response=weather_resp)
        music_result = self._handle_music_commands(text)
        if music_result is not None:
            return music_result
        if matches_time(text):
            # Resolve against the raw text so city casing survives for the
            # spoken reply ("Tokyo", not "tokyo").
            result = build_time_response(
                user_input,
                default_timezone=settings.default_timezone,
                geolocate=get_local_timezone,
            )
            return CommandResult(
                handled=True,
                response=result.response,
                focus_text=result.focus_text,
            )
        if matches_date(text):
            now = datetime.now()
            return CommandResult(handled=True, response=f"Today's date is {now.strftime('%A, %B %d, %Y')}.")
        file_result = self._handle_file_operations(text)
        if file_result is not None:
            return file_result

        if text == "open this" or "open this" in text:
            return self._open_action(selected_action)

        if "open that" in text or "open the last one" in text:
            return self._open_action(last_action)

        action_key = match_action(text)
        if action_key and ("open" in text or "launch" in text or text.endswith("jarvis")):
            return self._open_action(action_key)

        if text.startswith("open "):
            remainder = text.removeprefix("open ").strip()
            action_key = match_action(remainder)
            if action_key:
                return self._open_action(action_key)
            return CommandResult(handled=True, response=f"I heard the request to open {remainder}, but I do not have a configured launcher for it yet.")

        return CommandResult(handled=False, response="", action="ai_fallback")
