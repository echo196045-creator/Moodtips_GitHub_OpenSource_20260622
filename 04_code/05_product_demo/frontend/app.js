const API_BASE =
  window.location.protocol.startsWith("http")
    ? ""
    : "http://127.0.0.1:8000";

window.HeKouApiBase = API_BASE;

const rootModules = window.HeKouModules || {};
const { constants, utils } = rootModules;

if (!constants || !utils) {
  throw new Error("Frontend modules failed to load.");
}

const {
  appName,
  appTag,
  appSlogan,
  appSubline,
  homePromise,
  moodQuadrants,
  moods,
  priceOptions,
  temperatureOptions,
  caffeineOptions,
  tasteOptions,
  weekLabels
} = constants;

const {
  escapeHtml,
  formatCurrency,
  formatMonthKey,
  getCalendarDates,
  getMonthKey,
  renderImage,
  shiftMonthKey
} = utils;

const STEP_META = {
  mood: { counter: "01 / 03", label: "情绪" },
  filters: { counter: "02 / 03", label: "偏好" },
  result: { counter: "03 / 03", label: "结果" }
};

const state = {
  apiReady: false,
  view: "home",
  form: createDefaultForm(),
  retrySeed: 0,
  submitting: false,
  accepting: false,
  uploadingImage: false,
  result: null,
  notice: null,
  calendarByMonth: {},
  recapByMonth: {},
  currentMonth: getMonthKey(new Date())
};

let rootEl = null;
let noticeTimer = 0;

document.addEventListener("DOMContentLoaded", async () => {
  rootEl = document.getElementById("app");
  document.body.addEventListener("click", onBodyClick);
  document.body.addEventListener("change", onBodyChange);
  renderApp();
  await hydrate();
});

function createDefaultForm() {
  return {
    moodCode: "",
    priceBand: "any",
    temperaturePref: "any",
    caffeinePref: "any",
    tasteTags: []
  };
}

async function hydrate() {
  await checkHealth();
  await ensureMonthData(state.currentMonth);
  renderApp();
}

function onBodyClick(event) {
  const actionEl = event.target.closest("[data-action]");
  if (actionEl) {
    if ("disabled" in actionEl && actionEl.disabled) {
      return;
    }
    handleAction(actionEl.dataset.action, actionEl.dataset.value || "");
    return;
  }

  const moodEl = event.target.closest("[data-mood-code]");
  if (moodEl && state.view === "mood") {
    state.form.moodCode = moodEl.dataset.moodCode || "";
    state.view = "filters";
    state.result = null;
    state.retrySeed = 0;
    renderApp();
    return;
  }

  const chipEl = event.target.closest("[data-chip-group]");
  if (chipEl) {
    toggleChip(chipEl.dataset.chipGroup || "", chipEl.dataset.chipValue || "");
  }
}

function onBodyChange(event) {
  const inputEl = event.target.closest("[data-upload-input]");
  if (!inputEl || !inputEl.files || !inputEl.files.length) {
    return;
  }
  const file = inputEl.files[0];
  inputEl.value = "";
  void uploadResultImage(file);
}

function handleAction(action, value) {
  switch (action) {
    case "go-home":
      state.view = "home";
      renderApp();
      break;
    case "start-flow":
      state.view = "mood";
      renderApp();
      break;
    case "back-step":
      handleBackStep();
      break;
    case "submit":
      if (!state.submitting) {
        void submitRecommendation(false);
      }
      break;
    case "reroll":
      if (!state.submitting) {
        state.retrySeed += 1;
        void submitRecommendation(true);
      }
      break;
    case "accept":
      if (!state.accepting) {
        void acceptRecommendation();
      }
      break;
    case "open-upload":
      openUploadInput();
      break;
    case "month-prev":
      state.currentMonth = shiftMonthKey(state.currentMonth, -1);
      void ensureMonthData(state.currentMonth);
      renderApp();
      break;
    case "month-next":
      state.currentMonth = shiftMonthKey(state.currentMonth, 1);
      void ensureMonthData(state.currentMonth);
      renderApp();
      break;
    case "set-price":
      state.form.priceBand = value || "any";
      renderApp();
      break;
    case "set-temperature":
      state.form.temperaturePref = value || "any";
      renderApp();
      break;
    case "set-caffeine":
      state.form.caffeinePref = value || "any";
      renderApp();
      break;
    default:
      break;
  }
}

