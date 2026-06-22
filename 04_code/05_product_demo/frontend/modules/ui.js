(() => {
  const root = (window.HeKouModules = window.HeKouModules || {});
  const { constants, recommendation, utils } = root;

  const { budgetOptions, caffeineOptions, moodCatalog, preferenceCatalog, temperatureOptions } = constants;
  const {
    buildEncouragement,
    buildPriceBadgeLabel,
    buildPriceInsights,
    buildPriceNote,
    buildRecommendationReasons,
    buildServingNote,
    getMood
  } = recommendation;
  const {
    capitalize,
    escapeHtml,
    formatCurrency,
    formatDateTime,
    getCalendarDates,
    getMonthKey,
    renderImage
  } = utils;

  function renderNotice({ state, els }) {
    if (!els.noticeBanner) {
      return;
    }

    if (!state.notice?.message) {
      els.noticeBanner.textContent = "";
      els.noticeBanner.className = "notice-banner notice-info hidden";
      return;
    }

    els.noticeBanner.textContent = state.notice.message;
    els.noticeBanner.className = `notice-banner notice-${escapeHtml(state.notice.tone || "info")}`;
  }

  function renderPageVisibility({ state }) {
    document.querySelectorAll(".page").forEach((pageEl) => {
      pageEl.classList.toggle("active", pageEl.id === `page${capitalize(state.page)}`);
    });
  }

  function renderChoosePage({ state, els }) {
    els.moodGrid.innerHTML = moodCatalog
      .map(
        (mood) => `
          <button
            type="button"
            class="mood-card ${state.form.mood === mood.code ? "active" : ""}"
            style="--mood-color:${mood.color}"
            data-mood-code="${escapeHtml(mood.code)}"
            aria-pressed="${state.form.mood === mood.code ? "true" : "false"}"
          >
            <span class="mood-title">${escapeHtml(mood.title)}</span>
            <span class="mood-subtitle">${escapeHtml(mood.subtitle)}</span>
          </button>
        `
      )
      .join("");

    els.budgetOptions.innerHTML = renderChoiceOptions(budgetOptions, "budget", state.form.budget);
    els.temperatureOptions.innerHTML = renderChoiceOptions(temperatureOptions, "temperature", state.form.temperature);
    els.caffeineOptions.innerHTML = renderChoiceOptions(caffeineOptions, "caffeine", state.form.caffeine);

    els.preferenceOptions.innerHTML = preferenceCatalog
      .map((preference) => {
        const active = state.form.preferences.includes(preference.code);
        return `
          <button
            type="button"
            class="choice-pill ${active ? "active" : ""}"
            data-preference-code="${escapeHtml(preference.code)}"
            aria-pressed="${active ? "true" : "false"}"
          >
            ${escapeHtml(preference.label)}
          </button>
        `;
      })
      .join("");

    if (els.submitRecommendationButton) {
      els.submitRecommendationButton.disabled = state.isSubmittingRecommendation;
      els.submitRecommendationButton.textContent = state.isSubmittingRecommendation ? "正在替我选一杯..." : "替我选一杯";
      els.submitRecommendationButton.setAttribute("aria-busy", state.isSubmittingRecommendation ? "true" : "false");
    }
  }

  function renderResultPage({ state, els, getCurrentCandidate }) {
    if (state.loading) {
      els.resultState.innerHTML = `
        <article class="empty-card">
          <p class="loading-line"></p>
          <p class="loading-line short"></p>
          <p class="small-copy">正在替你从当前饮品目录里挑一杯更合适的。</p>
        </article>
      `;
      return;
    }

    if (state.error) {
      els.resultState.innerHTML = `<article class="empty-card">${escapeHtml(state.error)}</article>`;
      return;
    }

    if (!state.result || !state.result.candidates.length) {
      els.resultState.innerHTML = `<article class="empty-card">先选一个状态，我再替你定这一杯。</article>`;
      return;
    }

    const candidate = getCurrentCandidate();
    const servingNote = buildServingNote(candidate, state.form);
    const encouragement = buildEncouragement({ moodCode: state.form.mood, resultIndex: state.result.index });
    const priceBadgeLabel = buildPriceBadgeLabel(candidate);
    const priceNote = buildPriceNote(candidate);
    const reasonChips = buildRecommendationReasons(candidate, state.form);
    const priceChips = buildPriceInsights(candidate);
    const flavorChips = (candidate.option_summary || [])
      .slice(0, 3)
      .map((item) => `<span class="info-pill">${escapeHtml(item.group_name)}</span>`)
      .join("");
    const disabledAttr = state.isAcceptingResult ? "disabled" : "";
    const acceptLabel = state.isAcceptingResult ? "正在记录..." : "就喝它了";
    const rerollLabel = state.isAcceptingResult ? "稍等一下" : "刷新提示";

    els.resultIntro.textContent = `我按你刚才的状态和偏好，替你选了第 ${state.result.index + 1} 杯。`;
    els.resultState.innerHTML = `
      <article class="result-card">
        <div class="result-visual">
          ${renderImage(candidate.image_url, candidate.sku_name)}
        </div>
        <div class="result-copy">
          <div class="result-topline">
            <span class="brand-badge">${escapeHtml(candidate.brand_name || "今日推荐")}</span>
            <span class="price-badge">${escapeHtml(priceBadgeLabel)}</span>
          </div>
          <h3>${escapeHtml(candidate.display_name || candidate.sku_name)}</h3>
          <p class="small-copy">${escapeHtml(candidate.original_category || candidate.category || "饮品推荐")}</p>
          <div class="chip-row">${flavorChips || '<span class="info-pill">支持客制化</span>'}</div>

          <div class="result-meta-stack">
            <div class="result-group">
              <span class="detail-label">为什么是它</span>
              <div class="chip-row">
                ${(reasonChips.length ? reasonChips : ["符合你刚才的限制与偏好"])
                  .map((item) => `<span class="info-pill reason-pill">${escapeHtml(item)}</span>`)
                  .join("")}
              </div>
            </div>

            <div class="result-group">
              <span class="detail-label">价格说明</span>
              <div class="chip-row">
                ${(priceChips.length ? priceChips : ["人民币价格"])
                  .map((item) => `<span class="info-pill source-pill">${escapeHtml(item)}</span>`)
                  .join("")}
              </div>
              ${priceNote ? `<p class="small-copy">${escapeHtml(priceNote)}</p>` : ""}
            </div>
          </div>

          <div class="detail-block">
            <span class="detail-label">推荐喝法</span>
            <p>${escapeHtml(servingNote)}</p>
          </div>
          <div class="detail-block">
            <span class="detail-label">给现在的你</span>
            <p>${escapeHtml(encouragement)}</p>
          </div>
          <div class="result-actions">
            <button type="button" class="primary-button" data-action="accept-result" ${disabledAttr}>${escapeHtml(acceptLabel)}</button>
            <button type="button" class="secondary-button" data-action="reroll-result" ${disabledAttr}>${escapeHtml(rerollLabel)}</button>
          </div>
        </div>
      </article>
    `;
  }

  function renderHomePage({
    state,
    els,
    buildRecapView,
    getCalendarRecordsForMonth,
    getLatestUsefulMonthKey,
    scheduleMonthlyDataLoad
  }) {
    if (state.health) {
      els.brandCount.textContent = String(state.health.menu_brand_count || "--");
      els.itemCount.textContent = String(state.health.menu_item_count || "--");
    }

    if (state.flashMessage) {
      els.flashMessage.textContent = state.flashMessage;
      els.flashMessage.classList.remove("hidden");
    } else {
      els.flashMessage.classList.add("hidden");
    }

    const currentMonthKey = getMonthKey(new Date());
    const currentMonthRecords = getCalendarRecordsForMonth(currentMonthKey);
    const latestRecapMonthKey = getLatestUsefulMonthKey();
    const recapView = buildRecapView(latestRecapMonthKey);

    els.recordCount.textContent = String(currentMonthRecords.length);
    els.calendarMonthLabel.textContent = utils.formatMonthKey(currentMonthKey);
    els.homeCalendar.innerHTML = renderCalendar(currentMonthKey, true, currentMonthRecords);
    els.recapTitle.textContent = recapView.title;
    els.homeRecapCard.innerHTML = recapView.cardHtml;
    els.sourceStandardBlurb.textContent = buildSourceStandardBlurb(state.sourceStandard);
    els.brandPreviewGrid.innerHTML = state.menuBrands.length
      ? state.menuBrands.slice(0, 6).map((brand) => renderBrandCard(brand, { compact: true, selectedBrandCode: state.selectedCatalogBrandCode })).join("")
      : `<article class="empty-card">品牌目录正在加载中，稍后会显示当前可推荐的品牌范围。</article>`;

    scheduleMonthlyDataLoad(currentMonthKey, { calendar: true, recap: currentMonthKey === latestRecapMonthKey });
    if (latestRecapMonthKey !== currentMonthKey) {
      scheduleMonthlyDataLoad(latestRecapMonthKey, { calendar: false, recap: true });
    }
  }

  function renderCatalogPage({ state, els, getCatalogSelectedBrand }) {
    const selectedBrand = getCatalogSelectedBrand();
    const detail = selectedBrand ? state.catalogDetailsByCode[selectedBrand.brand_code] : null;
    const itemResponse = selectedBrand ? state.catalogItemsByCode[selectedBrand.brand_code] : null;
    const ruleItems = buildSourceRuleItems(state.sourceStandard);

    const counts = state.menuBrands.reduce(
      (accumulator, brand) => {
        const maturity = classifyBrandMaturity(brand);
        accumulator[maturity.key] = (accumulator[maturity.key] || 0) + 1;
        return accumulator;
      },
      { official: 0, reference: 0, estimate: 0, catalog: 0 }
    );

    els.catalogOfficialCount.textContent = String(counts.official || 0);
    els.catalogReferenceCount.textContent = String(counts.reference || 0);
    els.catalogEstimateCount.textContent = String(counts.estimate || 0);
    els.catalogVisibleCount.textContent = String(state.menuBrands.length || 0);
    els.catalogRuleList.innerHTML = ruleItems.map((item) => `<article class="rule-item"><p>${escapeHtml(item)}</p></article>`).join("");
    els.catalogBrandGrid.innerHTML = state.menuBrands.length
      ? state.menuBrands.map((brand) => renderBrandCard(brand, { selectedBrandCode: state.selectedCatalogBrandCode })).join("")
      : `<article class="empty-card">还没有读到品牌目录，请确认本地 API 是否已连接。</article>`;

    if (!selectedBrand) {
      els.catalogDetailStatus.textContent = "等待载入品牌详情";
      els.catalogDetailCard.innerHTML = `<article class="empty-card">选中一个品牌后，这里会展示它的数据说明和示例饮品。</article>`;
      return;
    }

    els.catalogDetailStatus.textContent = selectedBrand.brand_name_local || selectedBrand.brand_name || selectedBrand.brand_code;

    if (!detail || !itemResponse) {
      els.catalogDetailCard.innerHTML = `<article class="empty-card">正在读取 ${escapeHtml(
        selectedBrand.brand_name_local || selectedBrand.brand_name || selectedBrand.brand_code
      )} 的详情与示例饮品。</article>`;
      return;
    }

    const maturity = classifyBrandMaturity(selectedBrand);
    const source = (detail.sources || [])[0] || {};
    const categoryPills = (detail.category_breakdown || [])
      .slice(0, 6)
      .map((item) => `<span class="info-pill">${escapeHtml(`${item.category_name} ${item.item_count}`)}</span>`)
      .join("");
    const sampleCards = (itemResponse.items || [])
      .slice(0, 6)
      .map(
        (item) => `
          <article class="catalog-sample-card">
            <div class="catalog-sample-visual">${renderImage(item.image_url, item.display_name || item.item_name)}</div>
            <div class="catalog-sample-copy">
              <div class="brand-card-top">
                <h4>${escapeHtml(item.display_name || item.item_name)}</h4>
                <span class="meta-chip">${escapeHtml(formatCurrency(item.base_price, item.currency_code || "CNY"))}</span>
              </div>
              <p>${escapeHtml(item.category_name || item.normalized_category || "饮品")}</p>
              <div class="chip-row">
                ${(item.option_summary || [])
                  .slice(0, 3)
                  .map((option) => `<span class="info-pill">${escapeHtml(option.group_name)}</span>`)
                  .join("")}
              </div>
            </div>
          </article>
        `
      )
      .join("");

    els.catalogDetailCard.innerHTML = `
      <div class="catalog-detail-layout">
        <div class="brand-card-top">
          <div class="brand-card-copy">
            <h3>${escapeHtml(selectedBrand.brand_name_local || selectedBrand.brand_name || selectedBrand.brand_code)}</h3>
            <p>${escapeHtml(summarizeBrandNote(selectedBrand.brand_notes || ""))}</p>
          </div>
          <span class="tone-chip ${escapeHtml(maturity.toneClass)}">${escapeHtml(maturity.label)}</span>
        </div>

        <div class="catalog-source-block">
          <h4>当前前台来源</h4>
          <p>${escapeHtml(source.source_name || "当前品牌详情已接入目录。")}</p>
          <div class="catalog-note-list">
            <span class="meta-chip">${escapeHtml(`${detail.item_count || 0} 款饮品`)}</span>
            <span class="meta-chip">${escapeHtml(
              `${formatCurrency(detail.min_price, detail.default_currency_code || "CNY")} - ${formatCurrency(
                detail.max_price,
                detail.default_currency_code || "CNY"
              )}`
            )}</span>
            <span class="meta-chip">${escapeHtml(`${source.city || "Shenzhen"} 基线`)}</span>
            <span class="meta-chip">${escapeHtml(source.imported_at ? formatDateTime(source.imported_at) : "已接入目录")}</span>
          </div>
        </div>

        <div class="catalog-source-block">
          <h4>品类覆盖</h4>
          <div class="catalog-category-list">${categoryPills || '<span class="info-pill">等待更多品类数据</span>'}</div>
        </div>

        <div class="catalog-source-block">
          <h4>示例饮品</h4>
          <div class="catalog-sample-grid">
            ${sampleCards || '<article class="empty-card">这个品牌的示例饮品还在加载中。</article>'}
          </div>
        </div>
      </div>
    `;
  }

  function renderRecapPage({
    state,
    els,
    buildRecapView,
    getCalendarRecordsForMonth,
    getRecentAcceptedRecordsForMonth,
    scheduleMonthlyDataLoad
  }) {
    const monthKey = state.recapMonthKey;
    const recapView = buildRecapView(monthKey);
    const records = getCalendarRecordsForMonth(monthKey);

    els.recapPageTitle.textContent = recapView.title;
    els.recapMonthMeta.textContent = recapView.meta;
    els.recapCalendar.innerHTML = renderCalendar(monthKey, false, records);
    els.recapSummary.innerHTML = recapView.html;
    els.recentAcceptedList.innerHTML = renderRecentAcceptedList(getRecentAcceptedRecordsForMonth(monthKey));

    scheduleMonthlyDataLoad(monthKey);
  }

  function renderChoiceOptions(options, type, activeCode) {
    return options
      .map(
        (option) => `
          <button
            type="button"
            class="choice-pill ${activeCode === option.code ? "active" : ""}"
            data-${type}-code="${escapeHtml(option.code)}"
            aria-pressed="${activeCode === option.code ? "true" : "false"}"
          >
            ${escapeHtml(option.label)}
          </button>
        `
      )
      .join("");
  }

  function renderCalendar(monthKey, compact, records) {
    const recordsByDate = {};
    records.forEach((record) => {
      const dateKey = record.created_at.slice(0, 10);
      if (!recordsByDate[dateKey]) {
        recordsByDate[dateKey] = [];
      }
      recordsByDate[dateKey].push(record);
    });

    const dates = getCalendarDates(monthKey);
    const weekHeader = ["一", "二", "三", "四", "五", "六", "日"]
      .map((weekday) => `<span class="calendar-weekday">${weekday}</span>`)
      .join("");

    const dayCells = dates
      .map((item) => {
        const dateKey = item.date.toISOString().slice(0, 10);
        const dots = (recordsByDate[dateKey] || [])
          .slice(0, compact ? 2 : 4)
          .map((record) => {
            const mood = getMood(record.mood_code);
            return `<span class="calendar-dot" style="--dot-color:${escapeHtml(mood?.color || "#c5c5c5")}"></span>`;
          })
          .join("");

        return `
          <div class="calendar-day ${item.currentMonth ? "" : "muted"}">
            <span class="calendar-date">${item.date.getDate()}</span>
            <div class="calendar-dots">${dots}</div>
          </div>
        `;
      })
      .join("");

    return `
      <div class="calendar-week">${weekHeader}</div>
      <div class="calendar-grid ${compact ? "compact" : ""}">${dayCells}</div>
    `;
  }

  function renderRecentAcceptedList(records) {
    if (!records.length) {
      return `<article class="accepted-card empty-card">这个月还没有被确认的那一杯。</article>`;
    }

    return records
      .map((record) => {
        const mood = getMood(record.mood_code);
        return `
          <article class="accepted-card">
            <div class="accepted-topline">
              <span class="mini-pill" style="--pill-color:${escapeHtml(mood?.color || "#dedede")}">${escapeHtml(mood?.title || "状态")}</span>
              <span class="small-meta">${escapeHtml(formatDateTime(record.created_at))}</span>
            </div>
            <h4>${escapeHtml(record.sku_name)}</h4>
            <p>${escapeHtml(record.brand_name)} · ${escapeHtml(formatCurrency(record.price, record.currency_code || "CNY"))}</p>
          </article>
        `;
      })
      .join("");
  }

  function classifyBrandMaturity(brand) {
    const note = String(brand?.brand_notes || "").toLowerCase();
    if (note.includes("official site display prices")) {
      return { key: "official", label: "官网展示价", toneClass: "tone-official" };
    }
    if (note.includes("unverified mainland reference pricing")) {
      return { key: "estimate", label: "官网图 + 参考估价", toneClass: "tone-estimate" };
    }
    if (note.includes("shenzhen reference pricing")) {
      return { key: "reference", label: "官网图 + 深圳参考价", toneClass: "tone-reference" };
    }
    return { key: "catalog", label: "已接入目录", toneClass: "" };
  }

  function buildSourceStandardBlurb(sourceStandard) {
    const standard = sourceStandard || {};
    const city = standard.official_pricing_city || "深圳";
    return `当前目录默认以 ${city} 作为统一价格基线，只展示中国大陆人民币饮品数据；未核验来源不会进入前台推荐。`;
  }

  function buildSourceRuleItems(sourceStandard) {
    const standard = sourceStandard || {};
    const city = standard.official_pricing_city || "深圳";
    return [
      `只展示中国大陆官方内容支撑的饮品目录，默认币种为 ${standard.required_currency_code || "CNY"}。`,
      `不做定位，不做下单，统一以 ${city} 作为价格基线。`,
      "若门店级价格未单独核验，前台必须明确标注为参考价或参考估价。"
    ];
  }

  function renderBrandCard(brand, options = {}) {
    const maturity = classifyBrandMaturity(brand);
    const isActive = !options.compact && options.selectedBrandCode === brand.brand_code;
    const priceRange = `${formatCurrency(brand.min_price, brand.default_currency_code || "CNY")} - ${formatCurrency(
      brand.max_price,
      brand.default_currency_code || "CNY"
    )}`;

    return `
      <button
        type="button"
        class="brand-card ${isActive ? "active" : ""}"
        data-catalog-brand="${escapeHtml(brand.brand_code)}"
      >
        <div class="brand-card-top">
          <div class="brand-card-copy">
            <h4>${escapeHtml(brand.brand_name_local || brand.brand_name || brand.brand_code)}</h4>
            <p>${escapeHtml(priceRange)}</p>
          </div>
          <span class="tone-chip ${escapeHtml(maturity.toneClass)}">${escapeHtml(maturity.label)}</span>
        </div>
        <div class="brand-card-meta">
          <span class="meta-chip">${escapeHtml(`${brand.item_count || 0} 款饮品`)}</span>
          <span class="meta-chip">${escapeHtml(`${brand.option_group_count || 0} 组客制化`)}</span>
        </div>
        ${
          options.compact
            ? ""
            : `<p>${escapeHtml(summarizeBrandNote(brand.brand_notes || ""))}</p>`
        }
      </button>
    `;
  }

  function summarizeBrandNote(note) {
    if (!note) {
      return "已接入当前目录，可用于情绪推荐。";
    }
    return String(note)
      .replace("Consumer-visible mainland snapshot backed by official product content and official site display prices.", "产品图与价格来自大陆官网展示。")
      .replace("Consumer-visible mainland snapshot backed by official product content and unverified mainland reference pricing.", "产品图来自大陆官网，价格为参考估算并已标注。")
      .replace("Consumer-visible mainland reference snapshot backed by official product content and Shenzhen reference pricing.", "产品图来自大陆官方内容，价格采用深圳统一参考基线。");
  }

  root.ui = {
    renderCatalogPage,
    renderChoosePage,
    renderHomePage,
    renderNotice,
    renderPageVisibility,
    renderRecapPage,
    renderResultPage
  };
})();
