const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

const statusText = document.getElementById("statusText");
const subStatus = document.getElementById("subStatus");
const heardBadge = document.getElementById("heardBadge");
const weatherLocation = document.getElementById("weatherLocation");
const conversationLog = document.getElementById("conversationLog");
const weatherCard = document.getElementById("weatherCard");
const topicsList = document.getElementById("topicsList");
const deepDiveCard = document.getElementById("deepDiveCard");
const appsGrid = document.getElementById("appsGrid");
const commandInput = document.getElementById("commandInput");
const sendCommandBtn = document.getElementById("sendCommandBtn");
const topicsInput = document.getElementById("topicsInput");
const saveTopicsBtn = document.getElementById("saveTopicsBtn");
const orb = document.getElementById("orb");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const assistantName = "Jarvis";
const ownerName = "Omair";
const wakePhrase = "are you up jarvis";
const sleepPhrase = "alright jarvis thank you for your help";
const defaultTopics = [
  "artificial intelligence",
  "space exploration",
  "future gadgets",
  "global technology",
];
const storageKey = "jarvis-interests";

const appShortcuts = [
  {
    name: "YouTube",
    summary: "Open videos, news, and explainers in a new tab.",
    url: "https://www.youtube.com/",
  },
  {
    name: "Google Maps",
    summary: "Pull up directions and places quickly.",
    url: "https://maps.google.com/",
  },
  {
    name: "Gmail",
    summary: "Check your mail from Jarvis view.",
    url: "https://mail.google.com/",
  },
  {
    name: "Spotify",
    summary: "Play music while Jarvis keeps listening.",
    url: "https://open.spotify.com/",
  },
];

const state = {
  active: false,
  listening: false,
  recognition: null,
  awaitingExplorationChoice: null,
  spokenTopics: [],
};

function addMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = "message";
  const label = document.createElement("strong");
  label.textContent = role;
  const body = document.createElement("p");
  body.textContent = text;
  wrapper.append(label, body);
  conversationLog.prepend(wrapper);
}

function speak(text) {
  addMessage(assistantName, text);
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.volume = 1;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function updateStatus(main, detail, { active = false, listening = false } = {}) {
  statusText.textContent = main;
  subStatus.textContent = detail;
  orb.classList.toggle("active", active);
  orb.classList.toggle("listening", listening);
}

function renderApps() {
  appsGrid.innerHTML = "";
  appShortcuts.forEach((app) => {
    const card = document.createElement("div");
    card.className = "app-card";
    card.innerHTML = `
      <h4>${app.name}</h4>
      <p>${app.summary}</p>
      <a href="${app.url}" target="_blank" rel="noreferrer">Open app</a>
    `;
    appsGrid.appendChild(card);
  });
}

function getInterestTopics() {
  const saved = window.localStorage.getItem(storageKey);
  if (!saved) {
    return [...defaultTopics];
  }

  const parsed = saved
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  return parsed.length ? parsed : [...defaultTopics];
}

function saveInterestTopics() {
  const value = topicsInput.value.trim();
  const topics = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  if (!topics.length) {
    speak("Please enter at least one topic to save your interests.");
    return;
  }

  window.localStorage.setItem(storageKey, topics.join(", "));
  loadDailyTopics();
  speak("Your interest topics have been updated.");
}

function renderTopicCards(items) {
  topicsList.innerHTML = "";

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "topic-card";
    const title = document.createElement("h4");
    title.textContent = item.title;
    const summary = document.createElement("p");
    summary.textContent = item.summary;
    const button = document.createElement("button");
    button.dataset.topic = item.title;
    button.textContent = `Explore ${item.title}`;
    card.append(title, summary, button);
    topicsList.appendChild(card);
  });

  topicsList.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const topic = button.dataset.topic;
      showDeepDive(topic);
    });
  });
}

