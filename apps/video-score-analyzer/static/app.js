const $ = (selector) => document.querySelector(selector);

const videoInput = $("#videoInput");
const preview = $("#preview");
const analyzeBtn = $("#analyzeBtn");
const calibrateBtn = $("#calibrateBtn");
const statusEl = $("#status");
const hint = $("#hint");

let currentReport = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function setText(selector, value) {
  $(selector).textContent = value ?? "--";
}

function scoreClass(score) {
  if (score >= 75) return "good";
  if (score >= 60) return "warn";
  return "bad";
}

function renderReport(report) {
  currentReport = report;
  const { video, scores } = report;
  setText("#totalScore", scores.total);
  setText("#advice", scores.advice);
  setText("#tiktokScore", scores.platforms.tiktok.score);
  setText("#reelsScore", scores.platforms.instagram_reels.score);
  setText("#shortsScore", scores.platforms.youtube_shorts.score);
  renderFacts(video);
  renderGolden(scores.golden_3s);
  renderDimensions(scores.dimensions);
  renderTimeline(report.frames);
  renderShots(report.shots);
  renderExports(report.exports);
  renderPerformanceResult(null);
}

function renderFacts(video) {
  const facts = [
    ["文件", video.file_name],
    ["大小", `${video.file_size_mb} MB`],
    ["时长", video.duration_label],
    ["分辨率", video.resolution],
    ["比例", video.aspect_ratio],
    ["9:16 竖屏", video.is_vertical_9_16 ? "是" : "否，需要裁剪或重导出"],
    ["帧率", `${video.fps} fps`],
    ["音频", video.has_audio ? "有" : "没有"],
    ["编码", `${video.video_codec} / ${video.audio_codec}`],
  ];
  $("#videoFacts").innerHTML = facts.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
}

function renderGolden(golden) {
  setText("#goldenScore", golden.score);
  setText("#goldenRisk", `滑走风险：${golden.risk}`);
  setText("#goldenIssue", golden.biggest_issue);
  $("#openingTips").innerHTML = golden.rewrite_opening.map((tip) => `<li>${tip}</li>`).join("");
}

function labelForDimension(key) {
  const labels = {
    golden_3s: "黄金三秒",
    structure: "视频结构",
    rhythm: "镜头节奏",
    product_exposure: "产品露出",
    emotional_value: "情绪价值",
    visual_quality: "画面质量",
    platform_fit: "平台适配",
    cta_conversion: "CTA / 转化",
  };
  return labels[key] || key;
}

function renderDimensions(dimensions) {
  $("#dimensionBars").innerHTML = Object.entries(dimensions)
    .map(([key, item]) => {
      const score = item.score;
      return `
        <div class="bar-row" title="${item.reason}">
          <strong>${labelForDimension(key)}</strong>
          <div class="bar-track"><div class="bar-fill" style="width:${score}%"></div></div>
          <span>${score}</span>
        </div>
      `;
    })
    .join("");
}

function renderTimeline(frames) {
  $("#timeline").innerHTML = frames
    .filter((frame) => frame.image_url)
    .map(
      (frame) => `
        <div class="frame-card">
          <img src="${frame.image_url}" alt="${frame.time_label}">
          <div>
            <strong>${frame.time_label}</strong><br>
            可用 ${frame.ad_usability_score ?? "--"} / 变化 ${frame.change_score ?? "--"}
          </div>
        </div>
      `,
    )
    .join("");
}

function renderShots(shots) {
  $("#shots").innerHTML = shots
    .map(
      (shot) => `
        <div class="shot-row">
          <div class="shot-thumb">
            ${shot.frame_url ? `<img src="${shot.frame_url}" alt="镜头 ${shot.index}">` : ""}
          </div>
          <div class="shot-meta">
            <strong>#${shot.index}</strong>
            <span>${shot.start}-${shot.end}s</span>
            <span>代表帧 ${shot.frame_time || "--"}</span>
          </div>
          <span class="pill ${shot.keep ? "keep" : "cut"}">${shot.keep ? "保留" : "考虑删"}</span>
          <div class="shot-score">
            <strong>${shot.score}</strong>
            <span>可用分</span>
          </div>
          <p>${shot.issue}</p>
          <p>${shot.suggestion}</p>
        </div>
      `,
    )
    .join("");
}

function renderExports(exports) {
  $("#exports").innerHTML = `
    <a href="${exports.markdown}" target="_blank">下载 Markdown 报告</a>
    <a href="${exports.csv}" target="_blank">下载 CSV 帧数据</a>
    <a href="${exports.json}" target="_blank">下载 JSON 全量结果</a>
  `;
}

