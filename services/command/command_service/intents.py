import random
import re

EMAIL_UNCONFIGURED_RESPONSE = (
    "Email delivery isn't configured yet, sir. I can open Gmail, but I can't send emails automatically from Jarvis yet."
)

LOCAL_RESPONSE_VARIANTS = {
    "how_are_you": [
        "I'm operating smoothly and ready to help.",
        "All systems are steady and I'm ready for your next command.",
        "I'm doing well and standing by for whatever you need.",
    ],
    "greeting": [
        "Hello. I'm here and ready.",
        "Hi. Ready when you are.",
        "Hello there. What would you like me to do?",
    ],
    "acknowledgement": [
        "Always ready, sir.",
        "At your service.",
        "Ready when you are.",
    ],
    "interesting_fact": [
        "Interesting fact: a teaspoon of neutron star material would weigh billions of tons on Earth.",
        "Interesting fact: octopuses have three hearts and blue blood.",
        "Interesting fact: honey never really spoils if it stays sealed.",
        "Interesting fact: Venus spins in the opposite direction from most planets.",
    ],
    "joke": [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "Why did the computer go to therapy? It had too many unresolved issues.",
        "Why do Java developers wear glasses? Because they don't see sharp.",
        "Why was the developer calm during the outage? He had already cached his panic.",
    ],
    "riddle": [
        "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I? An echo.",
        "What has keys but cannot open locks? A piano.",
        "What gets wetter the more it dries? A towel.",
        "What has a head, a tail, but no body? A coin.",
    ],
}

APP_TARGETS = {
    "chrome": {
        "label": "Google Chrome",
        "aliases": ["chrome", "google chrome", "browser", "google"],
    },
    "whatsapp": {
        "label": "WhatsApp",
        "aliases": ["whatsapp", "whats app"],
    },
    "notepad": {
        "label": "Notepad",
        "aliases": ["notepad", "notes"],
    },
    "calculator": {
        "label": "Calculator",
        "aliases": ["calculator", "calc"],
    },
    "explorer": {
        "label": "File Explorer",
        "aliases": ["file explorer", "explorer", "files"],
    },
    "settings": {
        "label": "Windows Settings",
        "aliases": ["settings", "windows settings"],
    },
    "youtube": {
        "label": "YouTube",
        "aliases": ["youtube"],
    },
}

_last_variant_by_key: dict[str, str] = {}


def normalize(value: str) -> str:
    return " ".join(value.lower().strip().split())


def choose_variant(key: str) -> str:
    options = LOCAL_RESPONSE_VARIANTS.get(key, [])
    if not options:
        return ""
    if len(options) == 1:
        choice = options[0]
    else:
        previous = _last_variant_by_key.get(key)
        available = [option for option in options if option != previous]
        choice = random.choice(available or options)
    _last_variant_by_key[key] = choice
    return choice


def matches_time(text: str) -> bool:
    # "time for", "time to" etc. are almost always a different sense of the
    # word ("time for lunch"), not a request for the clock.
    if re.search(r"\btime (?:for|to)\b", text):
        return False
    return (
        bool(re.search(r"\b(time|clock)\b", text))
        and bool(
            re.search(
                r"\b(what|whats|what's|current|currently|tell|give|check|know|show|now|is|it|hour)\b",
                text,
            )
        )
    ) or text.strip() in {"time", "what time", "what's the time", "what is the time"}


def matches_date(text: str) -> bool:
    exact_matches = {
        "date",
        "what date",
        "today's date",
        "what is today's date",
        "what day is it",
        "what day is it today",
    }
    if text.strip() in exact_matches:
        return True
    if not re.search(r"\b(date|day)\b", text):
        return False
    return bool(re.search(r"\b(what|current|today|tell|is|whats|what's)\b", text))


def matches_location(text: str) -> bool:
    phrases = ["where am i", "what is my location", "where are we", "current location"]
    return any(phrase in text for phrase in phrases)


def matches_weather(text: str) -> bool:
    return bool(re.search(r"\b(weather|temperature|forecast|climate)\b", text))


def matches_email_action(raw_text: str, text: str) -> bool:
    email_address_present = bool(re.search(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", raw_text))
    email_action_patterns = (
        r"\bsend (?:me )?(?:an? )?email\b",
        r"\bemail me\b",
        r"\bsend this to my email\b",
        r"\bemail reminder\b",
        r"\bsend (?:an? )?email reminder\b",
        r"\bconfigure email notifications?\b",
        r"\bemail notifications?\b",
        r"\bcan you email me\b",
        r"\bi already shared (?:you )?my email\b",
    )
    if any(re.search(pattern, text) for pattern in email_action_patterns):
        return True
    if email_address_present and re.search(r"\b(send|email|mail|message|notify|remind)\b", text):
        return True
    return False

def match_action(text: str) -> str | None:
    for action_key, config in APP_TARGETS.items():
        for alias in config["aliases"]:
            if alias in text:
                return action_key
    return None
