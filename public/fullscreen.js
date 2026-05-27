import { getNextRenderableSlide } from "./slide-sequence.mjs";

const params = new URLSearchParams(window.location.search);
const isFileProtocol = window.location.protocol === "file:";
const isLocalServer = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const forcedDataMode = document.body.dataset.displayMode;
const dataMode = forcedDataMode || (isFileProtocol ? "preview" : (isLocalServer ? "server" : "static"));
const includeClasses = params.get("includeClasses") === "true";
const slideDelayMs = Math.max(5000, Number.parseInt(params.get("delay") || "15000", 10) || 15000);
const keepAliveMs = Math.max(15000, Number.parseInt(params.get("keepAliveMs") || "30000", 10) || 30000);
const apiOrigin = window.location.origin;
const assetBase = window.location.href;
const fullscreenThemeStorageKey = "fullscreenTheme";
const fullscreenTheme = params.get("theme") || localStorage.getItem(fullscreenThemeStorageKey) || "heritage";

document.body.dataset.fullscreenTheme = fullscreenTheme;
localStorage.setItem(fullscreenThemeStorageKey, fullscreenTheme);

const state = {
  slides: [],
  currentIndex: 0,
  rotateTimer: null,
  refreshTimer: null,
  keepAliveTimer: null,
  progressTimer: null,
  progressStartedAt: 0,
  failedVideoIds: new Set()
};

const refreshMs = 5 * 60 * 1000;

const slideVideo = document.querySelector("#slideVideo");
const slideImage = document.querySelector("#slideImage");
const slidePoster = document.querySelector("#slidePoster");
const slideAvailability = document.querySelector("#slideAvailability");
const slideCategory = document.querySelector("#slideCategory");
const slideCounter = document.querySelector("#slideCounter");
const slideTitle = document.querySelector("#slideTitle");
const slideDate = document.querySelector("#slideDate");
const slideDateNote = document.querySelector("#slideDateNote");
const slideDetails = document.querySelector("#slideDetails");
const slideQrPanel = document.querySelector("#slideQrPanel");
const slideQrImage = document.querySelector("#slideQrImage");
const slideQrLink = document.querySelector("#slideQrLink");
const slideProgress = document.querySelector("#slideProgress");
const slideProgressBar = document.querySelector("#slideProgressBar");
const keepAlivePulse = document.querySelector("#keepAlivePulse");
const keepAliveVideo = document.querySelector("#keepAliveVideo");

function buildApiUrl(force = false) {
  const apiUrl = new URL("/api/slides", apiOrigin);
  apiUrl.searchParams.set("includeClasses", String(includeClasses));
  if (force) {
    apiUrl.searchParams.set("_", Date.now().toString());
  }
  return apiUrl.toString();
}

function buildStaticDataUrl(force = false) {
  const dataUrl = new URL("./slides.json", window.location.href);
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
  return String(value || "").replace(/Ã‚Â£/g, "\u00A3").trim();
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

function formatQrLinkLabel(eventUrl) {
  try {
    const url = new URL(eventUrl);
    return `${url.host}${url.pathname === "/" ? "" : url.pathname}`;
  } catch {
    return eventUrl;
  }
}

function updateQrPanel(item) {
  if (!slideQrPanel || !slideQrImage || !slideQrLink) {
    return;
  }

  const eventUrl = getValidEventUrl(item?.link);
  const qrLocalUrl = normalizeAssetUrl(item?.qrLocal);

  if (!eventUrl) {
    slideQrPanel.hidden = true;
    slideQrPanel.dataset.qrStatus = "hidden";
    slideQrImage.hidden = true;
    slideQrImage.removeAttribute("src");
    slideQrImage.alt = "";
    slideQrImage.onload = null;
    slideQrImage.onerror = null;
    slideQrLink.removeAttribute("href");
    slideQrLink.textContent = "";
    return;
  }

  slideQrPanel.hidden = false;
  slideQrImage.alt = `QR code for ${item.title || "event details"}`;
  slideQrLink.href = eventUrl;
  slideQrLink.textContent = formatQrLinkLabel(eventUrl);
  slideQrImage.onload = null;
  slideQrImage.onerror = null;

  if (!qrLocalUrl) {
    slideQrPanel.dataset.qrStatus = "unavailable";
    slideQrImage.hidden = true;
    slideQrImage.removeAttribute("src");
    return;
  }

  slideQrPanel.dataset.qrStatus = "loading";
  slideQrImage.hidden = false;
  slideQrImage.removeAttribute("src");
  slideQrImage.onload = () => {
    slideQrPanel.dataset.qrStatus = "ready";
  };
  slideQrImage.onerror = () => {
    slideQrPanel.dataset.qrStatus = "unavailable";
    slideQrImage.hidden = true;
    slideQrImage.removeAttribute("src");
  };
  slideQrImage.src = qrLocalUrl;
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
      cost: "\u00A312",
      status: "",
      meta: ["Suitable for ages 11+"],
      imageLocal: null,
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    },
    {
      title: "10CCLO",
      category: "Music",
      isClass: false,
      dateText: "17 - 18 Apr 2026",
      startTime: "7:30pm",
      cost: "\u00A318",
      status: "Limited Availability",
      meta: ["Live music performance"],
      imageLocal: null,
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    },
    {
      title: "Creative Sketchbook Club",
      category: "Adult Workshops and Activities",
      isClass: true,
      dateText: "20 Apr 2026",
      startTime: "6pm",
      cost: "\u00A38",
      status: "",
      meta: ["Weekly creative class"],
      imageLocal: null,
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    }
  ];

  return items.filter((item) => includeClasses || !item.isClass);
}