function numericValue(selector) {
  const value = Number($(selector).value || 0);
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function performanceLevel(score) {
  if (score >= 85) return "强：实际数据说明内容有效，可以反向修正素材判断。";
  if (score >= 70) return "不错：有继续测试价值，优先优化开头和字幕。";
  if (score >= 55) return "一般：数据还不能证明适合放量。";
  return "弱：真实数据也不支持放量，建议重剪或换素材。";
}

function renderPerformanceResult(result) {
  const box = $("#performanceResult");
  if (!result) {
    box.innerHTML = "先分析视频，再填真实发布数据。数据表现好时，系统会提示“内容可能有效，低分原因来自视觉规则误判”。";
    return;
  }
  box.innerHTML = `
    <div class="performance-score">
      <div><span>实际表现分</span><strong>${result.performanceScore}</strong></div>
      <div><span>校准后综合分</span><strong>${result.calibratedScore}</strong></div>
    </div>
    <p><strong>${result.level}</strong></p>
    <p>互动率：${result.engagementRate}%；强互动率：${result.strongEngagementRate}%；留存参考：${result.retentionLabel}</p>
    <p>${result.note}</p>
  `;
}

function calibrateWithPerformance() {
  if (!currentReport) {
    renderPerformanceResult({ performanceScore: 0, calibratedScore: 0, level: "请先分析视频。", engagementRate: 0, strongEngagementRate: 0, retentionLabel: "--", note: "还没有素材体检分，不能校准。" });
    return;
  }
  const views = numericValue("#viewsInput");
  if (!views) {
    renderPerformanceResult({ performanceScore: 0, calibratedScore: currentReport.scores.total, level: "请至少填写播放量。", engagementRate: 0, strongEngagementRate: 0, retentionLabel: "--", note: "没有播放量时，互动率和表现分没有分母。" });
    return;
  }
  const likes = numericValue("#likesInput");
  const comments = numericValue("#commentsInput");
  const shares = numericValue("#sharesInput");
  const saves = numericValue("#savesInput");
  const completion = numericValue("#completionInput");
  const avgWatch = numericValue("#avgWatchInput");
  const duration = Number(currentReport.video.duration_seconds || 0);

  const engagementRate = ((likes + comments + shares + saves) / views) * 100;
  const strongEngagementRate = ((comments * 4 + shares * 6 + saves * 5) / views) * 100;
  const engagementScore = clampScore(engagementRate * 11);
  const strongScore = clampScore(strongEngagementRate * 18);
  const completionScore = completion ? clampScore(completion * 1.25) : 0;
  const avgWatchScore = avgWatch && duration ? clampScore((avgWatch / duration) * 125) : 0;
  const retentionScore = completion && avgWatchScore ? Math.round((completionScore + avgWatchScore) / 2) : completionScore || avgWatchScore || 55;
  const performanceScore = clampScore(engagementScore * 0.35 + strongScore * 0.3 + retentionScore * 0.35);
  const materialScore = Number(currentReport.scores.total || 0);
  const calibratedScore = clampScore(materialScore * 0.35 + performanceScore * 0.65);

  let note = "校准后综合分更相信真实发布数据，因为播放后的用户反馈比画面启发式更接近市场结果。";
  if (performanceScore - materialScore >= 18) {
    note = "真实表现明显高于素材体检分：说明这个视频可能有真实感、人物/场景吸引力或平台分发优势，是当前算法低估了它。";
  } else if (materialScore - performanceScore >= 18) {
    note = "素材体检分高但真实表现低：说明画面合格不等于用户愿意看，优先检查开头钩子、标题、封面和投放人群。";
  }

  renderPerformanceResult({
    performanceScore,
    calibratedScore,
    level: performanceLevel(performanceScore),
    engagementRate: engagementRate.toFixed(2),
    strongEngagementRate: strongEngagementRate.toFixed(2),
    retentionLabel: completion ? `${completion}% 完播` : avgWatch ? `${avgWatch}s / ${duration.toFixed(1)}s` : "未填写，按中性值处理",
    note,
  });
}

videoInput.addEventListener("change", () => {
  const file = videoInput.files[0];
  if (!file) return;
  preview.src = URL.createObjectURL(file);
  hint.textContent = `已选择：${file.name}。点击“开始分析”后会在本地抽帧和评分。`;
});

analyzeBtn.addEventListener("click", async () => {
  const file = videoInput.files[0];
  if (!file) {
    hint.textContent = "请先选择一个视频。";
    return;
  }
  const form = new FormData();
  form.append("video", file);
  analyzeBtn.disabled = true;
  setStatus("Analyzing");
  hint.textContent = "正在分析：读取视频信息、抽帧、检测音频、生成时间轴。短视频一般几十秒内完成。";
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "分析失败");
    renderReport(data.report);
    setStatus("Done");
    hint.textContent = `完成：${data.report.video.file_name}`;
  } catch (error) {
    setStatus("Failed");
    hint.textContent = error.message;
  } finally {
    analyzeBtn.disabled = false;
  }
});

calibrateBtn.addEventListener("click", calibrateWithPerformance);
