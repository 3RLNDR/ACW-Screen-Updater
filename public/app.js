const params = new URLSearchParams(window.location.search);
const storedPreference = localStorage.getItem("includeClasses");
const showRemoteImages = params.get("showImages") === "true";
const defaultIncludeClasses = storedPreference === null
  ? params.get("includeClasses") !== "false"
  : storedPreference === "true";
const isFileProtocol = window.location.protocol === "file:";
const isLocalServer = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const dataMode = isFileProtocol ? "preview" : (isLocalServer ? "server" : "static");
const apiOrigin = isLocalServer ? window.location.origin : "http://localhost:8080";
const assetBase = window.location.href;
const fullscreenThemeStorageKey = "fullscreenTheme";

const state = {
  includeClasses: defaultIncludeClasses,
  fullscreenTheme: params.get("theme") || localStorage.getItem(fullscreenThemeStorageKey) || "heritage",
  items: [],
  refreshTimer: null
};

const refreshMs = 5 * 60 * 1000;

const includeClassesToggle = document.querySelector("#includeClassesToggle");
const refreshButton = document.querySelector("#refreshButton");
const updatedAt = document.querySelector("#updatedAt");
const modeLabel = document.querySelector("#modeLabel");
const eventCount = document.querySelector("#eventCount");
const pageCounter = document.querySelector("#pageCounter");
const sourceStatus = document.querySelector("#sourceStatus");
const eventsGrid = document.querySelector("#eventsGrid");
const template = document.querySelector("#eventCardTemplate");
const fullscreenLink = document.querySelector("#fullscreenLink");
const fullscreenAllLink = document.querySelector("#fullscreenAllLink");
const fullscreenUrlDisplay = document.querySelector("#fullscreenUrlDisplay");
const themeOptions = document.querySelector("#themeOptions");

const fullscreenThemes = [
  { id: "heritage", label: "Heritage", preview: ["#f3ede4", "#b14b2d"] },
  { id: "midnight", label: "Midnight", preview: ["#1f2a44", "#5d80b8"] },
  { id: "evergreen", label: "Evergreen", preview: ["#17352f", "#7ea07b"] },
  { id: "spotlight", label: "Spotlight", preview: ["#2f2b2b", "#d2a14c"] }
];

const posterClasses = {
  "theatre and performance": "poster-theatre",
  music: "poster-music",
  comedy: "poster-comedy",
  films: "poster-film",
  film: "poster-film",
  exhibitions: "poster-exhibition",
  exhibition: "poster-exhibition",
  "special events": "poster-special",
  talks: "poster-talks",
  "adult workshops and activities": "poster-workshop",
  "children and young people's activities": "poster-workshop"
};

includeClassesToggle.checked = state.includeClasses;

includeClassesToggle.addEventListener("change", () => {
  state.includeClasses = includeClassesToggle.checked;
  localStorage.setItem("includeClasses", String(state.includeClasses));
  loadEvents();
});

refreshButton.addEventListener("click", () => {
  loadEvents(true);
});

function buildApiUrl(force = false) {
  const apiUrl = new URL("/api/events", apiOrigin);
  apiUrl.searchParams.set("includeClasses", String(state.includeClasses));
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

function formatRefreshTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Preview data";
  }
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function setModeLabel() {
  modeLabel.textContent = state.includeClasses
    ? "All events, classes and courses"
    : "Events only";
}

function getPosterClass(category, isClass) {
  if (isClass) {
    return "poster-workshop";
  }

  const normalized = (category || "").trim().toLowerCase();
  return posterClasses[normalized] || "poster-generic";
}

function getPosterKicker(item) {
  if (item.isClass) {
    return "Workshop";
  }

  const normalized = (item.category || "").trim();
  if (!normalized) {
    return "Event";
  }

  if (normalized === "Theatre and Performance") {
    return "Stage";
  }

  if (normalized === "Films") {
    return "Screen";
  }

  return normalized;
}

function getPosterMeta(item) {
  if (Array.isArray(item.meta) && item.meta.length) {
    return item.meta[0];
  }

  if (item.status) {
    return item.status;
  }

  return item.dateText || "Arts Centre Washington";
}