function openUploadInput() {
  const input = document.querySelector("[data-upload-input]");
  if (input instanceof HTMLInputElement) {
    input.click();
  }
}

function handleBackStep() {
  if (state.view === "result") {
    state.view = "filters";
  } else if (state.view === "filters") {
    state.view = "mood";
  } else if (state.view === "mood") {
    state.view = "home";
  }
  renderApp();
}

function toggleChip(group, value) {
  if (group !== "taste") {
    return;
  }

  const next = new Set(state.form.tasteTags);
  if (next.has(value)) {
    next.delete(value);
  } else if (next.size < 3) {
    next.add(value);
  } else {
    setNotice("口味最多选 3 个。", "info");
    return;
  }

  state.form.tasteTags = [...next];
  renderApp();
}

async function checkHealth() {
  try {
    await getJSON(`${API_BASE}/health`);
    state.apiReady = true;
  } catch (error) {
    state.apiReady = false;
    setNotice("本地服务未连接。", "error", 4200);
  }
}

async function ensureMonthData(monthKey) {
  await Promise.all([loadCalendar(monthKey), loadRecap(monthKey)]);
}

async function loadCalendar(monthKey) {
  if (state.calendarByMonth[monthKey]) {
    return;
  }
  try {
    state.calendarByMonth[monthKey] = await getJSON(
      `${API_BASE}/api/accept-records/calendar?month=${encodeURIComponent(monthKey)}`
    );
  } catch (error) {
    state.calendarByMonth[monthKey] = { month: monthKey, count: 0, items: [] };
  }
}

async function loadRecap(monthKey) {
  if (state.recapByMonth[monthKey]) {
    return;
  }
  try {
    state.recapByMonth[monthKey] = await getJSON(
      `${API_BASE}/api/accept-records/recap?month=${encodeURIComponent(monthKey)}`
    );
  } catch (error) {
    state.recapByMonth[monthKey] = buildEmptyRecap(monthKey);
  }
}

async function submitRecommendation(isReroll) {
  if (!state.apiReady) {
    setNotice("本地服务暂时不可用。", "error");
    return;
  }

  if (!state.form.moodCode) {
    state.view = "mood";
    setNotice("先选一个情绪。", "info");
    renderApp();
    return;
  }

  state.submitting = true;
  state.view = "result";
  if (!isReroll) {
    state.result = null;
  }
  renderApp();

  try {
    const previousBrandCode = isReroll ? (state.result?.recommendation?.brand_code || "") : "";
    const response = await postJSON(`${API_BASE}/api/recommendation/simple`, {
      mood_code: state.form.moodCode,
      price_band: state.form.priceBand,
      temperature_pref: state.form.temperaturePref,
      caffeine_pref: state.form.caffeinePref,
      taste_tags: state.form.tasteTags,
      retry_seed: state.retrySeed,
      exclude_brand_code: previousBrandCode
    });
    state.result = response;
    state.view = "result";
  } catch (error) {
    state.view = isReroll && state.result?.recommendation ? "result" : "filters";
    if (isReroll && state.result?.recommendation) {
      setNotice("先看这一杯。", "info", 3000);
    } else {
      setNotice("这组条件下暂时没找到合适的。", "error", 3600);
    }
  } finally {
    state.submitting = false;
    renderApp();
  }
}

