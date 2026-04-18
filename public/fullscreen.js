const params = new URLSearchParams(window.location.search);
const isFileProtocol = window.location.protocol === "file:";
const isLocalServer = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const forcedDataMode = document.body.dataset.displayMode;
const dataMode = forcedDataMode || (isFileProtocol ? "preview" : (isLocalServer ? "server" : "static"));
const includeClasses = params.get("includeClasses") === "true";
const slideDelayMs = Math.max(5000, Number.parseInt(params.get("delay") || "15000", 10) || 15000);
const keepAliveMs = Math.max(15000, Number.parseInt(params.get("keepAliveMs") || "30000", 10) || 30000);
const apiOrigin = isLocalServer ? window.location.origin : "http://localhost:8080";
const assetBase = window.location.href;
const fullscreenThemeStorageKey = "fullscreenTheme";
const fullscreenTheme = params.get("theme") || localStorage.getItem(fullscreenThemeStorageKey) || "heritage";

document.body.dataset.fullscreenTheme = fullscreenTheme;
localStorage.setItem(fullscreenThemeStorageKey, fullscreenTheme);

const state = {
  items: [],
  currentIndex: 0,
  rotateTimer: null,
  refreshTimer: null,
  keepAliveTimer: null,
  progressTimer: null,
  progressStartedAt: 0
};

const refreshMs = 5 * 60 * 1000;

const slideImage = document.querySelector("#slideImage");
const slidePoster = document.querySelector("#slidePoster");
const slideAvailability = document.querySelector("#slideAvailability");
const slideCategory = document.querySelector("#slideCategory");
const slideCounter = document.querySelector("#slideCounter");
const slideTitle = document.querySelector("#slideTitle");
const slideDate = document.querySelector("#slideDate");
const slideDetails = document.querySelector("#slideDetails");
const slideQrPanel = document.querySelector("#slideQrPanel");
const slideQrImage = document.querySelector("#slideQrImage");
const slideQrLink = document.querySelector("#slideQrLink");
const slideProgress = document.querySelector("#slideProgress");
const slideProgressBar = document.querySelector("#slideProgressBar");
const keepAlivePulse = document.querySelector("#keepAlivePulse");
const keepAliveVideo = document.querySelector("#keepAliveVideo");

function buildApiUrl(force = false) {
  const apiUrl = new URL("/api/events", apiOrigin);
  apiUrl.searchParams.set("includeClasses", String(includeClasses));
  if (force) {
    apiUrl.searchParams.set("_", Date.now().toString());
  }
  return apiUrl.toString();
}

function buildStaticDataUrl(force = false) {
  const dataUrl = new URL("./events.json", window.location.href);
  if (force) {
    dataUrl.searchParams.set("_", Date.now().toString());
  }
  return dataUrl.toString();
}

function normalizeAssetUrl(value) {
  if (!value) {
    return null;
  }

  if (value.startsWith("http://") || value.startsWith("https://") || value.startsWith("data:")) {
    return value;
  }

  return new URL(value, assetBase).toString();
}

function normalizeDisplayText(value) {
  return String(value || "").replace(/Â£/g, "\u00A3").trim();
}