function toEventSlide(item) {
  return {
    type: "event",
    id: item.id || item.title || Math.random().toString(36).slice(2),
    eventId: item.id || item.title || "",
    title: item.title,
    category: item.category,
    dateText: item.dateText,
    startTime: item.startTime,
    cost: item.cost,
    status: item.status,
    meta: item.meta,
    link: item.link,
    imageLocal: item.imageLocal,
    qrLocal: item.qrLocal,
    isClass: item.isClass
  };
}

function normalizeCompareText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function isExhibition(item) {
  return normalizeCompareText(item?.category) === "exhibitions";
}

function getExhibitionDateRange(item) {
  const primaryMeta = Array.isArray(item?.meta) ? item.meta.find((value) => String(value || "").trim()) : "";
  return normalizeDisplayText(primaryMeta);
}

function getSlideDateContent(item) {
  const defaultDate = normalizeDisplayText(item?.dateText) || "Date to be confirmed";

  if (!isExhibition(item)) {
    return { primary: defaultDate, note: "" };
  }

  const exhibitionRange = getExhibitionDateRange(item);
  if (!exhibitionRange) {
    return { primary: defaultDate, note: "" };
  }

  return {
    primary: exhibitionRange,
    note: defaultDate ? `Open until ${defaultDate}` : ""
  };
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

  const titleLength = slideTitle.textContent.trim().length;
  const hasVisibleQr = Boolean(slideQrPanel && !slideQrPanel.hidden);
  const computed = window.getComputedStyle(slideTitle);
  let fontSize = Number.parseFloat(computed.fontSize);

  if (hasVisibleQr && titleLength >= 60) {
    fontSize = Math.min(fontSize, 64);
  }

  if (hasVisibleQr && titleLength >= 80) {
    fontSize = Math.min(fontSize, 56);
  }

  if (titleLength >= 100) {
    fontSize = Math.min(fontSize, 50);
  }

  slideTitle.style.fontSize = `${fontSize}px`;
  slideTitle.style.lineHeight = "0.95";

  let measuredLineHeight = Number.parseFloat(window.getComputedStyle(slideTitle).lineHeight);
  if (!Number.isFinite(measuredLineHeight)) {
    measuredLineHeight = fontSize * 0.95;
  }

  const maxLines = hasVisibleQr ? 4 : 5;
  const maxHeight = measuredLineHeight * maxLines + 2;

  while (slideTitle.offsetHeight > maxHeight && fontSize > 40) {
    fontSize -= 2;
    slideTitle.style.fontSize = `${fontSize}px`;
    slideTitle.style.lineHeight = "0.95";
  }
}

function restartProgressBar(durationMs) {
  if (!slideProgress || !slideProgressBar) {
    return;
  }

  const shouldAnimate = state.slides.length > 1;
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
    const progress = Math.max(2, Math.min(100, (elapsed / durationMs) * 100));
    slideProgressBar.style.width = `${progress}%`;
  }, 100);
}

function stopCurrentPlayback() {
  clearTimeout(state.rotateTimer);
  clearInterval(state.progressTimer);
  if (slideVideo) {
    slideVideo.pause();
    slideVideo.onended = null;
    slideVideo.onerror = null;
    slideVideo.removeAttribute("src");
    slideVideo.load();
  }
}

function scheduleAdvance(durationMs) {
  clearTimeout(state.rotateTimer);
  restartProgressBar(durationMs);
  if (state.slides.length <= 1) {
    return;
  }
  state.rotateTimer = setTimeout(() => {
    advanceToNextSlide();
  }, durationMs);
}