async function acceptRecommendation() {
  if (!state.result?.recommendation) {
    return;
  }

  const selectedMood = getSelectedMood();
  const item = state.result.recommendation;
  state.accepting = true;
  renderApp();

  try {
    await postJSON(`${API_BASE}/api/accept-records`, {
      session_id: state.result.session_id,
      mood_code: state.form.moodCode,
      mood_label: getMoodQuadrant(selectedMood)?.label || "",
      budget_band: state.form.priceBand,
      temperature_pref: state.form.temperaturePref,
      caffeine_pref: state.form.caffeinePref,
      preference_tags: state.form.tasteTags,
      sku_id: item.item_id,
      sku_name: item.item_name,
      brand_code: item.brand_code,
      brand_name: item.brand_name,
      image_url: item.image_url,
      base_price: item.base_price,
      currency_code: item.currency_code || "CNY",
      serving_note: item.default_serving_note,
      encouragement_copy: item.encouragement
    });

    state.calendarByMonth[state.currentMonth] = null;
    state.recapByMonth[state.currentMonth] = null;
    await ensureMonthData(state.currentMonth);

    state.form = createDefaultForm();
    state.retrySeed = 0;
    state.result = null;
    state.view = "home";
    setNotice("已记录。", "success", 2400);
  } catch (error) {
    setNotice("记录失败，请再试一次。", "error", 3200);
  } finally {
    state.accepting = false;
    renderApp();
  }
}

async function uploadResultImage(file) {
  if (!state.result?.recommendation) {
    return;
  }
  if (!file || !file.type || !file.type.startsWith("image/")) {
    setNotice("请选一张图片。", "error", 2600);
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    setNotice("图片太大了，换个 8MB 以内的吧。", "error", 3200);
    return;
  }

  state.uploadingImage = true;
  renderApp();

  try {
    const dataUrl = await readFileAsDataUrl(file);
    const item = state.result.recommendation;
    const response = await postJSON(`${API_BASE}/api/simple/visual-overrides`, {
      item_id: item.item_id,
      brand_code: item.brand_code,
      item_name: item.item_name,
      image_data_url: dataUrl,
      badge_text: "用户上传",
      image_mode: "user_uploaded",
      note: file.name || "用户上传图片",
      submitter_note: file.name || "用户上传图片",
      original_file_name: file.name || ""
    });

    state.result.recommendation.image_review_id = response.review_id || "";
    state.result.recommendation.image_review_status = response.review_status || "pending";
    setNotice("已提交待审核，审核后同步。", "success", 2800);
  } catch (error) {
    setNotice("提交失败，稍后再试。", "error", 3200);
  } finally {
    state.uploadingImage = false;
    renderApp();
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("read-failed"));
    reader.readAsDataURL(file);
  });
}

function getSelectedMood() {
  return moods.find((item) => item.code === state.form.moodCode) || null;
}

function renderApp() {
  if (!rootEl) {
    return;
  }

  rootEl.dataset.view = state.view;
  document.body.classList.toggle("body-locked", state.view === "mood" || state.view === "filters");
  document.documentElement.classList.toggle("body-locked", state.view === "mood" || state.view === "filters");

  rootEl.innerHTML = `
    <div class="app-shell app-shell--${escapeHtml(state.view)}">
      <div class="halo halo-a"></div>
      <div class="halo halo-b"></div>
      ${renderHeader()}
      ${renderNotice()}
      <main class="main-shell main-shell--${escapeHtml(state.view)}">
        ${renderCurrentView()}
      </main>
    </div>
  `;
}

function renderHeader() {
  if (state.view === "home") {
    return `
      <header class="topbar home-topbar">
        <button class="brand-lockup" data-action="go-home" type="button">
          <span class="brand-tag">${escapeHtml(appTag)}</span>
          <span class="brand-name">${escapeHtml(appName)}</span>
        </button>
      </header>
    `;
  }

  const meta = STEP_META[state.view] || { counter: "", label: "" };
  return `
    <header class="topbar step-topbar">
      <button class="back-button" data-action="back-step" type="button">返回</button>
      <div class="step-meta">
        <span class="step-counter">${escapeHtml(meta.counter)}</span>
        <span class="step-label">${escapeHtml(meta.label)}</span>
      </div>
      <button class="brand-mini" data-action="go-home" type="button">${escapeHtml(appName)}</button>
    </header>
  `;
}

function renderNotice() {
  if (!state.notice?.message) {
    return "";
  }
  return `<div class="notice notice-${escapeHtml(state.notice.tone || "info")}">${escapeHtml(state.notice.message)}</div>`;
}

