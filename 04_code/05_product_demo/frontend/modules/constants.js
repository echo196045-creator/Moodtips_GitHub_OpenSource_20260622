(() => {
  const root = (window.HeKouModules = window.HeKouModules || {});

  root.constants = {
    appName: "Moodtips",
    appTag: "饮品提示",
    appSlogan: "跟着心情喝。",
    appSubline: "选一个现在的你。",
    homePromise: "四种状态，随手点。",
    weekLabels: ["一", "二", "三", "四", "五", "六", "日"],
    moodQuadrants: {
      spark: {
        label: "开心",
        color: "#7f9f9e",
        recapLine: "这个月，开心出现得更多一点。"
      },
      ease: {
        label: "躺平",
        color: "#a6bcbc",
        recapLine: "这个月，你更常把节奏放慢。"
      },
      cooldown: {
        label: "烦躁",
        color: "#86a6bf",
        recapLine: "这个月，你更常想先降一降噪。"
      },
      recharge: {
        label: "难受",
        color: "#aeb8cb",
        recapLine: "这个月，你更常需要缓一缓。"
      }
    },
    moods: [
      {
        code: "spark",
        quadrant: "spark",
        title: "开心",
        subtitle: "",
        sticker: "./assets/moods/mood-uploaded-happy.png",
        alt: "开心表情包"
      },
      {
        code: "ease",
        quadrant: "ease",
        title: "躺平",
        subtitle: "",
        sticker: "./assets/moods/mood-uploaded-ease.png",
        alt: "躺平表情包"
      },
      {
        code: "cooldown",
        quadrant: "cooldown",
        title: "烦躁",
        subtitle: "",
        sticker: "./assets/moods/mood-uploaded-angry.png",
        alt: "烦躁表情包"
      },
      {
        code: "recharge",
        quadrant: "recharge",
        title: "难受",
        subtitle: "",
        sticker: "./assets/moods/mood-uploaded-difficult.png",
        alt: "难受表情包"
      }
    ],
    priceOptions: [
      { code: "any", label: "都可以" },
      { code: "under_15", label: "15 内" },
      { code: "15_20", label: "15-20" },
      { code: "above_20", label: "20 以上" }
    ],
    temperatureOptions: [
      { code: "any", label: "都可以" },
      { code: "cold", label: "冷" },
      { code: "hot", label: "热" }
    ],
    caffeineOptions: [
      { code: "any", label: "都可以" },
      { code: "none", label: "无咖啡因" },
      { code: "low", label: "低咖啡因" },
      { code: "normal", label: "正常" },
      { code: "strong", label: "强咖啡因" }
    ],
    tasteOptions: [
      { code: "fresh", label: "清新" },
      { code: "tea_forward", label: "茶感" },
      { code: "milky", label: "奶香" },
      { code: "fruity", label: "果香" },
      { code: "smooth", label: "顺口" },
      { code: "light", label: "轻盈" },
      { code: "sugar_free_friendly", label: "无糖友好" }
    ]
  };
})();
