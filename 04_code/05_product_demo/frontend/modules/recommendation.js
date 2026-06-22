(() => {
  const root = (window.HeKouModules = window.HeKouModules || {});
  const { constants, utils } = root;

  const { average, dedupe } = utils;
  const { encouragementTemplates, moodCatalog, preferenceCatalog } = constants;

  const defaultLikedCategoriesByMood = {
    tired: ["fruit_tea", "tea", "yogurt"],
    annoyed: ["tea", "fruit_tea"],
    empty: ["milk_tea", "latte", "yogurt", "coffee_latte"],
    light: ["fruit_tea", "tea", "yogurt"],
    unclear: ["fruit_tea", "tea", "milk_tea"]
  };

  function getMood(code) {
    return moodCatalog.find((item) => item.code === code) || null;
  }

  function getPreference(code) {
    return preferenceCatalog.find((item) => item.code === code) || null;
  }

  function buildApiPayload(form) {
    const mood = getMood(form.mood);
    const selectedPreferences = (form.preferences || []).map((code) => getPreference(code)).filter(Boolean);
    const likedCategories = dedupe(
      selectedPreferences.flatMap((item) => item.categories || []).concat(defaultLikedCategoriesByMood[form.mood] || ["fruit_tea", "tea"])
    );
    const sweetPref =
      average(selectedPreferences.map((item) => Number(item.sweetPref || 0)).filter((value) => !Number.isNaN(value))) || 2.0;
    const caffeinePrefLevel =
      average(selectedPreferences.map((item) => Number(item.caffeinePrefLevel || 0)).filter((value) => !Number.isNaN(value))) || 1.8;
    const microAdjusts = dedupe(selectedPreferences.flatMap((item) => item.microAdjusts || [])).filter(Boolean);

    return {
      entry_mode: "mood",
      goal: mood?.payload.goal || "refresh",
      mood: mood?.payload.mood || "none",
      scene: "",
      budget_band: "high",
      temperature_pref: "any",
      caffeine_pref: "allow",
      dairy_avoid: false,
      micro_adjusts: microAdjusts,
      profile: {
        sweet_pref: sweetPref,
        caffeine_pref_level: caffeinePrefLevel,
        usual_temp: "",
        liked_categories: likedCategories,
        disliked_categories: []
      },
      top_k: 4
    };
  }

  function buildServingNote(candidate) {
    const optionGroups = candidate?.option_summary || [];
    const canSugar = optionGroups.some((item) => item.group_type === "sugar_level");
    const canIce = optionGroups.some((item) => item.group_type === "ice_level");

    if (candidate?.available_hot && !candidate?.available_cold) {
      return "推荐喝法：先按门店标准热饮做法，味道通常更完整。";
    }
    if (candidate?.available_cold && !candidate?.available_hot) {
      return "推荐喝法：先按门店标准冷饮做法，入口会更利落。";
    }
    if (canSugar && canIce) {
      return "推荐喝法：先按门店标准做法，最接近它本来的状态。";
    }
    if (canSugar) {
      return "推荐喝法：先按门店默认甜度试一次，更容易判断是不是你的菜。";
    }
    return "推荐喝法：先按门店标准做法，给自己一个最省心的答案。";
  }

  function buildEncouragement({ moodCode, resultIndex = 0 }) {
    const lines = encouragementTemplates[moodCode] || encouragementTemplates.unclear || [];
    if (!lines.length) {
      return "先喝一口，再继续。";
    }
    return lines[resultIndex % lines.length];
  }

  function buildTasteChips(candidate, selectedPreferenceCodes = []) {
    const chips = [];
    const fromSystem = candidate?.explanation_tags || [];
    chips.push(...fromSystem.slice(0, 2));
    selectedPreferenceCodes.forEach((code) => {
      const preference = getPreference(code);
      if (preference) {
        chips.push(preference.label);
      }
    });
    return dedupe(chips).slice(0, 3);
  }

  root.recommendation = {
    buildApiPayload,
    buildEncouragement,
    buildServingNote,
    buildTasteChips,
    getMood,
    getPreference
  };
})();