function renderCurrentView() {
  if (state.view === "mood") {
    return renderMoodView();
  }
  if (state.view === "filters") {
    return renderFiltersView();
  }
  if (state.view === "result") {
    return renderResultView();
  }
  return renderHomeView();
}

function renderHomeView() {
  return `
    <section class="panel home-hero">
      <div class="hero-copy">
        <p class="eyebrow">${escapeHtml(appTag)}</p>
        <h1>${escapeHtml(appName)}</h1>
        <p class="subline">${escapeHtml(appSlogan)}</p>
        <p class="promise">${escapeHtml(appSubline)}</p>
      </div>
      <div class="hero-orbit">
        <span>${escapeHtml(homePromise)}</span>
      </div>
    </section>

    <section class="home-insight-grid">
      ${renderCalendarCard()}
      ${renderRecapCard()}
    </section>

    <section class="panel entry-panel">
      <h2>开始</h2>
      <button class="primary-button home-start-button" data-action="start-flow" type="button">
        选心情
      </button>
    </section>
  `;
}

function renderMoodView() {
  return `
    <section class="step-screen">
      <div class="step-card mood-stage">
        <div class="step-copy-block">
          <h1 class="step-title">现在呢</h1>
        </div>
        <div class="mood-grid mood-grid--stage">
          ${moods.map(renderMoodCard).join("")}
        </div>
      </div>
    </section>
  `;
}

function renderFiltersView() {
  const selectedMood = getSelectedMood();
  const moodBadge = selectedMood
    ? `
        <div class="selected-mood-badge" style="--mood-color:${escapeHtml(getMoodColor(selectedMood))}">
          <img class="selected-mood-sticker" src="${escapeHtml(selectedMood.sticker)}" alt="" />
          <span>${escapeHtml(selectedMood.title)}</span>
        </div>
      `
    : "";

  return `
    <section class="step-screen">
      <div class="step-card filter-stage">
        <div class="step-copy-block">
          <h1 class="step-title">再筛一下</h1>
          ${moodBadge}
        </div>
        <div class="filter-layout">
          ${renderOptionGroup("价格", "", priceOptions, state.form.priceBand, "set-price")}
          ${renderOptionGroup("温度", "", temperatureOptions, state.form.temperaturePref, "set-temperature")}
          ${renderOptionGroup("咖啡因", "", caffeineOptions, state.form.caffeinePref, "set-caffeine", "filter-block--wide")}
          <div class="filter-block filter-block--taste">
            <div class="filter-meta">
              <span class="filter-title">口味</span>
              <span class="filter-tip">最多 3 个</span>
            </div>
            <div class="chip-row">
              ${tasteOptions.map(renderTasteChip).join("")}
            </div>
          </div>
        </div>
        <button class="primary-button step-submit-button" data-action="submit" type="button" ${state.submitting ? "disabled" : ""}>
          ${state.submitting ? "匹配中" : "看结果"}
        </button>
      </div>
    </section>
  `;
}

