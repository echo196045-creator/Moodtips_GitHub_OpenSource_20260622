const API_BASE = "http://127.0.0.1:8000";

const categoryLabelMap = {
  tea: "茶",
  fruit_tea: "果茶",
  milk_tea: "奶茶",
  milk_drink: "奶饮",
  coffee: "咖啡",
  coffee_latte: "奶咖",
  coffee_sparkling: "气泡咖啡",
  latte: "茶拿铁",
  yogurt: "酸奶",
  smoothie: "冰沙 / 思慕雪",
  tea_sparkling: "气泡茶",
  tea_cheese: "奶盖茶",
  herbal_tea: "草本热饮",
  other: "其他"
};

const featureLabelMap = {
  energy_intensity: "提神",
  refresh_intensity: "清新",
  comfort_intensity: "安抚",
  indulgence_intensity: "奖励感",
  tea_intensity: "茶感",
  milk_intensity: "奶感",
  fruit_intensity: "果香",
  sweetness_intensity: "甜感",
  heaviness_intensity: "厚重度",
  caffeine_level: "咖啡因"
};

const profileTagLabelMap = {
  tea_forward: "茶感明显",
  milk_forward: "奶感明显",
  fruit_forward: "果香明显",
  low_caffeine: "低咖啡因",
  energy_boost: "提神向",
  refreshing: "清新向",
  comforting: "安抚向",
  indulgent: "满足向",
  heavy_body: "口感厚重",
  light_body: "轻盈口感",
  custom_sugar: "可调糖",
  custom_ice: "可调冰",
  toppings_available: "可加料",
  alt_milk_possible: "可换奶基",
  official_snapshot: "官方图文快照",
  official_display_price: "官方展示价格",
  reference_pricing: "深圳参考定价"
};

const moodTagLabelMap = {
  tired: "疲惫",
  stressed: "焦虑",
  empty: "空空的",
  need_care: "想被安抚",
  foggy: "脑子转不动",
  refresh: "想提提神",
  reward: "想奖励自己"
};

const sceneTagLabelMap = {
  study: "工作 / 学习",
  commute: "通勤路上",
  after_work: "下班之后",
  rainy_day: "雨天",
  hot_weather: "炎热天气",
  social: "社交时刻",
  alone: "一个人待着",
  after_meal: "饭后",
  late_night: "深夜",
  weekend: "周末放空",
  work_break: "工位间隙",
  overtime: "加班中",
  reward: "奖励时刻"
};

const optionGroupLabelMap = {
  size: "杯型 / 容量",
  sugar_level: "糖度",
  ice_level: "冰量",
  topping: "加料",
  milk: "奶底",
  milk_option: "奶基",
  tea_base: "茶底",
  temperature: "温度",
  customization: "其他客制",
  unknown: "未归类"
};

const sourceTypeLabelMap = {
  benchmark_seed: "基准样本",
  api: "真实来源",
  crawler: "抓取来源",
  manual: "人工录入"
};

const state = {
  brandFilter: "all",
  dashboard: null,
  selectedItemId: "",
  selectedItemDetail: null
};

const els = {};

document.addEventListener("DOMContentLoaded", async () => {
  cacheElements();
  bindEvents();
  renderAll();
  await bootstrap();
});

async function bootstrap() {
  await Promise.all([checkApiStatus(), loadDashboard()]);
}

function cacheElements() {
  els.opsApiStatus = document.getElementById("opsApiStatus");
  els.opsImportStatus = document.getElementById("opsImportStatus");
  els.opsMetricScope = document.getElementById("opsMetricScope");
  els.opsMetricItems = document.getElementById("opsMetricItems");
  els.opsMetricAvgPrice = document.getElementById("opsMetricAvgPrice");
  els.opsMetricReview = document.getElementById("opsMetricReview");
  els.opsBrandRail = document.getElementById("opsBrandRail");
  els.opsCoverageGrid = document.getElementById("opsCoverageGrid");
  els.opsBrandMatrix = document.getElementById("opsBrandMatrix");
  els.opsCategoryList = document.getElementById("opsCategoryList");
  els.opsPriceBandList = document.getElementById("opsPriceBandList");
  els.opsOptionGroupList = document.getElementById("opsOptionGroupList");
  els.opsProfileTags = document.getElementById("opsProfileTags");
  els.opsMoodTags = document.getElementById("opsMoodTags");
  els.opsSceneTags = document.getElementById("opsSceneTags");
  els.opsFeatureAverageList = document.getElementById("opsFeatureAverageList");
  els.opsReviewStatus = document.getElementById("opsReviewStatus");
  els.opsReviewQueue = document.getElementById("opsReviewQueue");
  els.opsDetailStatus = document.getElementById("opsDetailStatus");
  els.opsDetailCard = document.getElementById("opsDetailCard");
}

