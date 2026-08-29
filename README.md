# Jarvis for Omair

A local desktop Jarvis-style assistant for your Windows laptop.

## What it does

- Listens for `are you up jarvis`
- Keeps a dedicated on-screen Jarvis interface open on your laptop
- Shows daily weather and temperature
- Displays interest topics on its own interface
- Opens common apps and web tools
- Speaks replies back to you
- Supports narration requests
- Attempts simple translation requests
- Lets you explore topics in more detail
- Signs off when you say `alright jarvis thank you for your help`

## Run it

First-time setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Quickest way after setup:

```bat
start-jarvis.bat
```

This launches the desktop app. The launcher prefers `.venv\Scripts\pythonw.exe` and falls back to your system Python if the project virtual environment is not ready yet.

## Manual desktop launch

```powershell
.\.venv\Scripts\python jarvis_desktop.py
```

## Environment variables

Copy `.env.example` into your own local environment setup and set secrets outside Git-tracked files.

```powershell
$env:WEATHER_API_KEY="your_weatherapi_key"
$env:OPENWEATHER_API_KEY="your_openweathermap_key"
```

Weather keys in the environment take priority over `jarvis_config.json`. Keep `weather_api_key` and `openweather_api_key` blank in the config file.

## Testing

Run the smoke tests after setup or after any code change:

```powershell
.\.venv\Scripts\python test_jarvis_smoke.py
```

The smoke suite checks config shape, source syntax, model paths, memory structure, and safe note-file routing.

## Voice examples

- `are you up jarvis`
- `what is today's weather`
- `show topics that interest me`
- `explore artificial intelligence`
- `translate hello to spanish`
- `narrate the future belongs to builders`
- `open calculator`
- `open notepad`
- `display apps`
- `alright jarvis thank you for your help`

## Files

- `jarvis_desktop.py` - the native desktop interface
- `jarvis_speech_listener.ps1` - Windows speech recognition bridge
- `jarvis_speak.ps1` - Windows voice reply script
- `start-jarvis.bat` - quick desktop launcher
- `install-startup-shortcut.ps1` - optional helper to make Jarvis launch when Windows starts
- `start-jarvis-web.bat` - older browser-based version if you want the original web UI

## Optional startup helper

If you want Jarvis to open automatically when Windows starts, this helper creates a shortcut in your Startup folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-startup-shortcut.ps1
```

To remove it later:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-startup-shortcut.ps1 -Remove
```

## Browser fallback

The original browser build is legacy and is not the active development path. It is still available for reference:

```bat
start-jarvis-web.bat
```

## Notes

- Weather, translation, and topic summaries need internet access when the app is running.
- The desktop app uses Vosk for offline-first speech recognition and Piper for primary voice output.
- App launching is implemented for common built-in Windows apps and a few web destinations.
- You can change the owner name, assistant name, and interest topics from inside the desktop interface.
- Voice-created files and folders are confined to the `notes/` directory under the configured workspace.
- Memory is stored in `memory.json` as `{ "memories": {}, "reminders": [] }`. To reset personal memory, blank values inside `memories` and keep `reminders` as a list.