function renderResultView() {
  if (state.submitting || !state.result?.recommendation) {
    return `
      <section class="result-screen">
        <div class="panel result-panel loading-panel">
          <h2>匹配中</h2>
          <div class="loading-bar"></div>
        </div>
      </section>
    `;
  }

  const item = state.result.recommendation;
  const explanationSections = Array.isArray(item.explanation_sections) ? item.explanation_sections : [];
  const profileSummary = Array.isArray(state.result.meta?.profile_summary) ? state.result.meta.profile_summary : [];
  return `
    <section class="result-screen">
      <div class="panel result-panel">
        <div class="result-visual">
          <div class="result-image-frame">
            ${renderImage(item.image_url, item.item_name, item.image_badge_text || "", "contain")}
          </div>
          <div class="result-image-tools">
            <button class="secondary-button result-upload-button" data-action="open-upload" type="button" ${state.uploadingImage ? "disabled" : ""}>
              ${state.uploadingImage ? "提交中" : "提交图片"}
            </button>
            <input class="result-upload-input" data-upload-input type="file" accept="image/*" />
          </div>
        </div>
        <div class="result-copy">
          <h2>${escapeHtml(item.item_name)}</h2>
          <div class="result-meta-row">
            <span class="result-meta-item result-meta-item--brand">${escapeHtml(item.brand_name)}</span>
            <span class="result-meta-item result-meta-item--price">${escapeHtml(formatCurrency(item.base_price, item.currency_code || "CNY"))}</span>
            ${item.lifecycle_label ? `<span class="result-badge">${escapeHtml(item.lifecycle_label)}</span>` : ""}
            ${item.image_trust ? `<span class="result-badge result-badge--trust">${escapeHtml(item.image_trust)}</span>` : ""}
          </div>
          ${item.default_serving_note ? `<p class="result-note">${escapeHtml(item.default_serving_note)}</p>` : ""}
          ${profileSummary.length ? `
            <div class="result-memory">
              ${profileSummary.slice(0, 3).map((chip) => `<span class="result-memory-chip">${escapeHtml(chip)}</span>`).join("")}
            </div>
          ` : ""}
          <div class="result-explanations">
            ${explanationSections
              .map(
                (section) => `
                  <div class="result-explanation result-explanation--${escapeHtml(section.code || "note")}">
                    <span class="result-explanation-title">${escapeHtml(section.title || "")}</span>
                    <span class="result-explanation-text">${escapeHtml(section.text || "")}</span>
                  </div>
                `
              )
              .join("")}
          </div>
          <div class="result-tags">
            ${(item.tags || [])
              .slice(0, 3)
              .map((tag) => `<span class="result-tag">${escapeHtml(tag)}</span>`)
              .join("")}
          </div>
          <p class="result-reason">${escapeHtml(item.reason || "这一杯会比较适合现在的你。")}</p>
          <p class="result-encouragement">${escapeHtml(item.encouragement || "先喝一口。")}</p>
          <div class="result-actions">
            <button class="primary-button" data-action="accept" type="button" ${state.accepting ? "disabled" : ""}>
              ${state.accepting ? "记录中" : "就喝它"}
            </button>
            <button class="secondary-button" data-action="reroll" type="button" ${state.submitting ? "disabled" : ""}>
              换一个
            </button>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderMoodCard(mood) {
  const active = state.form.moodCode === mood.code;
  return `
    <button
      type="button"
      class="mood-card ${active ? "is-active" : ""}"
      data-mood-code="${escapeHtml(mood.code)}"
      style="--mood-color:${escapeHtml(getMoodColor(mood))}"
    >
      <span class="mood-sticker-wrap" aria-hidden="true" style="--mood-sticker:url('${escapeHtml(mood.sticker)}')"></span>
      <div class="mood-copy">
        <strong>${escapeHtml(mood.title)}</strong>
      </div>
    </button>
  `;
}

function getMoodQuadrant(mood) {
  return moodQuadrants?.[mood?.quadrant] || null;
}

function getMoodColor(mood) {
  return getMoodQuadrant(mood)?.color || "#7ea8b0";
}

function renderOptionGroup(title, tip, options, activeValue, action, extraClass = "") {
  return `
    <div class="filter-block ${escapeHtml(extraClass)}">
      <div class="filter-meta">
        <span class="filter-title">${escapeHtml(title)}</span>
        ${tip ? `<span class="filter-tip">${escapeHtml(tip)}</span>` : ""}
      </div>
      <div class="chip-row">
        ${options
          .map(
            (option) => `
              <button
                type="button"
                class="choice-chip ${activeValue === option.code ? "is-active" : ""}"
                data-action="${escapeHtml(action)}"
                data-value="${escapeHtml(option.code)}"
              >
                ${escapeHtml(option.label)}
              </button>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderTasteChip(option) {
  const active = state.form.tasteTags.includes(option.code);
  return `
    <button
      type="button"
      class="choice-chip ${active ? "is-active" : ""}"
      data-chip-group="taste"
      data-chip-value="${escapeHtml(option.code)}"
    >
      ${escapeHtml(option.label)}
    </button>
  `;
}

function renderCalendarCard() {
  const monthKey = state.currentMonth;
  const calendar = state.calendarByMonth[monthKey] || { items: [] };
  const moodByCode = Object.fromEntries(moods.map((item) => [item.code, item]));
  const itemsByDate = {};

  (calendar.items || []).forEach((item) => {
    const bucket = itemsByDate[item.accepted_date] || [];
    bucket.push(item);
    itemsByDate[item.accepted_date] = bucket;
  });

  return `
    <section class="panel calendar-panel">
      <div class="panel-head calendar-head">
        <h2>${escapeHtml(formatMonthKey(monthKey))}</h2>
        <div class="month-switcher">
          <button type="button" class="ghost-button" data-action="month-prev">上月</button>
          <button type="button" class="ghost-button" data-action="month-next">下月</button>
        </div>
      </div>
      <div class="calendar-week">
        ${weekLabels.map((label) => `<span>${escapeHtml(label)}</span>`).join("")}
      </div>
      <div class="calendar-grid">
        ${getCalendarDates(monthKey)
          .map((cell) => renderCalendarCell(cell, itemsByDate, moodByCode))
          .join("")}
      </div>
    </section>
  `;
}

function renderCalendarCell(cell, itemsByDate, moodByCode) {
  const dayKey = `${cell.date.getFullYear()}-${String(cell.date.getMonth() + 1).padStart(2, "0")}-${String(
    cell.date.getDate()
  ).padStart(2, "0")}`;
  const items = itemsByDate[dayKey] || [];

  return `
    <div class="calendar-cell ${cell.currentMonth ? "" : "is-muted"}">
      <span class="calendar-day">${cell.date.getDate()}</span>
      <div class="calendar-dots">
        ${items
          .slice(0, 3)
          .map((item) => {
            const mood = moodByCode[item.mood_code];
            const color = getMoodColor(mood) || moodQuadrants?.[item.mood_code]?.color || "#7ea8b0";
            return `<span class="calendar-dot" style="--dot-color:${escapeHtml(color)}"></span>`;
          })
          .join("")}
        ${items.length > 3 ? `<span class="calendar-more">+${items.length - 3}</span>` : ""}
      </div>
    </div>
  `;
}

function renderRecapCard() {
  const recap = state.recapByMonth[state.currentMonth] || buildEmptyRecap(state.currentMonth);
  const topMood = recap.mood_counts?.[0];
  const topPreferences = (recap.preference_counts || []).slice(0, 3);
  const favoriteBrand = recap.brand_counts?.[0];

  return `
    <section class="panel summary-panel">
      <div class="panel-head summary-head">
        <h2>${escapeHtml(recap.summary_title || `${formatMonthKey(state.currentMonth)}记录`)}</h2>
        <span class="summary-count">${escapeHtml(String(recap.record_count || 0))}</span>
      </div>
      <div class="summary-facts">
        <div class="fact-chip">
          <span>高频情绪</span>
          <strong>${escapeHtml(topMood?.mood_label || "暂无")}</strong>
        </div>
        <div class="fact-chip">
          <span>常选口味</span>
          <strong>${escapeHtml(topPreferences.map((item) => item.tag_label).join(" / ") || "暂无")}</strong>
        </div>
        <div class="fact-chip">
          <span>常选品牌</span>
          <strong>${escapeHtml(favoriteBrand?.brand_name || "暂无")}</strong>
        </div>
        <div class="fact-chip">
          <span>连续记录</span>
          <strong>${escapeHtml(String(recap.longest_streak_days || 0))} 天</strong>
        </div>
      </div>
    </section>
  `;
}

function buildEmptyRecap(monthKey) {
  return {
    month: monthKey,
    record_count: 0,
    summary_title: `${formatMonthKey(monthKey)}记录`,
    summary_text: "",
    gentle_tip: "",
    mood_counts: [],
    preference_counts: [],
    brand_counts: [],
    longest_streak_days: 0
  };
}

function setNotice(message, tone = "info", duration = 2800) {
  state.notice = { message, tone };
  renderApp();
  window.clearTimeout(noticeTimer);
  if (duration > 0) {
    noticeTimer = window.setTimeout(() => {
      state.notice = null;
      renderApp();
    }, duration);
  }
}

async function getJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}
