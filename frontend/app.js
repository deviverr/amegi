// ===== Стан =====
let pendingImage = null; // data-URL скріншота

const $ = (id) => document.getElementById(id);
const messages = $("messages");
const gameSel = $("game");
const providerSel = $("provider");
const apiKeyInput = $("apiKey");

const EXAMPLES = [
  "Як перемогти Стіну плоті в Terraria?",
  "Який фокус відкрити першим за Німеччину в HoI4?",
  "Як зробити автоматичну ферму заліза в Minecraft?",
  "Як вижити першу зиму в Don't Starve Together?",
  "Що качати спочатку на Destiny Board в Albion Online?",
];

// ===== Ініціалізація =====
async function init() {
  // Збережені налаштування
  providerSel.value = localStorage.getItem("provider") || "groq";
  loadKeyForProvider();

  // Завантажити список ігор
  try {
    const r = await fetch("/api/games");
    const data = await r.json();
    const list = $("gamesList");
    data.games.forEach((g) => {
      const opt = document.createElement("option");
      opt.value = g.id;
      opt.textContent = g.name;
      gameSel.appendChild(opt);

      const chip = document.createElement("div");
      chip.className = "game-chip";
      chip.innerHTML = `<b>${g.name}</b><br><span>${g.wiki}</span>`;
      list.appendChild(chip);
    });
    if (data.default_provider) providerSel.value = localStorage.getItem("provider") || data.default_provider;
  } catch (e) {
    console.error(e);
  }

  // Приклади
  const ex = $("examples");
  EXAMPLES.forEach((t) => {
    const b = document.createElement("button");
    b.className = "example";
    b.textContent = t;
    b.onclick = () => { $("input").value = t; $("input").focus(); autoGrow(); };
    ex.appendChild(b);
  });
}

function loadKeyForProvider() {
  const p = providerSel.value;
  apiKeyInput.value = localStorage.getItem("key_" + p) || "";
  $("keyHint").textContent =
    p === "groq"
      ? "Отримати: console.groq.com/keys"
      : "Отримати: openrouter.ai/keys";
}

providerSel.onchange = () => {
  localStorage.setItem("provider", providerSel.value);
  loadKeyForProvider();
};
apiKeyInput.oninput = () => {
  localStorage.setItem("key_" + providerSel.value, apiKeyInput.value.trim());
};

// ===== Введення тексту =====
const input = $("input");
function autoGrow() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
}
input.addEventListener("input", autoGrow);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("composer").requestSubmit();
  }
});

// ===== Зображення =====
$("attachBtn").onclick = () => $("fileInput").click();
$("fileInput").onchange = (e) => {
  if (e.target.files[0]) readImage(e.target.files[0]);
};
$("removeImg").onclick = clearImage;

window.addEventListener("paste", (e) => {
  const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
  if (item) readImage(item.getAsFile());
});

function readImage(file) {
  const reader = new FileReader();
  reader.onload = () => {
    pendingImage = reader.result;
    $("previewImg").src = pendingImage;
    $("preview").hidden = false;
  };
  reader.readAsDataURL(file);
}
function clearImage() {
  pendingImage = null;
  $("preview").hidden = true;
  $("fileInput").value = "";
}

// ===== Надсилання =====
$("composer").addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question && !pendingImage) return;

  const key = apiKeyInput.value.trim();
  if (!key) {
    addError("Вкажіть ключ API у боковій панелі (Groq або OpenRouter). Це безкоштовно.");
    return;
  }

  clearWelcome();
  addUserMessage(question, pendingImage);

  const payload = {
    question,
    game: gameSel.value,
    image: pendingImage,
    provider: providerSel.value,
    api_key: key,
  };

  input.value = "";
  autoGrow();
  const img = pendingImage;
  clearImage();

  const loader = addLoader();
  $("sendBtn").disabled = true;

  try {
    const r = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await r.json();
    loader.remove();
    if (!r.ok) {
      addError(data.error || `Помилка ${r.status}`);
    } else {
      addBotMessage(data);
    }
  } catch (err) {
    loader.remove();
    addError("Не вдалося зв'язатися із сервером: " + err.message);
  } finally {
    $("sendBtn").disabled = false;
  }
});

// ===== Рендеринг повідомлень =====
function clearWelcome() {
  const w = messages.querySelector(".welcome");
  if (w) w.remove();
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

// Мінімальне форматування: **жирний** та посилання-цитати [1]
function formatAnswer(text, sources) {
  let html = escapeHtml(text);
  html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  const urls = {};
  (sources || []).forEach((s) => (urls[s.n] = s.url));
  html = html.replace(/\[(\d+)\]/g, (m, n) => {
    const url = urls[n];
    return url
      ? `<a class="cite" href="${url}" target="_blank" rel="noopener">[${n}]</a>`
      : `<span class="cite">[${n}]</span>`;
  });
  return html;
}

function addUserMessage(text, image) {
  const el = document.createElement("div");
  el.className = "msg user";
  el.innerHTML = `
    <div class="bubble">
      ${text ? `<div class="answer-text">${escapeHtml(text)}</div>` : ""}
      ${image ? `<img class="shot" src="${image}" alt="скріншот" />` : ""}
    </div>
    <div class="avatar">🧑</div>`;
  messages.appendChild(el);
  scrollDown();
}

function addBotMessage(data) {
  const el = document.createElement("div");
  el.className = "msg bot";

  let sourcesHtml = "";
  if (data.sources && data.sources.length) {
    sourcesHtml =
      `<div class="sources"><h4>Джерела — ${escapeHtml(data.game_name)}</h4>` +
      data.sources
        .map(
          (s) =>
            `<div class="source"><span class="num">[${s.n}]</span>
             <a href="${s.url}" target="_blank" rel="noopener">${escapeHtml(s.title)}</a></div>`
        )
        .join("") +
      `</div>`;
  }

  const tags = `
    <div class="meta">
      <span class="tag game">🎮 ${escapeHtml(data.game_name)}</span>
      <span class="tag">${escapeHtml(data.provider)}</span>
      ${data.used_image ? '<span class="tag">🖼️ скріншот</span>' : ""}
      ${!data.sources?.length ? '<span class="tag">⚠️ без джерел вікі</span>' : ""}
    </div>`;

  el.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="bubble">
      ${tags}
      <div class="answer-text">${formatAnswer(data.answer, data.sources)}</div>
      ${sourcesHtml}
    </div>`;
  messages.appendChild(el);
  scrollDown();
}

function addLoader() {
  const el = document.createElement("div");
  el.className = "msg bot";
  el.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="bubble"><div class="dots"><span></span><span></span><span></span></div>
    <small style="color:var(--muted)"> шукаю у вікі та формую відповідь…</small></div>`;
  messages.appendChild(el);
  scrollDown();
  return el;
}

function addError(text) {
  clearWelcome();
  const el = document.createElement("div");
  el.className = "msg bot";
  el.innerHTML = `
    <div class="avatar">⚠️</div>
    <div class="bubble error-bubble"><div class="answer-text">${escapeHtml(text)}</div></div>`;
  messages.appendChild(el);
  scrollDown();
}

function scrollDown() {
  messages.scrollTop = messages.scrollHeight;
}

init();
