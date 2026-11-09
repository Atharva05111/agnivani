"use strict";
const $ = (id) => document.getElementById(id);
const ZONE_EXAMPLES = [
  "Zone B ka temperature kitna hai?",
  "आग कुठे लागली आहे?",
  "Pump chalu aahe ka?",
  "Canteen se bahar kaise nikle?",
  "Is everything normal?",
  "अलार्म बंद करा",
];
const LANG_LABEL = { "mr-IN": "मराठी", "hi-IN": "हिंदी", "en-IN": "English" };

let latest = null;          // last /api/state payload
let settingsRendered = false;

// --------------------------------------------------------------- audio
let ctx = null;
const bufferCache = new Map();
function audioCtx() {
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
  return ctx;
}
async function unlockAudio() {
  const c = audioCtx();
  if (c.state !== "running") await c.resume().catch(() => {});
  $("soundBanner").hidden = c.state === "running";
}
document.addEventListener("pointerdown", unlockAudio, { capture: true });
document.addEventListener("keydown", unlockAudio, { capture: true });

async function loadBuffer(url) {
  if (bufferCache.has(url)) return bufferCache.get(url);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Audio unavailable (${res.status})`);
  const buf = await audioCtx().decodeAudioData(await res.arrayBuffer());
  bufferCache.set(url, buf);
  return buf;
}

let currentSource = null;
function playBuffer(buf) {
  return new Promise((resolve) => {
    const src = audioCtx().createBufferSource();
    src.buffer = buf;
    src.connect(audioCtx().destination);
    src.onended = () => { if (currentSource === src) currentSource = null; resolve(); };
    currentSource = src;
    src.start();
  });
}
function stopPlayback() {
  if (currentSource) { try { currentSource.stop(); } catch (_) {} currentSource = null; }
}

function playSiren(seconds = 1.8) {
  const c = audioCtx();
  return new Promise((resolve) => {
    const osc = c.createOscillator(), gain = c.createGain();
    osc.type = "square";
    const t0 = c.currentTime;
    for (let t = 0; t < seconds; t += 0.45) {
      osc.frequency.setValueAtTime(960, t0 + t);
      osc.frequency.setValueAtTime(740, t0 + t + 0.225);
    }
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(0.08, t0 + 0.05);
    gain.gain.setValueAtTime(0.08, t0 + seconds - 0.08);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + seconds);
    osc.connect(gain).connect(c.destination);
    osc.start(t0); osc.stop(t0 + seconds);
    osc.onended = resolve;
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ------------------------------------------------- alarm announcement loop
const loop = { alarmId: null, running: false, paused: false, playingLang: null };

function alarmActive() {
  return latest && latest.alarm && !latest.alarm.acknowledged;
}

async function runAlarmLoop(alarmId) {
  loop.running = true;
  while (alarmActive() && latest.alarm.id === alarmId) {
    if (loop.paused || audioCtx().state !== "running") { await sleep(300); continue; }
    await playSiren();
    for (const ann of latest.announcements || []) {
      if (!alarmActive() || latest.alarm.id !== alarmId) break;
      while (loop.paused) await sleep(200);
      if (!ann.audio) continue;
      try {
        const buf = await loadBuffer(ann.audio);
        loop.playingLang = ann.lang; renderAnnouncements();
        await playBuffer(buf);
      } catch (e) { console.warn(e); }
      loop.playingLang = null; renderAnnouncements();
      await sleep(350);
    }
    await sleep(600);
  }
  loop.running = false; loop.playingLang = null; renderAnnouncements();
}

function syncAlarmLoop() {
  if (alarmActive()) {
    if (!loop.running || loop.alarmId !== latest.alarm.id) {
      loop.alarmId = latest.alarm.id;
      if (!loop.running) runAlarmLoop(latest.alarm.id);
    }
    if (audioCtx().state !== "running") $("soundBanner").hidden = false;
  } else if (loop.running) {
    stopPlayback();
  }
}

// ---------------------------------------------------------------- render
function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null) n.append(kid);
  return n;
}

const STATUS_WORD = { normal: "Normal", warning: "Rising", fire: "Fire" };

function renderZones(s) {
  const lamps = $("lamps");
  lamps.replaceChildren(...s.zones.map((z) => el("article", {
    class: "lamp", "data-status": z.status,
    "data-silenced": String(!!(s.alarm && s.alarm.acknowledged && s.alarm.zone === z.id)),
  },
    el("p", { class: "lamp-id" }, `Zone ${z.id}, exit ${z.exit_no}`),
    el("p", { class: "lamp-state" }, STATUS_WORD[z.status]),
    el("h3", { class: "lamp-name" }, z.label),
    el("p", { class: "lamp-readings" },
      el("span", {}, el("b", {}, z.temp.toFixed(1)), el("span", {}, " °C")),
      el("span", {}, el("b", {}, z.smoke.toFixed(1)), el("span", {}, " % smoke"))),
  )));
  const p = s.pumps;
  $("pumproom").replaceChildren(
    el("div", { class: "pump-cell" }, el("p", {}, "Header pressure"), el("b", {}, `${p.pressure.toFixed(1)} bar`)),
    el("div", { class: "pump-cell" }, el("p", {}, "Main fire pump"), el("b", { class: p.main_pump ? "on" : "" }, p.main_pump ? "Running" : "Standby")),
    el("div", { class: "pump-cell" }, el("p", {}, "Jockey pump"), el("b", {}, p.jockey_pump ? "Running" : "Off")),
    el("div", { class: "pump-cell" }, el("p", {}, "Fire water tank"), el("b", {}, `${p.tank}%`)),
  );
}

function renderStatus(s) {
  const bar = $("statusbar"), text = $("statusText");
  const zone = s.alarm ? s.zones.find((z) => z.id === s.alarm.zone) : null;
  const warn = s.zones.filter((z) => z.status === "warning");
  if (s.alarm) {
    const src = { camera: "flame camera", sensor: "heat and smoke sensors", manual: "manual call point" }[s.alarm.source];
    bar.dataset.state = s.alarm.acknowledged ? "silenced" : "fire";
    text.textContent = s.alarm.acknowledged
      ? `Alarm silenced. ${zone.label} still in alarm until reset.`
      : `Fire in ${zone.label}, detected by ${src}. Evacuate through exit ${zone.exit_no}.`;
  } else if (warn.length) {
    bar.dataset.state = "warning";
    text.textContent = `Temperature rising in ${warn.map((z) => z.label).join(" and ")}`;
  } else {
    bar.dataset.state = "normal";
    text.textContent = "All zones normal";
  }
  $("silenceBtn").hidden = !(s.alarm && !s.alarm.acknowledged);
  $("resetBtn").hidden = !(s.alarm || warn.length);
}

function renderAnnouncements() {
  const s = latest;
  if (!s) return;
  const list = $("annList");
  $("announce").dataset.active = String(!!s.alarm);
  if (!s.alarm) {
    $("announceHint").textContent = "Plays in every language on this shift when an alarm goes off.";
    const names = s.languages.filter((l) => s.settings.shift_langs.includes(l.code)).map((l) => l.native);
    list.replaceChildren(el("li", { class: "ann-empty" }, `Ready in ${names.join(", ")}.`));
    return;
  }
  const voice = s.settings.voice_mode === "officer" ? "the safety officer's voice" : "Gnani Timbre voices";
  $("announceHint").textContent = s.alarm.acknowledged ? "Silenced. Reset the system once the area is clear." : `Looping in ${voice}.`;
  if (!s.announcements.length) {
    list.replaceChildren(el("li", { class: "ann-empty" }, "Preparing announcements…"));
    return;
  }
  list.replaceChildren(...s.announcements.map((a) => {
    const meta = s.languages.find((l) => l.code === a.lang);
    const state = a.error ? "Voice failed" : a.audio ? (loop.playingLang === a.lang ? "Speaking" : "Ready") : "Generating…";
    return el("li", { class: "ann", "data-playing": String(loop.playingLang === a.lang), title: a.error || "" },
      el("header", {}, el("b", {}, `${meta.native}${meta.native !== meta.english ? ` (${meta.english})` : ""}`), el("span", {}, state)),
      el("p", { lang: a.lang.slice(0, 2) }, a.text));
  }));
}

function renderSettings(s) {
  if (!settingsRendered) {
    $("langs").replaceChildren(...s.languages.map((l) => el("label", { class: "lang-toggle" },
      el("input", { type: "checkbox", value: l.code, onchange: saveLangs }),
      el("span", { lang: l.code.slice(0, 2) }, l.native === l.english ? l.native : `${l.native}`))));
    $("drillGrid").replaceChildren(...s.zones.flatMap((z) => [
      el("p", {}, z.label),
      el("button", { class: "btn btn-quiet", onclick: () => post("/api/drill/start", { zone: z.id }) }, "Heat and smoke rise"),
      el("button", { class: "btn btn-quiet", onclick: () => post("/api/drill/camera", { zone: z.id }) }, "Camera sees flames"),
    ]));
    settingsRendered = true;
  }
  for (const box of $("langs").querySelectorAll("input")) {
    if (document.activeElement !== box) box.checked = s.settings.shift_langs.includes(box.value);
  }
  const ready = s.settings.officer_voice_ready;
  $("voiceOfficer").disabled = !ready;
  for (const r of document.querySelectorAll('input[name="voice"]')) r.checked = r.value === s.settings.voice_mode;
  $("officerDel").hidden = !ready;
  if (!officerRecording && !officerBusy) {
    $("officerRec").textContent = ready ? "Re-record voice" : "Record officer's voice";
    if (!$("officerStatus").dataset.sticky) $("officerStatus").textContent = ready ? "Voice saved." : "";
  }
  $("keyBanner").hidden = s.settings.gnani_configured;
}

function renderEvents(s) {
  $("events").replaceChildren(...s.events.map((e) => el("li", {},
    el("time", {}, new Date(e.t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })),
    el("span", {}, e.msg))));
}

async function refresh() {
  try {
    const res = await fetch("/api/state");
    latest = await res.json();
    renderStatus(latest); renderZones(latest); renderAnnouncements(); renderSettings(latest); renderEvents(latest);
    syncAlarmLoop();
  } catch (e) {
    $("statusText").textContent = "Lost connection to the AgniVani server. Is it still running?";
  }
}

async function post(url, body, method = "POST") {
  const res = await fetch(url, {
    method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  refresh();
  return data;
}

$("silenceBtn").onclick = () => post("/api/alarm/silence");
$("resetBtn").onclick = () => { stopPlayback(); post("/api/reset"); };
$("soundBanner").onclick = unlockAudio;

function saveLangs() {
  const langs = [...$("langs").querySelectorAll("input:checked")].map((i) => i.value);
  if (!langs.length) { this.checked = true; return; }
  post("/api/settings", { shift_langs: langs }).catch((e) => alert(e.message));
}
for (const r of document.querySelectorAll('input[name="voice"]')) {
  r.onchange = () => post("/api/settings", { voice_mode: r.value }).catch((e) => alert(e.message));
}

// ------------------------------------------------------------ recording
class WavRecorder {
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.proc = this.ctx.createScriptProcessor(4096, 1, 1);
    this.chunks = [];
    this.proc.onaudioprocess = (e) => this.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    this.source.connect(this.proc);
    this.proc.connect(this.ctx.destination);
    this.startedAt = performance.now();
  }
  async stop(targetRate = 16000) {
    this.proc.disconnect(); this.source.disconnect();
    this.stream.getTracks().forEach((t) => t.stop());
    const rate = this.ctx.sampleRate;
    await this.ctx.close();
    const total = this.chunks.reduce((n, c) => n + c.length, 0);
    const all = new Float32Array(total);
    let off = 0;
    for (const c of this.chunks) { all.set(c, off); off += c.length; }
    const ratio = rate / targetRate, outLen = Math.floor(total / ratio);
    const pcm = new Int16Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const start = Math.floor(i * ratio), end = Math.min(total, Math.floor((i + 1) * ratio));
      let sum = 0;
      for (let j = start; j < end; j++) sum += all[j];
      const v = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
      pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
    }
    return { blob: wavBlob(pcm, targetRate), seconds: outLen / targetRate };
  }
}
function wavBlob(pcm, rate) {
  const buf = new ArrayBuffer(44 + pcm.length * 2), v = new DataView(buf);
  const str = (o, s) => [...s].forEach((ch, i) => v.setUint8(o + i, ch.charCodeAt(0)));
  str(0, "RIFF"); v.setUint32(4, 36 + pcm.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, pcm.length * 2, true);
  new Int16Array(buf, 44).set(pcm);
  return new Blob([buf], { type: "audio/wav" });
}

// --------------------------------------------------------------- console
const chat = $("chat");
function addMsg(node) {
  $("chatEmpty").hidden = true;
  chat.append(node);
  chat.scrollTop = chat.scrollHeight;
  return node;
}

async function speakReply(url) {
  if (!url) return;
  loop.paused = true; stopPlayback();
  try { await playBuffer(await loadBuffer(url)); } catch (e) { console.warn(e); }
  loop.paused = false;
}

function showReply(pending, data) {
  pending.classList.remove("msg-pending");
  pending.replaceChildren(
    el("small", {}, data.detected_language ? `You said (detected ${data.detected_language})` : "You asked"),
    data.transcript);
  const bot = el("li", { class: "msg msg-bot", lang: data.reply_language.slice(0, 2) },
    el("small", {}, `AgniVani, ${LANG_LABEL[data.reply_language]}`), data.reply);
  if (data.audio) bot.append(el("div", {}, el("button", { class: "btn btn-quiet", onclick: () => speakReply(data.audio) }, "Play again")));
  if (data.tts_error) bot.append(el("small", {}, `Voice reply failed: ${data.tts_error}`));
  addMsg(bot);
  speakReply(data.audio);
}

async function ask(form, label) {
  const pending = addMsg(el("li", { class: "msg msg-user msg-pending" }, el("small", {}, label), "…"));
  const lang = $("replyLang").value;
  if (lang) form.append("lang", lang);
  try {
    const isText = form.has("text");
    const res = await fetch(isText ? "/api/ask/text" : "/api/ask/audio", isText
      ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: form.get("text"), lang: lang || null }) }
      : { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    showReply(pending, data);
    refresh();
  } catch (e) {
    pending.remove();
    addMsg(el("li", { class: "msg-error" }, e.message));
  }
}

$("chips").replaceChildren(...ZONE_EXAMPLES.map((q) => el("button", {
  class: "chip", type: "button", onclick: () => { const f = new FormData(); f.append("text", q); ask(f, "You asked"); },
}, q)));

$("typeForm").onsubmit = (e) => {
  e.preventDefault();
  const q = $("typeInput").value.trim();
  if (!q) return;
  $("typeInput").value = "";
  const f = new FormData(); f.append("text", q); ask(f, "You asked");
};

// push-to-talk: hold, or tap once to start and again to stop
const mic = { rec: null, downAt: 0, toggle: false, timer: null };
async function micStart() {
  if (mic.rec) return;
  try {
    loop.paused = true; stopPlayback();
    mic.rec = new WavRecorder();
    await mic.rec.start();
    $("micBtn").setAttribute("aria-pressed", "true");
    $("micLabel").textContent = "Listening… release to send";
    mic.timer = setTimeout(micStop, 15000);
  } catch (e) {
    mic.rec = null; loop.paused = false;
    addMsg(el("li", { class: "msg-error" }, "Microphone blocked. Allow mic access for this page in the browser's address bar."));
  }
}
async function micStop() {
  if (!mic.rec) return;
  clearTimeout(mic.timer);
  const rec = mic.rec; mic.rec = null; mic.toggle = false;
  $("micBtn").setAttribute("aria-pressed", "false");
  $("micLabel").textContent = "Hold to talk";
  const { blob, seconds } = await rec.stop();
  loop.paused = false;
  if (seconds < 0.6) { addMsg(el("li", { class: "msg-error" }, "Too short. Hold the button while you speak.")); return; }
  const f = new FormData(); f.append("audio", blob, "question.wav");
  $("micBtn").disabled = true; $("micLabel").textContent = "Transcribing…";
  await ask(f, "Transcribing with Gnani Prisma");
  $("micBtn").disabled = false; $("micLabel").textContent = "Hold to talk";
}
$("micBtn").addEventListener("pointerdown", (e) => {
  e.preventDefault();
  if (mic.toggle) { micStop(); return; }
  mic.downAt = performance.now(); micStart();
});
$("micBtn").addEventListener("pointerup", () => {
  if (!mic.rec) return;
  if (performance.now() - mic.downAt < 350) { mic.toggle = true; $("micLabel").textContent = "Listening… tap to send"; return; }
  micStop();
});
$("micBtn").addEventListener("pointerleave", () => { if (mic.rec && !mic.toggle) micStop(); });
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !e.repeat && !/INPUT|SELECT|TEXTAREA|BUTTON/.test(document.activeElement.tagName)) { e.preventDefault(); micStart(); }
});
document.addEventListener("keyup", (e) => {
  if (e.code === "Space" && mic.rec && !mic.toggle) { e.preventDefault(); micStop(); }
});

// --------------------------------------------------------- officer voice
let officerRecording = false, officerBusy = false;
$("officerRec").onclick = async () => {
  const btn = $("officerRec"), status = $("officerStatus");
  if (officerRecording) return;
  const rec = new WavRecorder();
  try { await rec.start(); } catch (_) { status.textContent = "Microphone blocked. Allow mic access and try again."; return; }
  officerRecording = true; btn.disabled = true; status.dataset.sticky = "1";
  for (let s = 15; s > 0; s--) { status.textContent = `Recording… ${s}s left. Read the line above.`; await sleep(1000); }
  const { blob } = await rec.stop(16000);
  officerRecording = false; officerBusy = true;
  status.textContent = "Cloning voice with Gnani…";
  const f = new FormData(); f.append("audio", blob, "officer.wav");
  try {
    const res = await fetch("/api/officer-voice", { method: "POST", body: f });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    status.textContent = data.error ? `Voice saved, but the preview failed: ${data.error}` : "Voice saved. Playing a preview in Marathi.";
    if (data.preview) speakReply(data.preview);
  } catch (e) {
    status.textContent = e.message;
  } finally {
    officerBusy = false; btn.disabled = false;
    setTimeout(() => { delete status.dataset.sticky; }, 8000);
    refresh();
  }
};
$("officerDel").onclick = () => post("/api/officer-voice", null, "DELETE");

// ------------------------------------------------------------------ boot
refresh();
setInterval(refresh, 1000);