function bindEvents() {
  document.body.addEventListener("click", onBodyClick);
}

function onBodyClick(event) {
  const brandButton = event.target.closest("[data-ops-brand]");
  if (brandButton) {
    state.brandFilter = brandButton.dataset.opsBrand;
    state.selectedItemId = "";
    state.selectedItemDetail = null;
    loadDashboard();
    return;
  }

  const reviewButton = event.target.closest("[data-review-item-id]");
  if (reviewButton) {
    const itemId = reviewButton.dataset.reviewItemId;
    loadItemDetail(itemId);
  }
}

function currentBrandCodeOrNull() {
  return state.brandFilter === "all" ? null : state.brandFilter;
}

async function checkApiStatus() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const marketName = normalizeDisplayText(data.market_name || "China Mainland");
    setStatus(els.opsApiStatus, "ok", `API 在线 · ${marketName} · ${data.default_currency_code}`);
  } catch (error) {
    setStatus(els.opsApiStatus, "error", "API 暂不可用");
  }
}

async function loadDashboard() {
  setStatus(els.opsImportStatus, "pending", "正在读取治理摘要");
  els.opsReviewStatus.textContent = "正在生成待复核队列";

  const params = new URLSearchParams({
    review_limit: "14",
    tag_limit: "10"
  });
  const brandCode = currentBrandCodeOrNull();
  if (brandCode) {
    params.set("brand_code", brandCode);
  }

  try {
    const response = await fetch(`${API_BASE}/api/ops/menu-governance?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    state.dashboard = await response.json();
    const latestImportedAt = state.dashboard.latest_imported_at
      ? `最新导入：${formatDateTime(state.dashboard.latest_imported_at)}`
      : "未读取到导入时间";
    setStatus(els.opsImportStatus, "ok", latestImportedAt);

    const queue = state.dashboard.review_queue || [];
    els.opsReviewStatus.textContent = `当前展示 ${queue.length} 条优先复核样本`;

    const currentExists = queue.some((item) => item.item_id === state.selectedItemId);
    if (!currentExists) {
      state.selectedItemId = queue[0]?.item_id || "";
      state.selectedItemDetail = null;
      if (state.selectedItemId) {
        await loadItemDetail(state.selectedItemId, true);
      }
    }
  } catch (error) {
    state.dashboard = null;
    state.selectedItemId = "";
    state.selectedItemDetail = null;
    setStatus(els.opsImportStatus, "error", "治理摘要读取失败");
    els.opsReviewStatus.textContent = "暂时读取不到待复核样本";
  }

  renderAll();
}

async function loadItemDetail(itemId, silent = false) {
  state.selectedItemId = itemId;
  if (!silent) {
    setStatus(els.opsImportStatus, "ok", els.opsImportStatus.textContent);
  }
  els.opsDetailStatus.textContent = "正在读取商品详情";

  try {
    const response = await fetch(`${API_BASE}/api/ops/menu-items/${encodeURIComponent(itemId)}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    state.selectedItemDetail = await response.json();
    const brandName = displayText(state.selectedItemDetail.brand_name);
    const itemName = displayText(state.selectedItemDetail.item_name);
    els.opsDetailStatus.textContent = `${brandName} · ${itemName}`;
  } catch (error) {
    state.selectedItemDetail = null;
    els.opsDetailStatus.textContent = "详情读取失败";
  }

  renderReviewQueue();
  renderDetail();
}

function renderAll() {
  renderMetrics();
  renderBrandRail();
  renderCoverageGrid();
  renderBrandMatrix();
  renderDistributions();
  renderTagClusters();
  renderFeatureAverages();
  renderReviewQueue();
  renderDetail();
}

function renderMetrics() {
  const dashboard = state.dashboard;
  if (!dashboard) {
    els.opsMetricScope.textContent = "全部";
    els.opsMetricItems.textContent = "--";
    els.opsMetricAvgPrice.textContent = "--";
    els.opsMetricReview.textContent = "--";
    return;
  }

  els.opsMetricScope.textContent = dashboard.scope === "all" ? "全部" : brandNameForScope();
  els.opsMetricItems.textContent = String(dashboard.summary?.item_count || 0);
  els.opsMetricAvgPrice.textContent = formatCurrency(dashboard.summary?.avg_price || 0, "CNY");
  els.opsMetricReview.textContent = String(dashboard.summary?.review_queue_count || 0);
}

function renderBrandRail() {
  const brands = state.dashboard?.brands || [];
  const allCount = state.dashboard?.summary?.item_count || 0;
  const base = [
    {
      brand_code: "all",
      brand_name: "全部品牌",
      item_count: allCount
    },
    ...brands
  ];

  els.opsBrandRail.innerHTML = base
    .map((brand) => {
      const active = state.brandFilter === brand.brand_code;
      return `
        <button
          type="button"
          class="catalog-button ${active ? "active" : ""}"
          data-ops-brand="${escapeHtml(brand.brand_code)}"
        >
          ${escapeHtml(displayText(brand.brand_name))}
          <span class="ops-inline-count">${escapeHtml(String(brand.item_count || 0))}</span>
        </button>
      `;
    })
    .join("");
}

function renderCoverageGrid() {
  const summary = state.dashboard?.summary;
  if (!summary) {
    els.opsCoverageGrid.innerHTML = "";
    return;
  }

  const cards = [
    {
      label: "描述覆盖",
      value: formatPercent(summary.description_coverage_ratio),
      note: `${summary.described_count} / ${summary.item_count} 有描述`
    },
    {
      label: "客制覆盖",
      value: formatPercent(summary.customization_coverage_ratio),
      note: `${summary.customizable_count} / ${summary.item_count} 有客制组选项`
    },
    {
      label: "情绪标签覆盖",
      value: formatPercent(summary.mood_coverage_ratio),
      note: `${summary.mood_covered_count} / ${summary.item_count} 有情绪标签`
    },
    {
      label: "场景标签覆盖",
      value: formatPercent(summary.scene_coverage_ratio),
      note: `${summary.scene_covered_count} / ${summary.item_count} 有场景标签`
    },
    {
      label: "画像标签覆盖",
      value: formatPercent(summary.profile_coverage_ratio),
      note: `${summary.profile_covered_count} / ${summary.item_count} 有画像标签`
    },
    {
      label: "冷饮支持",
      value: formatPercent(summary.cold_support_ratio),
      note: `${summary.cold_supported_count} / ${summary.item_count} 支持冷饮`
    }
  ];

  els.opsCoverageGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="meta-box">
          <span>${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value)}</strong>
          <small class="small-copy">${escapeHtml(card.note)}</small>
        </article>
      `
    )
    .join("");
}

function renderBrandMatrix() {
  const brands = state.dashboard?.brands || [];
  if (!brands.length) {
    els.opsBrandMatrix.innerHTML = `<article class="detail-card empty-detail">暂无品牌治理摘要。</article>`;
    return;
  }

  els.opsBrandMatrix.innerHTML = brands
    .map((brand) => {
      const selected = state.brandFilter === brand.brand_code;
      const currencyCode = brand.default_currency_code || "CNY";
      const priceRange = `${formatCurrency(brand.min_price || 0, currencyCode)} - ${formatCurrency(
        brand.max_price || 0,
        currencyCode
      )}`;

      return `
        <article class="ops-brand-card ${selected ? "selected" : ""}">
          <div class="section-head">
            <div>
              <h3>${escapeHtml(displayText(brand.brand_name))}</h3>
              <span>${escapeHtml(displaySourceNote(brand))}</span>
            </div>
            <button type="button" class="tiny-button" data-ops-brand="${escapeHtml(brand.brand_code)}">切换视角</button>
          </div>
          <div class="catalog-meta">
            <span class="info-pill">${escapeHtml(String(brand.item_count || 0))} 个饮品</span>
            <span class="info-pill">${escapeHtml(String(brand.option_count || 0))} 个选项</span>
          </div>
          <p class="detail-copy">价格带：${escapeHtml(priceRange)}</p>
          <p class="detail-copy">最近导入：${escapeHtml(formatDateTime(brand.latest_imported_at))}</p>
        </article>
      `;
    })
    .join("");
}

function renderDistributions() {
  const dashboard = state.dashboard;
  renderBarList(els.opsCategoryList, dashboard?.category_distribution || [], (row) => displayCategory(row.code), (row) => row.count);
  renderBarList(
    els.opsPriceBandList,
    dashboard?.price_band_distribution || [],
    (row) => displayPriceBand(row.code),
    (row) => row.count
  );
  renderBarList(
    els.opsOptionGroupList,
    dashboard?.option_group_distribution || [],
    (row) => displayOptionGroup(row.group_type),
    (row) => row.item_count,
    (row) => `${row.item_count} 个饮品关联`
  );
}

function renderTagClusters() {
  const tags = state.dashboard?.tag_distributions || {};
  renderTagList(els.opsProfileTags, tags.profile || [], displayProfileTag);
  renderTagList(els.opsMoodTags, tags.mood || [], displayMoodTag);
  renderTagList(els.opsSceneTags, tags.scene || [], displaySceneTag);
}

function renderFeatureAverages() {
  const rows = state.dashboard?.feature_averages || [];
  if (!rows.length) {
    els.opsFeatureAverageList.innerHTML = `<article class="detail-card empty-detail">暂无特征均值数据。</article>`;
    return;
  }

  els.opsFeatureAverageList.innerHTML = rows
    .map(
      (row) => `
        <div class="feature-item">
          <div class="section-head">
            <h3>${escapeHtml(displayFeature(row.code))}</h3>
            <span>${escapeHtml(Number(row.avg_score || 0).toFixed(2))}</span>
          </div>
          <div class="feature-bar"><span style="width:${Math.max(8, Math.min(100, Number(row.avg_score || 0) * 20))}%"></span></div>
        </div>
      `
    )
    .join("");
}

function renderReviewQueue() {
  const queue = state.dashboard?.review_queue || [];
  if (!queue.length) {
    els.opsReviewQueue.innerHTML = `<article class="detail-card empty-detail">当前范围内没有高优先级待复核商品。</article>`;
    return;
  }

  els.opsReviewQueue.innerHTML = queue
    .map((item) => {
      const selected = state.selectedItemId === item.item_id;
      return `
        <article class="review-card ${selected ? "selected" : ""}">
          <div class="section-head">
            <div>
              <h3>${escapeHtml(displayText(item.item_name))}</h3>
              <span>${escapeHtml(displayText(item.brand_name))} · ${escapeHtml(displayCategory(item.normalized_category))}</span>
            </div>
            <span class="rank-badge">P${escapeHtml(String(item.priority_score || 0))}</span>
          </div>
          <div class="catalog-meta">
            <span class="price-badge">${escapeHtml(formatCurrency(item.base_price, item.currency_code))}</span>
            <span class="info-pill">${escapeHtml(String(item.option_group_count || 0))} 组客制</span>
            <span class="info-pill">${escapeHtml(String(item.profile_tag_count || 0))} 个画像标签</span>
            <span class="info-pill">${escapeHtml(displaySourceLabel(item))}</span>
          </div>
          <div class="chip-row">
            ${(item.review_reasons || [])
              .map((reason) => `<span class="summary-chip">${escapeHtml(displayText(reason))}</span>`)
              .join("")}
          </div>
          <div class="card-actions">
            <button type="button" class="card-button ${selected ? "primary" : ""}" data-review-item-id="${escapeHtml(item.item_id)}">
              ${selected ? "正在查看" : "查看详情"}
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderDetail() {
  const detail = state.selectedItemDetail;
  if (!detail) {
    els.opsDetailCard.className = "detail-card empty-detail";
    els.opsDetailCard.innerHTML = "选择一条待复核样本后，这里会显示商品画像、标签、价格和客制化结构，方便继续人工校对。";
    if (!state.selectedItemId) {
      els.opsDetailStatus.textContent = "等待选中样本";
    }
    return;
  }

  els.opsDetailCard.className = "detail-card";

  const featureBars = Object.entries(detail.feature_profile || {})
    .map(
      ([key, value]) => `
        <div class="feature-item">
          <div class="section-head">
            <h3>${escapeHtml(displayFeature(key))}</h3>
            <span>${escapeHtml(Number(value || 0).toFixed(1))}</span>
          </div>
          <div class="feature-bar"><span style="width:${Math.max(8, Math.min(100, Number(value || 0) * 20))}%"></span></div>
        </div>
      `
    )
    .join("");

  const groups = (detail.customization_groups || [])
    .map(
      (group) => `
        <div class="customization-group">
          <div class="section-head">
            <h3>${escapeHtml(displayText(group.group_name))}</h3>
            <span>${group.required ? "必选" : "可选"} · ${(group.options || []).length} 个选项</span>
          </div>
          <div class="option-list">
            ${(group.options || [])
              .slice(0, 10)
              .map(
                (option) => `
                  <span class="option-chip">
                    ${escapeHtml(displayText(option.option_name))}
                    ${Number(option.price_delta || 0) > 0 ? ` · +${escapeHtml(formatCurrency(option.price_delta, detail.currency_code))}` : ""}
                  </span>
                `
              )
              .join("")}
          </div>
        </div>
      `
    )
    .join("");

  const tagChips = [
    ...(detail.profile_tags || []).map((tag) => displayProfileTag(tag)),
    ...(detail.mood_tags || []).map((tag) => `情绪 · ${displayMoodTag(tag)}`),
    ...(detail.scene_tags || []).map((tag) => `场景 · ${displaySceneTag(tag)}`)
  ];

  els.opsDetailCard.innerHTML = `
    <div class="card-topline">
      <span class="brand-badge">${escapeHtml(displayText(detail.brand_name))}</span>
      <span class="price-badge">${escapeHtml(formatCurrency(detail.base_price, detail.currency_code))}</span>
    </div>
    <div class="card-title">
      <h2>${escapeHtml(displayText(detail.item_name))}</h2>
      <span class="category-badge">${escapeHtml(displayCategory(detail.normalized_category))}</span>
    </div>
    <p class="detail-copy">${escapeHtml(displayText(detail.description || "当前没有商品描述，建议人工补充一句对口味或场景有帮助的说明。"))}</p>
    <div class="chip-row">
      <span class="info-pill">${escapeHtml(displaySourceLabel(detail))}</span>
      ${tagChips.map((chip) => `<span class="summary-chip">${escapeHtml(chip)}</span>`).join("")}
    </div>
    <p class="detail-copy">${escapeHtml(displaySourceNote(detail))}</p>
    ${formatPriceContextNote(detail) ? `<p class="detail-copy">${escapeHtml(formatPriceContextNote(detail))}</p>` : ""}
    <div class="detail-grid">
      <div class="feature-list">${featureBars}</div>
      <div class="customization-list">
        ${groups || '<article class="feature-item">当前没有客制化结构，适合排查是否导入缺失。</article>'}
      </div>
    </div>
  `;
}

function renderBarList(target, rows, labelFn, countFn, noteFn) {
  if (!rows.length) {
    target.innerHTML = `<article class="detail-card empty-detail">暂无分布数据。</article>`;
    return;
  }

  const maxValue = Math.max(...rows.map((row) => Number(countFn(row) || 0)), 1);
  target.innerHTML = rows
    .slice(0, 8)
    .map((row) => {
      const value = Number(countFn(row) || 0);
      const width = Math.max(8, Math.round((value / maxValue) * 100));
      const note = noteFn ? noteFn(row) : `${value} 个饮品`;
      return `
        <div class="ops-bar-row">
          <div class="section-head">
            <h3>${escapeHtml(labelFn(row))}</h3>
            <span>${escapeHtml(note)}</span>
          </div>
          <div class="feature-bar"><span style="width:${width}%"></span></div>
        </div>
      `;
    })
    .join("");
}

function renderTagList(target, rows, labelFn) {
  if (!rows.length) {
    target.innerHTML = `<span class="info-pill">暂无标签</span>`;
    return;
  }

  target.innerHTML = rows
    .map(
      (row) => `
        <span class="summary-chip">
          ${escapeHtml(labelFn(row.code))}
          <span class="ops-inline-count">${escapeHtml(String(row.count || 0))}</span>
        </span>
      `
    )
    .join("");
}

function setStatus(element, status, text) {
  element.className = `status-pill status-${status}`;
  element.textContent = text;
}

function brandNameForScope() {
  const brands = state.dashboard?.brands || [];
  const matched = brands.find((brand) => brand.brand_code === state.brandFilter);
  return displayText(matched?.brand_name || brands[0]?.brand_name || "单品牌");
}

function displayCategory(code) {
  return categoryLabelMap[code] || displayText(code || "未分类");
}

function displayFeature(code) {
  return featureLabelMap[code] || displayText(code);
}

function displayProfileTag(code) {
  return profileTagLabelMap[code] || displayText(code);
}

function displayMoodTag(code) {
  return moodTagLabelMap[code] || displayText(code);
}

function displaySceneTag(code) {
  return sceneTagLabelMap[code] || displayText(code);
}

function displayOptionGroup(code) {
  return optionGroupLabelMap[code] || displayText(code || "未归类");
}

function displaySourceLabel(payload = {}) {
  const captureStatus = String(payload.capture_status || "");
  if (captureStatus === "verified_official_cn") {
    return "大陆官方已核验";
  }
  if (captureStatus === "official_cn_snapshot") {
    return "大陆官方快照";
  }

  const sourceType = String(payload.source_type || "");
  const channelName = displayText(payload.channel_name || "");
  const sourceName = displayText(payload.source_name || "");
  if (sourceTypeLabelMap[sourceType]) {
    return sourceTypeLabelMap[sourceType];
  }
  if (channelName.includes("Benchmark") || sourceName.includes("Benchmark")) {
    return "基准样本";
  }
  if (channelName || sourceName) {
    return "真实来源";
  }
  return "未标注来源";
}

function displaySourceNote(payload = {}) {
  const label = displaySourceLabel(payload);
  const channelName = displayText(payload.channel_name || payload.source_name || payload.store_name || "");
  return channelName ? `${label} · ${channelName}` : label;
}

function formatPriceContextNote(payload = {}) {
  const ctx = payload.price_context || null;
  if (!ctx || ctx.price_mode !== "cny_demo") {
    return "";
  }

  const sourceSalePrice = Number(ctx.source_sale_price || 0);
  const fxRate = Number(ctx.fx_rate_to_cny || 0);
  if (!sourceSalePrice || !fxRate) {
    return "";
  }

  const sourceCurrency = ctx.source_currency_code || "SGD";
  const normalizedCurrency = ctx.normalized_currency_code || "CNY";
  const fxDate = ctx.fx_updated_at ? String(ctx.fx_updated_at).slice(5, 16) : "";
  const dateLabel = fxDate ? `（汇率快照 ${fxDate}）` : "";
  return `源站活动价 ${formatCurrency(sourceSalePrice, sourceCurrency)}，当前以 ${normalizedCurrency} 折算展示${dateLabel}`;
}

function displayPriceBand(code) {
  if (code === "low") return "价格友好";
  if (code === "mid") return "主流价格";
  if (code === "high") return "高价带";
  return displayText(code || "未知");
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function formatCurrency(value, currencyCode = "CNY") {
  if (value == null || Number.isNaN(Number(value))) {
    return "--";
  }

  try {
    return new Intl.NumberFormat("zh-CN", {
      style: "currency",
      currency: currencyCode,
      minimumFractionDigits: Number(value) % 1 === 0 ? 0 : 2,
      maximumFractionDigits: 2
    }).format(Number(value));
  } catch (error) {
    return `${currencyCode} ${Number(value).toFixed(2)}`;
  }
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return displayText(value);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function displayText(value) {
  return normalizeDisplayText(value == null ? "" : String(value));
}

function normalizeDisplayText(value) {
  if (!value) {
    return "";
  }

  const trimmed = String(value).trim();
  if (!looksLikeMojibake(trimmed)) {
    return trimmed;
  }

  try {
    const bytes = Uint8Array.from(Array.from(trimmed).map((char) => char.charCodeAt(0)));
    const decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes).trim();
    return decoded || trimmed;
  } catch (error) {
    return trimmed;
  }
}

function looksLikeMojibake(value) {
  if (!value) {
    return false;
  }

  if (/[\u4e00-\u9fff]/.test(value)) {
    return false;
  }

  return /[ÃÂÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ\u0080-\u00bf]/.test(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