function escapeSvgText(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function getImageTheme(category, isClass) {
  if (isClass) {
    return {
      start: "#335042",
      end: "#78a88c",
      kicker: "WORKSHOP"
    };
  }

  const normalized = (category || "").trim().toLowerCase();
  switch (normalized) {
    case "theatre and performance":
      return { start: "#64281b", end: "#c66b37", kicker: "STAGE" };
    case "music":
      return { start: "#18404b", end: "#2f8f98", kicker: "LIVE" };
    case "comedy":
      return { start: "#6c2440", end: "#d35f59", kicker: "COMEDY" };
    case "films":
    case "film":
      return { start: "#1f2840", end: "#5369a8", kicker: "SCREEN" };
    case "exhibitions":
    case "exhibition":
      return { start: "#34553d", end: "#8cb36d", kicker: "GALLERY" };
    case "special events":
      return { start: "#5b3317", end: "#d2a14c", kicker: "SPECIAL" };
    case "talks":
      return { start: "#4a312e", end: "#b98267", kicker: "TALKS" };
    default:
      return { start: "#31463f", end: "#1d2523", kicker: "EVENT" };
  }
}

function buildFallbackImage(item) {
  const theme = getImageTheme(item.category, item.isClass);
  const title = escapeSvgText(item.title || "Upcoming event");
  const subtitle = escapeSvgText((Array.isArray(item.meta) && item.meta[0]) || item.dateText || "Arts Centre Washington");
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${theme.start}"/>
          <stop offset="100%" stop-color="${theme.end}"/>
        </linearGradient>
      </defs>
      <rect width="1200" height="675" fill="url(#g)"/>
      <circle cx="1060" cy="90" r="180" fill="rgba(255,255,255,0.10)"/>
      <path d="M140 675 L340 0 L410 0 L210 675 Z" fill="rgba(255,255,255,0.08)"/>
      <text x="72" y="110" fill="rgba(255,255,255,0.85)" font-size="34" font-family="Arial, sans-serif" letter-spacing="6">${theme.kicker}</text>
      <text x="72" y="250" fill="#ffffff" font-size="86" font-weight="700" font-family="Georgia, serif">${title}</text>
      <text x="72" y="318" fill="rgba(255,255,255,0.86)" font-size="34" font-family="Arial, sans-serif">${subtitle}</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function buildPoster(card, item) {
  const poster = card.querySelector(".event-poster");
  const kicker = card.querySelector(".event-kicker");
  const posterTitle = card.querySelector(".event-poster-title");
  const posterMeta = card.querySelector(".event-poster-meta");

  poster.hidden = false;
  poster.className = `event-poster ${getPosterClass(item.category, item.isClass)}`;
  kicker.textContent = getPosterKicker(item);
  posterTitle.textContent = item.title || "Untitled event";
  posterMeta.textContent = getPosterMeta(item);
}

function getFallbackItems() {
  return [
    {
      title: "Wired",
      category: "Theatre and Performance",
      isClass: false,
      dateText: "16 Apr 2026",
      startTime: "7pm",
      cost: "\u00A312",
      status: "",
      meta: ["Suitable for ages 11+"],
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
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    },
    {
      title: "Patrick Monahan - The Good, The Pat & The Ugly",
      category: "Comedy",
      isClass: false,
      dateText: "24 Apr 2026",
      startTime: "8pm",
      cost: "\u00A316",
      status: "",
      meta: ["Stand-up comedy night"],
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    },
    {
      title: "Mr Drayton's Rock Docs: Purple Rain",
      category: "Films",
      isClass: false,
      dateText: "22 Apr 2026",
      startTime: "2pm",
      cost: "\u00A37",
      status: "",
      meta: ["Film screening"],
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    },
    {
      title: "Present Continuous, Present Imperfect",
      category: "Exhibitions",
      isClass: false,
      dateText: "15 - 25 Apr 2026",
      cost: "Free",
      status: "Free",
      meta: ["Gallery exhibition"],
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    },
    {
      title: "Summer Craft & Makers Fair",
      category: "Special Events",
      isClass: false,
      dateText: "18 Jul 2026",
      cost: "Free",
      status: "Free",
      meta: ["Venue-wide special event"],
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
      link: "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
    }
  ];
}

function renderThemeOptions() {
  themeOptions.innerHTML = "";

  fullscreenThemes.forEach((theme) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "theme-option";
    button.dataset.theme = theme.id;
    button.setAttribute("aria-pressed", String(state.fullscreenTheme === theme.id));
    button.innerHTML = `
      <span class="theme-option-swatch" style="--theme-a:${theme.preview[0]}; --theme-b:${theme.preview[1]};"></span>
      <span>${theme.label}</span>
    `;
    button.addEventListener("click", () => {
      state.fullscreenTheme = theme.id;
      localStorage.setItem(fullscreenThemeStorageKey, theme.id);
      renderThemeOptions();
      updateFullscreenLink();
    });
    themeOptions.appendChild(button);
  });
}

function updateFullscreenLink() {
  const eventsOnlyUrl = new URL("./fullscreen.html", window.location.href);
  eventsOnlyUrl.searchParams.set("includeClasses", "false");
  eventsOnlyUrl.searchParams.set("theme", state.fullscreenTheme);
  fullscreenLink.href = eventsOnlyUrl.toString();
  fullscreenUrlDisplay.href = eventsOnlyUrl.toString();
  fullscreenUrlDisplay.textContent = eventsOnlyUrl.toString();

  const allItemsUrl = new URL("./fullscreen.html", window.location.href);
  allItemsUrl.searchParams.set("includeClasses", "true");
  allItemsUrl.searchParams.set("theme", state.fullscreenTheme);
  fullscreenAllLink.href = allItemsUrl.toString();
}

function renderPayload(payload, sourceLabel) {
  const payloadItems = Array.isArray(payload.items) ? payload.items : [];
  state.items = payloadItems.filter((item) => state.includeClasses || !item.isClass);

  updatedAt.textContent = formatRefreshTime(payload.fetchedAt || new Date().toISOString());
  eventCount.textContent = String(state.items.length);
  sourceStatus.textContent = sourceLabel;

  renderPage();
}

function renderPage() {
  const page = state.items ?? [];
  eventsGrid.innerHTML = "";

  page.forEach((item) => {
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector(".event-card");
    const image = fragment.querySelector(".event-image");
    const category = fragment.querySelector(".event-category");
    const status = fragment.querySelector(".event-status");
    const title = fragment.querySelector(".event-title");
    const date = fragment.querySelector(".event-date");
    const meta = fragment.querySelector(".event-meta");
    const link = fragment.querySelector(".event-link");

    category.textContent = item.category || "Event";
    title.textContent = item.title || "Untitled event";
    date.textContent = item.dateText || "Date to be confirmed";
    meta.textContent = Array.isArray(item.meta) ? item.meta.join(" | ") : "";
    status.textContent = item.status || (item.isClass ? "Class or course" : "Upcoming event");
    status.classList.toggle("is-muted", !item.status);
    link.href = item.link || "#";
    buildPoster(card, item);

    const imageSource = normalizeAssetUrl(item.imageLocal)
      || (showRemoteImages && item.image ? item.image : null)
      || buildFallbackImage(item);

    if (imageSource) {
      image.hidden = false;
      image.src = imageSource;
      image.alt = item.title || "Event artwork";
      image.addEventListener("error", () => {
        image.hidden = true;
        image.removeAttribute("src");
      }, { once: true });
    } else {
      image.hidden = true;
      image.removeAttribute("src");
    }

    if (!item.link) {
      link.remove();
    }

    eventsGrid.appendChild(fragment);
  });

  pageCounter.textContent = `Showing all ${state.items.length} events`;
}

async function loadEvents(force = false) {
  setModeLabel();
  sourceStatus.textContent = force ? "Refreshing event data..." : "Loading event data...";

  try {
    if (dataMode === "preview") {
      throw new Error("Direct file mode");
    }

    const response = await fetch(
      dataMode === "server" ? buildApiUrl(force) : buildStaticDataUrl(force),
      { cache: "no-store" }
    );
    if (!response.ok) {
      let message = `Request failed with ${response.status}`;
      try {
        const errorPayload = await response.json();
        if (errorPayload?.error) {
          message = errorPayload.error;
        }
      } catch {
        // Ignore JSON parse failures and keep the status code message.
      }
      throw new Error(message);
    }

    const payload = await response.json();
    renderPayload(
      payload,
      dataMode === "static"
        ? (payload.sourceUrl ? `Published from ${new URL(payload.sourceUrl).host}` : "Published site data")
        : (payload.sourceUrl ? `Live from ${new URL(payload.sourceUrl).host}` : "Live data loaded")
    );
  } catch (error) {
    const fallbackItems = getFallbackItems().filter((item) => state.includeClasses || !item.isClass);
    renderPayload({
      fetchedAt: null,
      total: fallbackItems.length,
      items: fallbackItems
    }, dataMode === "preview"
      ? "Preview data loaded from local file"
      : `Live feed unavailable (${error.message}), showing preview data`);
  }
}

function startRefreshLoop() {
  clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(() => loadEvents(true), refreshMs);
}

setModeLabel();
renderThemeOptions();
updateFullscreenLink();
loadEvents();
startRefreshLoop();