async function fetchWeather() {
  try {
    const coords = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) =>
          resolve({
            lat: position.coords.latitude,
            lon: position.coords.longitude,
          }),
        reject,
        { timeout: 10000 }
      );
    });

    const weatherResponse = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${coords.lat}&longitude=${coords.lon}&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=auto`
    );
    const weather = await weatherResponse.json();

    const geoResponse = await fetch(
      `https://geocode.maps.co/reverse?lat=${coords.lat}&lon=${coords.lon}`
    );
    const geo = await geoResponse.json();
    const locationName =
      geo.address?.city ||
      geo.address?.town ||
      geo.address?.state ||
      "Your area";

    weatherLocation.textContent = locationName;
    weatherCard.className = "stack-card";
    weatherCard.textContent = "";
    const forecast = document.createElement("p");
    forecast.append("Forecast for today in ");
    const location = document.createElement("strong");
    location.textContent = locationName;
    forecast.append(location, ".");
    const grid = document.createElement("div");
    grid.className = "weather-grid";
    grid.append(
      createWeatherMetric("Current", `${Math.round(weather.current.temperature_2m)}°C`),
      createWeatherMetric("High", `${Math.round(weather.daily.temperature_2m_max[0])}°C`),
      createWeatherMetric("Low", `${Math.round(weather.daily.temperature_2m_min[0])}°C`)
    );
    weatherCard.append(forecast, grid);

    speak(
      `Today's weather in ${locationName} is ${Math.round(
        weather.current.temperature_2m
      )} degrees Celsius, with a high of ${Math.round(
        weather.daily.temperature_2m_max[0]
      )} and a low of ${Math.round(weather.daily.temperature_2m_min[0])}.`
    );
  } catch (error) {
    weatherCard.className = "stack-card empty";
    weatherCard.innerHTML =
      "<p>I couldn't load the weather. Please allow location access and keep internet on.</p>";
    speak(
      "I couldn't load the weather right now. Please allow location access and try again."
    );
  }
}

function createWeatherMetric(label, value) {
  const metric = document.createElement("div");
  metric.className = "weather-metric";
  const labelNode = document.createElement("span");
  labelNode.textContent = label;
  const valueNode = document.createElement("strong");
  valueNode.textContent = value;
  metric.append(labelNode, valueNode);
  return metric;
}

async function fetchTopicSummary(topic) {
  try {
    const response = await fetch(
      `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(
        topic
      )}`
    );

    if (!response.ok) {
      throw new Error("Topic lookup failed");
    }

    const data = await response.json();
    return {
      title: data.title || topic,
      summary:
        data.extract ||
        `A fresh update is ready for ${topic}. Ask Jarvis to explore it.`,
    };
  } catch (error) {
    return {
      title: topic,
      summary: `I found ${topic} in your interest radar. Ask Jarvis to explore it in detail.`,
    };
  }
}

async function loadDailyTopics() {
  const interests = getInterestTopics();
  topicsInput.value = interests.join(", ");
  const summaries = await Promise.all(interests.map(fetchTopicSummary));
  renderTopicCards(summaries);
  state.spokenTopics = summaries.map((item) => item.title.toLowerCase());
}

async function showDeepDive(topic) {
  const item = await fetchTopicSummary(topic);
  deepDiveCard.className = "stack-card";
  deepDiveCard.textContent = "";
  const title = document.createElement("h4");
  title.textContent = item.title;
  const summary = document.createElement("p");
  summary.textContent = item.summary;
  deepDiveCard.append(title, summary);

  state.awaitingExplorationChoice = item.title;
  speak(
    `Here is your topic brief on ${item.title}. Would you like to explore this topic in detail?`
  );
}

async function translatePhrase(text, targetLanguage) {
  try {
    const response = await fetch(
      `https://api.mymemory.translated.net/get?q=${encodeURIComponent(
        text
      )}&langpair=en|${encodeURIComponent(targetLanguage)}`
    );
    const data = await response.json();
    const translated = data.responseData?.translatedText;
    if (!translated) {
      throw new Error("Missing translation");
    }
    speak(`Translation ready. ${translated}`);
  } catch (error) {
    speak(
      "I couldn't complete that translation right now. Try a phrase like translate hello to Spanish."
    );
  }
}

function narrateText(text) {
  speak(text);
}

function activateAssistant() {
  state.active = true;
  updateStatus("Jarvis active", "Awaiting your command, Master Omair.", {
    active: true,
    listening: true,
  });
  speak(`Yes Master ${ownerName}, I am online. How may I help you today?`);
}

function deactivateAssistant() {
  state.active = false;
  state.awaitingExplorationChoice = null;
  updateStatus("Standing by", "Wake phrase monitoring is still available.", {
    active: false,
    listening: true,
  });
  speak(`Alright Master ${ownerName}, call me if you need anything.`);
}