function renderEventSlide(index, item) {
  const imageSource = normalizeAssetUrl(item.imageLocal) || buildFallbackImage(item);
  const theme = getTheme(item.category, item.isClass);

  slideVideo.hidden = true;
  slidePoster.hidden = false;
  slideImage.hidden = false;
  slidePoster.style.background = `linear-gradient(135deg, ${theme.start}, ${theme.end})`;
  slideImage.src = imageSource;
  slideImage.alt = item.title || "Event artwork";
  slideImage.onerror = () => {
    slideImage.hidden = true;
    slideImage.removeAttribute("src");
  };

  slideCategory.textContent = item.category || "Event";
  setAvailabilityBadge(item.status);
  slideTitle.textContent = item.title || "Untitled event";
  const dateContent = getSlideDateContent(item);
  slideDate.textContent = dateContent.primary;
  if (slideDateNote) {
    slideDateNote.hidden = !dateContent.note;
    slideDateNote.textContent = dateContent.note;
  }
  slideDetails.innerHTML = "";
  const detailValues = [item.category, item.startTime, item.cost].filter(Boolean);
  detailValues.forEach((value) => {
    const pill = document.createElement("span");
    pill.className = "fullscreen-detail-pill";
    pill.textContent = normalizeDisplayText(value);
    slideDetails.appendChild(pill);
  });
  updateQrPanel(item);
  slideCounter.textContent = `${index + 1} / ${state.slides.length}`;
  requestAnimationFrame(() => fitTitleToFiveLines());
  scheduleAdvance(slideDelayMs);
}

function renderVideoSlide(index, slide) {
  const durationMs = Math.max(5000, (Number(slide.durationSeconds) || 20) * 1000);
  slideVideo.hidden = false;
  slidePoster.hidden = true;
  slideImage.hidden = true;
  slideImage.removeAttribute("src");
  slideQrPanel.hidden = true;
  slideAvailability.hidden = true;
  slideDetails.innerHTML = "";
  slideCategory.textContent = "Promo video";
  slideTitle.textContent = slide.title || "Promotional video";
  slideDate.textContent = "Playing now";
  if (slideDateNote) {
    slideDateNote.hidden = true;
    slideDateNote.textContent = "";
  }

  const detail = document.createElement("span");
  detail.className = "fullscreen-detail-pill";
  detail.textContent = "Video";
  slideDetails.appendChild(detail);

  slideCounter.textContent = `${index + 1} / ${state.slides.length}`;
  requestAnimationFrame(() => fitTitleToFiveLines());

  const videoUrl = normalizeAssetUrl(slide.src);
  if (!videoUrl) {
    state.failedVideoIds.add(slide.id);
    advanceToNextSlide();
    return;
  }

  slideVideo.src = videoUrl;
  slideVideo.onended = () => advanceToNextSlide();
  slideVideo.onerror = () => {
    state.failedVideoIds.add(slide.id);
    advanceToNextSlide();
  };

  scheduleAdvance(durationMs);
  slideVideo.play().catch(() => {
    state.failedVideoIds.add(slide.id);
    advanceToNextSlide();
  });
}

function findNextRenderableIndex(startIndex) {
  const slide = getNextRenderableSlide(state.slides, startIndex, state.failedVideoIds);
  if (!slide) {
    return -1;
  }
  return state.slides.findIndex((candidate, index) => {
    if (index < startIndex) {
      return false;
    }
    return candidate.id === slide.id && candidate.type === slide.type;
  }) !== -1
    ? state.slides.findIndex((candidate, index) => index >= startIndex && candidate.id === slide.id && candidate.type === slide.type)
    : state.slides.findIndex((candidate) => candidate.id === slide.id && candidate.type === slide.type);
}

function renderSlide(index) {
  if (!state.slides.length) {
    return;
  }

  stopCurrentPlayback();
  const resolvedIndex = findNextRenderableIndex(index);
  if (resolvedIndex === -1) {
    return;
  }

  state.currentIndex = resolvedIndex;
  const slide = state.slides[resolvedIndex];
  if (slide.type === "video") {
    renderVideoSlide(resolvedIndex, slide);
    return;
  }

  renderEventSlide(resolvedIndex, slide);
}

function advanceToNextSlide() {
  if (!state.slides.length) {
    return;
  }
  const nextIndex = (state.currentIndex + 1) % state.slides.length;
  renderSlide(nextIndex);
}

function filterSlidesForDisplay(slides) {
  const eventVisibility = new Map();
  slides.forEach((slide) => {
    if (slide.type === "event") {
      eventVisibility.set(slide.eventId || slide.id, includeClasses || !slide.isClass);
    }
  });

  return slides.filter((slide) => {
    if (slide.type === "event") {
      return includeClasses || !slide.isClass;
    }
    return eventVisibility.get(slide.eventId) !== false;
  });
}

function renderPayload(payload) {
  const payloadSlides = Array.isArray(payload.slides)
    ? payload.slides
    : (Array.isArray(payload.items) ? payload.items.map(toEventSlide) : []);
  state.slides = filterSlidesForDisplay(payloadSlides);
  if (!state.slides.length) {
    state.slides = getFallbackItems().map(toEventSlide);
  }
  renderSlide(0);
}

async function loadSlides(force = false) {
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

    renderPayload(await response.json());
  } catch {
    renderPayload({ items: getFallbackItems() });
  }
}

function startRefreshLoop() {
  clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(() => loadSlides(true), refreshMs);
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

loadSlides();
startRefreshLoop();
startKeepAliveLoop();
startKeepAliveVideo();