function getValidEventUrl(value) {
  if (!value) {
    return null;
  }

  try {
    const url = new URL(value, window.location.href);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

function updateQrPanel(item) {
  if (!slideQrPanel || !slideQrImage || !slideQrLink) {
    return;
  }

  const eventUrl = getValidEventUrl(item?.link);
  if (!eventUrl) {
    slideQrPanel.hidden = true;
    slideQrImage.hidden = true;
    slideQrImage.removeAttribute("src");
    slideQrImage.alt = "";
    slideQrLink.removeAttribute("href");
    slideQrLink.textContent = "";
    return;
  }

  const qrUrl = new URL("https://api.qrserver.com/v1/create-qr-code/");
  qrUrl.searchParams.set("size", "180x180");
  qrUrl.searchParams.set("format", "svg");
  qrUrl.searchParams.set("margin", "0");
  qrUrl.searchParams.set("data", eventUrl);

  slideQrPanel.hidden = false;
  slideQrImage.hidden = false;
  slideQrImage.src = qrUrl.toString();
  slideQrImage.alt = `QR code for ${item.title || "event details"}`;
  slideQrLink.href = eventUrl;
  slideQrLink.textContent = eventUrl;
}

function escapeSvgText(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function getTheme(category, isClass) {
  if (isClass) {
    return { start: "#335042", end: "#78a88c", label: "WORKSHOP" };
  }

  switch ((category || "").trim().toLowerCase()) {
    case "theatre and performance":
      return { start: "#64281b", end: "#c66b37", label: "STAGE" };
    case "music":
      return { start: "#18404b", end: "#2f8f98", label: "LIVE" };
    case "comedy":
      return { start: "#6c2440", end: "#d35f59", label: "COMEDY" };
    case "films":
      return { start: "#1f2840", end: "#5369a8", label: "SCREEN" };
    case "exhibitions":
      return { start: "#34553d", end: "#8cb36d", label: "GALLERY" };
    case "special events":
      return { start: "#5b3317", end: "#d2a14c", label: "SPECIAL" };
    case "talks":
      return { start: "#4a312e", end: "#b98267", label: "TALKS" };
    default:
      return { start: "#31463f", end: "#1d2523", label: "EVENT" };
  }
}

function buildFallbackImage(item) {
  const theme = getTheme(item.category, item.isClass);
  const title = escapeSvgText(item.title || "Upcoming event");
  const subtitle = escapeSvgText(item.dateText || "Arts Centre Washington");
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${theme.start}"/>
          <stop offset="100%" stop-color="${theme.end}"/>
        </linearGradient>
      </defs>
      <rect width="1600" height="900" fill="url(#g)"/>
      <circle cx="1410" cy="120" r="260" fill="rgba(255,255,255,0.10)"/>
      <path d="M220 900 L460 0 L560 0 L320 900 Z" fill="rgba(255,255,255,0.08)"/>
      <text x="100" y="140" fill="rgba(255,255,255,0.86)" font-size="42" font-family="Arial, sans-serif" letter-spacing="8">${theme.label}</text>
      <text x="100" y="335" fill="#ffffff" font-size="110" font-weight="700" font-family="Georgia, serif">${title}</text>
      <text x="100" y="415" fill="rgba(255,255,255,0.9)" font-size="44" font-family="Arial, sans-serif">${subtitle}</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function getFallbackItems() {
  const items = [
    {
      title: "Wired",
      category: "Theatre and Performance",
      isClass: false,
      dateText: "16 Apr 2026",
      startTime: "7pm",
      cost: "£12",
      status: "",
      meta: ["Suitable for ages 11+"],
      imageLocal: null
    },
    {
      title: "10CCLO",
      category: "Music",
      isClass: false,
      dateText: "17 - 18 Apr 2026",
      startTime: "7:30pm",
      cost: "£18",
      status: "Limited Availability",
      meta: ["Live music performance"],
      imageLocal: null
    },
    {
      title: "Creative Sketchbook Club",
      category: "Adult Workshops and Activities",
      isClass: true,
      dateText: "20 Apr 2026",
      startTime: "6pm",
      cost: "£8",
      status: "",
      meta: ["Weekly creative class"],
      imageLocal: null
    }
  ];

  return items.filter((item) => includeClasses || !item.isClass);
}

function normalizeCompareText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function setAvailabilityBadge(status) {
  const normalized = String(status || "").trim().toLowerCase();
  slideAvailability.hidden = true;
  slideAvailability.textContent = "";
  slideAvailability.className = "fullscreen-availability";

  if (normalized === "limited availability") {
    slideAvailability.hidden = false;
    slideAvailability.textContent = "Limited Availability";
    slideAvailability.classList.add("is-limited");
    return;
  }

  if (normalized === "sold out") {
    slideAvailability.hidden = false;
    slideAvailability.textContent = "Sold Out";
    slideAvailability.classList.add("is-sold-out");
  }
}

function fitTitleToFiveLines() {
  slideTitle.style.fontSize = "";
  slideTitle.style.lineHeight = "";

  const computed = window.getComputedStyle(slideTitle);
  let fontSize = Number.parseFloat(computed.fontSize);
  const lineHeight = Number.parseFloat(computed.lineHeight) || fontSize * 0.95;
  const maxHeight = lineHeight * 5 + 2;

  while (slideTitle.offsetHeight > maxHeight && fontSize > 44) {
    fontSize -= 2;
    slideTitle.style.fontSize = `${fontSize}px`;
    slideTitle.style.lineHeight = "0.95";
  }
}

function restartProgressBar() {
  if (!slideProgress || !slideProgressBar) {
    return;
  }

  const shouldAnimate = state.items.length > 1;
  slideProgress.hidden = !shouldAnimate;
  clearInterval(state.progressTimer);

  if (!shouldAnimate) {
    slideProgressBar.style.width = "100%";
    return;
  }

  state.progressStartedAt = Date.now();
  slideProgressBar.style.width = "2%";

  state.progressTimer = setInterval(() => {
    const elapsed = Date.now() - state.progressStartedAt;
    const progress = Math.max(2, Math.min(100, (elapsed / slideDelayMs) * 100));
    slideProgressBar.style.width = `${progress}%`;
  }, 100);
}

function renderSlide(index) {
  if (!state.items.length) {
    return;
  }

  state.currentIndex = index;
  const item = state.items[index];
  const imageSource = normalizeAssetUrl(item.imageLocal) || buildFallbackImage(item);
  const theme = getTheme(item.category, item.isClass);

  slidePoster.style.background = `linear-gradient(135deg, ${theme.start}, ${theme.end})`;
  slideImage.hidden = false;
  slideImage.src = imageSource;
  slideImage.alt = item.title || "Event artwork";
  slideImage.onerror = () => {
    slideImage.hidden = true;
    slideImage.removeAttribute("src");
  };

  slideCategory.textContent = item.category || "Event";
  setAvailabilityBadge(item.status);
  slideTitle.textContent = item.title || "Untitled event";
  slideDate.textContent = item.dateText || "Date to be confirmed";
  slideDetails.innerHTML = "";
  const detailValues = [item.category, item.startTime, item.cost].filter(Boolean);
  detailValues.forEach((value) => {
    const pill = document.createElement("span");
    pill.className = "fullscreen-detail-pill";
    pill.textContent = normalizeDisplayText(value);
    slideDetails.appendChild(pill);
  });
  updateQrPanel(item);
  slideCounter.textContent = `${index + 1} / ${state.items.length}`;
  restartProgressBar();
  requestAnimationFrame(() => fitTitleToFiveLines());
}

function startRotation() {
  clearInterval(state.rotateTimer);
  if (state.items.length <= 1) {
    return;
  }

  state.rotateTimer = setInterval(() => {
    const nextIndex = (state.currentIndex + 1) % state.items.length;
    renderSlide(nextIndex);
  }, slideDelayMs);
}

function renderPayload(payload, sourceLabel) {
  const payloadItems = Array.isArray(payload.items) ? payload.items : [];
  state.items = payloadItems.filter((item) => includeClasses || !item.isClass);
  renderSlide(0);
  startRotation();
}

async function loadEvents(force = false) {
  try {
    if (dataMode === "preview") {
      throw new Error("Direct file mode");
    }

    const response = await fetch(
      dataMode === "server" ? buildApiUrl(force) : buildStaticDataUrl(force),
      { cache: "no-store" }
    );
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const payload = await response.json();
    renderPayload(payload, payload.sourceUrl
      ? `Live from ${new URL(payload.sourceUrl).host}`
      : "Live data loaded");
  } catch (error) {
    renderPayload({
      fetchedAt: null,
      items: getFallbackItems()
    }, dataMode === "preview"
      ? "Preview data loaded from local file"
      : `Live feed unavailable (${error.message}), showing preview data`);
  }
}

function startRefreshLoop() {
  clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(() => loadEvents(true), refreshMs);
}

function emitKeepAlive() {
  const heartbeat = Date.now().toString();
  ["mousemove", "pointermove", "touchmove"].forEach((eventName) => {
    window.dispatchEvent(new Event(eventName));
    document.dispatchEvent(new Event(eventName));
  });

  if (keepAlivePulse) {
    keepAlivePulse.dataset.heartbeat = heartbeat;
    keepAlivePulse.textContent = heartbeat;
  }
}

function startKeepAliveLoop() {
  clearInterval(state.keepAliveTimer);
  emitKeepAlive();
  state.keepAliveTimer = setInterval(emitKeepAlive, keepAliveMs);
}

async function startKeepAliveVideo() {
  if (!keepAliveVideo || typeof HTMLCanvasElement === "undefined") {
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = 2;
  canvas.height = 2;

  const context = canvas.getContext("2d");
  if (!context || typeof canvas.captureStream !== "function") {
    return;
  }

  let frame = 0;
  const drawFrame = () => {
    frame += 1;
    context.fillStyle = frame % 2 === 0 ? "#000000" : "#010101";
    context.fillRect(0, 0, canvas.width, canvas.height);
  };

  drawFrame();
  setInterval(drawFrame, 1000);

  try {
    keepAliveVideo.srcObject = canvas.captureStream(1);
    await keepAliveVideo.play();
  } catch (error) {
    keepAlivePulse.dataset.videoKeepAlive = `failed:${error.message}`;
  }
}

loadEvents();
startRefreshLoop();
startKeepAliveLoop();
startKeepAliveVideo();