async function processCommand(rawText) {
  const text = rawText.toLowerCase().trim();
  heardBadge.textContent = rawText;
  addMessage(ownerName, rawText);

  if (text.includes(wakePhrase)) {
    activateAssistant();
    return;
  }

  if (text.includes(sleepPhrase)) {
    deactivateAssistant();
    return;
  }

  if (!state.active) {
    return;
  }

  if (
    state.awaitingExplorationChoice &&
    (text.includes("yes") || text.includes("explore"))
  ) {
    const topic = state.awaitingExplorationChoice;
    state.awaitingExplorationChoice = null;
    const item = await fetchTopicSummary(`${topic} technology future impact`);
    deepDiveCard.className = "stack-card";
    deepDiveCard.innerHTML = `
      <h4>${topic} Detailed View</h4>
      <p>${item.summary}</p>
    `;
    speak(`Diving deeper into ${topic}. ${item.summary}`);
    return;
  }

  if (state.awaitingExplorationChoice && text.includes("no")) {
    const topic = state.awaitingExplorationChoice;
    state.awaitingExplorationChoice = null;
    speak(`Understood. I will keep ${topic} on standby for later.`);
    return;
  }

  if (text.includes("weather") || text.includes("temperature")) {
    await fetchWeather();
    return;
  }

  if (text.includes("show topics") || text.includes("interests")) {
    await loadDailyTopics();
    speak("Your interest topics are now displayed on screen.");
    return;
  }

  if (text.includes("display apps") || text.includes("show apps")) {
    renderApps();
    speak("Your app shortcuts are ready on screen.");
    return;
  }

  if (text.includes("open ")) {
    const matchedApp = appShortcuts.find((app) =>
      text.includes(app.name.toLowerCase())
    );
    if (matchedApp) {
      window.open(matchedApp.url, "_blank", "noopener,noreferrer");
      speak(`Opening ${matchedApp.name} for you now.`);
      return;
    }
  }

  if (text.startsWith("explore ")) {
    await showDeepDive(rawText.slice(8).trim());
    return;
  }

  if (text.includes("translate")) {
    const match = rawText.match(/translate\s+(.+?)\s+to\s+([a-zA-Z]+)/i);
    if (match) {
      await translatePhrase(match[1], match[2]);
    } else {
      speak("Try saying translate hello to Spanish.");
    }
    return;
  }

  if (text.includes("narrate")) {
    const narration = rawText.replace(/.*narrate/i, "").trim();
    if (narration) {
      narrateText(narration);
    } else {
      speak("Tell me what you want narrated.");
    }
    return;
  }

  const matchedTopic = state.spokenTopics.find((topic) => text.includes(topic));
  if (matchedTopic) {
    await showDeepDive(matchedTopic);
    return;
  }

  speak(
    "I can help with weather, temperature, topics, apps, translation, narration, and topic exploration."
  );
}

function startRecognition() {
  if (!SpeechRecognition) {
    updateStatus(
      "Voice not supported",
      "Please open this in Chrome or Edge to use speech recognition."
    );
    addMessage(
      assistantName,
      "This browser does not support speech recognition. Please use Chrome or Edge."
    );
    return;
  }

  if (state.recognition) {
    state.recognition.start();
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    state.listening = true;
    updateStatus(
      state.active ? "Jarvis active" : "Standing by",
      state.active
        ? "Listening for your next command."
        : "Listening for the wake phrase.",
      { active: state.active, listening: true }
    );
  };

  recognition.onresult = async (event) => {
    const latest = event.results[event.results.length - 1][0].transcript;
    await processCommand(latest);
  };

  recognition.onerror = (event) => {
    addMessage(assistantName, `Voice recognition issue: ${event.error}`);
    updateStatus("Listening interrupted", "Use Start Listening to reconnect.", {
      active: state.active,
      listening: false,
    });
  };

  recognition.onend = () => {
    if (state.listening) {
      recognition.start();
    }
  };

  state.recognition = recognition;
  state.listening = true;
  recognition.start();
}

function stopRecognition() {
  state.listening = false;
  if (state.recognition) {
    state.recognition.stop();
  }
  updateStatus("Paused", "Voice listening is paused.", {
    active: false,
    listening: false,
  });
}

startBtn.addEventListener("click", startRecognition);
stopBtn.addEventListener("click", stopRecognition);
sendCommandBtn.addEventListener("click", async () => {
  const command = commandInput.value.trim();
  if (!command) {
    return;
  }
  commandInput.value = "";
  await processCommand(command);
});
commandInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    const command = commandInput.value.trim();
    if (!command) {
      return;
    }
    commandInput.value = "";
    await processCommand(command);
  }
});
saveTopicsBtn.addEventListener("click", saveInterestTopics);

renderApps();
loadDailyTopics();
addMessage(
  assistantName,
  `System ready. Say "${wakePhrase}" to activate ${assistantName}.`
);
