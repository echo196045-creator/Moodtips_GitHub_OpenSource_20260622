(() => {
  const root = (window.HeKouModules = window.HeKouModules || {});

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatCurrency(value, currencyCode = "CNY") {
    const amount = Number(value || 0);
    try {
      return new Intl.NumberFormat("zh-CN", {
        style: "currency",
        currency: currencyCode,
        maximumFractionDigits: 2
      }).format(amount);
    } catch (error) {
      return `${currencyCode} ${amount.toFixed(2)}`;
    }
  }

  function getMonthKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    return `${year}-${month}`;
  }

  function shiftMonthKey(monthKey, delta) {
    const [year, month] = String(monthKey).split("-").map(Number);
    const next = new Date(year, month - 1 + delta, 1);
    return getMonthKey(next);
  }

  function formatMonthKey(monthKey) {
    const [year, month] = String(monthKey).split("-").map(Number);
    if (!year || !month) {
      return monthKey;
    }
    return `${year}\u5e74${month}\u6708`;
  }

  function formatDateShort(isoString) {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return isoString;
    }
    return `${date.getMonth() + 1}.${date.getDate()}`;
  }

  function getCalendarDates(monthKey) {
    const [year, month] = String(monthKey).split("-").map(Number);
    const firstDay = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const dates = [];

    for (let index = 0; index < startOffset; index += 1) {
      dates.push({
        date: new Date(year, month - 1, 1 - (startOffset - index)),
        currentMonth: false
      });
    }

    for (let day = 1; day <= lastDay.getDate(); day += 1) {
      dates.push({ date: new Date(year, month - 1, day), currentMonth: true });
    }

    while (dates.length % 7 !== 0) {
      const lastDate = dates[dates.length - 1].date;
      dates.push({
        date: new Date(lastDate.getFullYear(), lastDate.getMonth(), lastDate.getDate() + 1),
        currentMonth: false
      });
    }

    return dates;
  }

  function resolveAssetUrl(imageUrl) {
    const url = String(imageUrl || "").trim();
    if (!url) {
      return "";
    }
    if (url.startsWith("data:") || url.startsWith("blob:")) {
      return url;
    }
    if (/^(https?:)?\/\//.test(url)) {
      return url;
    }
    if (url.startsWith("/")) {
      const base = String(window.HeKouApiBase || "").replace(/\/$/, "");
      return base ? `${base}${url}` : url;
    }
    return url;
  }

  function renderImage(imageUrl, altText, badgeText = "", fit = "cover") {
    const resolvedUrl = resolveAssetUrl(imageUrl);
    const badge = String(badgeText || "").trim();
    const objectFit = fit === "contain" ? "contain" : "cover";
    if (!resolvedUrl) {
      const first = String(altText || "").trim().slice(0, 1) || "?";
      return `
        <div class="image-shell">
          <div class="image-fallback">${escapeHtml(first)}</div>
          ${badge ? `<span class="image-badge">${escapeHtml(badge)}</span>` : ""}
        </div>
      `;
    }
    return `
      <div class="image-shell">
        <img class="drink-image" src="${escapeHtml(resolvedUrl)}" alt="${escapeHtml(altText || "drink image")}" loading="lazy" style="object-fit:${objectFit}" />
        ${badge ? `<span class="image-badge">${escapeHtml(badge)}</span>` : ""}
      </div>
    `;
  }

  root.utils = {
    escapeHtml,
    formatCurrency,
    formatDateShort,
    formatMonthKey,
    getCalendarDates,
    getMonthKey,
    renderImage,
    resolveAssetUrl,
    shiftMonthKey
  };
})();
