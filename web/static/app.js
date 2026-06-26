const state = {
  user: null,
  samples: [],
  selectedImagePath: "",
  selectedImageUrl: "",
};

const $ = (selector) => document.querySelector(selector);

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json();
}

function levelClass(level, abnormal) {
  if (level === "严重变质" || level === "无效图像") return "bad";
  if (abnormal || level === "轻微变质") return "warn";
  if (level === "优质" || level === "新鲜合格") return "good";
  return "neutral";
}

function setPreview(path, url) {
  state.selectedImagePath = path;
  state.selectedImageUrl = url;
  $("#previewImage").src = url;
}

async function loadSamples() {
  state.samples = await requestJson("/api/samples");
  const select = $("#sampleSelect");
  select.innerHTML = state.samples
    .map((sample, index) => `<option value="${index}">${sample.label}</option>`)
    .join("");
  if (state.samples.length > 0) {
    setPreview(state.samples[0].path, state.samples[0].url);
  }
}

async function login(event) {
  event.preventDefault();
  const payload = {
    username: $("#username").value.trim(),
    password: $("#password").value,
  };
  const data = await requestJson("/api/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  $("#loginMessage").textContent = data.message;
  if (!data.success) return;

  state.user = data;
  $("#currentRole").textContent = `${data.username}（${data.role}）`;
  $("#operatorPill").textContent = `${data.role}：${data.username}`;
  $("#permissionChips").innerHTML = data.permissions.map((item) => `<span class="chip">${item}</span>`).join("");
}

async function uploadImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    const data = await requestJson("/api/upload", {
      method: "POST",
      body: JSON.stringify({ filename: file.name, dataUrl: reader.result }),
    });
    if (data.success) {
      setPreview(data.path, data.url);
    }
  };
  reader.readAsDataURL(file);
}

async function recognize() {
  if (!state.selectedImagePath) return;
  const operator = state.user ? `${state.user.role}-${state.user.username}` : "未登录检测员";
  const data = await requestJson("/api/recognize", {
    method: "POST",
    body: JSON.stringify({ imagePath: state.selectedImagePath, operator }),
  });
  renderResult(data);
  await refreshRecords();
  await refreshStats();
}

function renderResult(data) {
  const cls = levelClass(data.fresh_level, data.is_abnormal);
  $("#resultCard").querySelector(".status-chip").className = `status-chip ${cls}`;
  $("#resultCard").querySelector(".status-chip").textContent = data.success ? "识别完成" : "质量拦截";
  $("#resultLevel").textContent = data.fresh_level;
  $("#confidence").textContent = data.confidence ? `${Math.round(data.confidence * 100)}%` : "-";
  $("#score").textContent = data.freshness_score;
  $("#abnormal").textContent = data.is_abnormal ? "异常" : "正常";
  $("#warningText").textContent = data.warning || data.message;
  renderFeatures(data.features || {});
}

function renderFeatures(features) {
  const labels = {
    brightness: "亮度",
    contrast: "对比度",
    sharpness: "清晰度",
    tomato_ratio: "番茄区域",
    red_ratio: "红色比例",
    green_ratio: "绿色比例",
    dark_spot_ratio: "暗斑比例",
    brown_ratio: "棕褐比例",
    edge_score: "纹理强度",
  };
  $("#featureGrid").innerHTML = Object.entries(labels)
    .map(([key, label]) => `<div><span>${features[key] ?? "-"}</span><small>${label}</small></div>`)
    .join("");
}

async function refreshRecords() {
  const level = $("#levelFilter").value;
  const abnormal = $("#abnormalFilter").value;
  const params = new URLSearchParams();
  if (level) params.set("level", level);
  if (abnormal) params.set("abnormal", abnormal);
  const records = await requestJson(`/api/records?${params.toString()}`);
  renderRecords(records);
  renderAlerts(records.filter((item) => item.is_abnormal).slice(0, 5));
}

function renderRecords(records) {
  $("#recordBody").innerHTML = records
    .map((item) => {
      const cls = levelClass(item.fresh_level, item.is_abnormal);
      return `
        <tr>
          <td>${item.created_at || "-"}</td>
          <td>${item.operator || "-"}</td>
          <td><img class="thumb" src="${item.image_url}" alt="检测图片" /></td>
          <td><span class="status-chip ${cls}">${item.fresh_level}</span></td>
          <td>${item.confidence ? Math.round(item.confidence * 100) + "%" : "-"}</td>
          <td>${item.is_abnormal ? "异常" : "正常"}</td>
        </tr>
      `;
    })
    .join("");
}

function renderAlerts(records) {
  $("#alertList").innerHTML =
    records.length === 0
      ? `<p class="notice">当前筛选范围内暂无异常记录。</p>`
      : records
          .map(
            (item) => `
              <div class="alert-item">
                <strong>${item.fresh_level}：${item.warning}</strong>
                <span>${item.created_at} · ${item.operator || "-"} · 置信度 ${item.confidence ? Math.round(item.confidence * 100) + "%" : "-"}</span>
              </div>
            `,
          )
          .join("");
}

async function refreshStats() {
  const stats = await requestJson("/api/stats");
  $("#metricTotal").textContent = stats.total;
  $("#metricSuccess").textContent = stats.success_count;
  $("#metricQualified").textContent = `${stats.qualified_rate}%`;
  $("#metricAbnormal").textContent = `${stats.abnormal_rate}%`;
  renderChart(stats.level_counts);
}

function renderChart(counts) {
  const entries = Object.entries(counts);
  const max = Math.max(1, ...entries.map(([, value]) => value));
  $("#levelChart").innerHTML = entries
    .map(([label, value]) => {
      const width = Math.max(4, Math.round((value / max) * 100));
      const color = label === "严重变质" ? "#c24135" : label === "轻微变质" ? "#c77712" : "#1f7a4d";
      return `
        <div class="bar-row">
          <strong>${label}</strong>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%; background:${color}"></div></div>
          <span>${value}</span>
        </div>
      `;
    })
    .join("");
}

async function loadTests() {
  const rows = await requestJson("/api/tests");
  $("#testBody").innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td>${item.name}</td>
          <td>${item.input}</td>
          <td>${item.expected}</td>
          <td class="pass">${item.status}</td>
        </tr>
      `,
    )
    .join("");
}

function bindEvents() {
  $("#loginForm").addEventListener("submit", login);
  $("#sampleSelect").addEventListener("change", (event) => {
    const sample = state.samples[Number(event.target.value)];
    setPreview(sample.path, sample.url);
  });
  $("#uploadInput").addEventListener("change", uploadImage);
  $("#detectBtn").addEventListener("click", recognize);
  $("#levelFilter").addEventListener("change", refreshRecords);
  $("#abnormalFilter").addEventListener("change", refreshRecords);
}

async function init() {
  bindEvents();
  await loadSamples();
  await loadTests();
  await refreshRecords();
  await refreshStats();
  await login(new Event("submit"));
}

init().catch((error) => {
  console.error(error);
  $("#loginMessage").textContent = error.message;
});
