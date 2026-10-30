"use strict";

// Settings page for claude-usage-smalltv. Plain JS on purpose: no build step, served by Python.

const I18N = {
  en: {
    subtitle: "Your Claude usage on a desk display",
    step: "Step {n} of {total}",
    next: "Continue",
    back: "Back",
    cancel: "Cancel",
    retry: "Check again",
    // step 1
    loginTitle: "Sign in to Claude",
    loginIntro: "The panel uses the login of Claude Code on this computer. No password or key is asked here.",
    loginOk: "Claude is connected",
    loginOkPlan: "Plan: {plan}",
    loginMissing: "Claude Code login not found",
    loginHow: "Install Claude Code, open a terminal and run {cmd} once to sign in with your Pro or Max account. Then come back here.",
    loginInstall: "How to install Claude Code",
    // step 2
    displayTitle: "Find your display",
    displayIntro: "Before searching:",
    tipPower: "Plug the display into a phone charger (5 V / 1 A or more).",
    tipWifi: "Connect it to the same Wi-Fi as this computer. It must be a 2.4 GHz network.",
    tipIp: "Right after power-on, the display shows its IP address on screen for a few seconds.",
    scan: "Search my network",
    scanning: "Searching… this can take up to a minute",
    scanNone: "No display answered. It may be asleep: type the IP shown on its screen below.",
    use: "Use this one",
    orType: "Or type the IP shown on the display:",
    ipPlaceholder: "e.g. 192.168.1.50",
    test: "Connect",
    testing: "Connecting…",
    found: "Found {firmware} at {host}",
    unreachable: "Nothing answered at {host}",
    unreachableHow: "Check that the display is on and on the same Wi-Fi, and that the IP is right. It may take a few seconds to wake up: try again.",
    unsupported: "{host} answered, but it is not a supported display",
    unsupportedHow: "Supported firmwares: SD PRO and GeekMagic stock (experimental). Check the IP: it may be another device on your network.",
    // step 3
    langTitle: "Choose the panel language",
    langIntro: "This is what the display will show. The numbers are your real usage.",
    // step 4
    confirmTitle: "Put the panel on the display",
    confirmIntro: "What happens now:",
    confirm1: "The panel is uploaded and becomes the only picture on screen.",
    confirm2: "Your other photos are only hidden, never deleted. The previous settings are saved so you can undo everything later.",
    confirm3: "From now on, the clock updates every minute and the usage every 5 minutes.",
    autostartLabel: "Start automatically when I sign in to this computer",
    autostartHint: "Recommended. Without it, the display stops updating when you close this program.",
    install: "Put the panel on the display",
    installing: "Setting up the display…",
    installed: "Done! Your display now shows your Claude usage.",
    // dashboard
    stateOnline: "Display up to date",
    stateOnlineDetail: "Last update at {time}.",
    stateConnecting: "Connecting to the display…",
    stateConnectingDetail: "This takes a few seconds.",
    stateOffline: "The display is not answering",
    stateOfflineDetail: "Check that it is plugged in and on the Wi-Fi. It will update by itself as soon as it is back, no need to do anything here.",
    stateUnsupported: "The device at this IP is not a supported display",
    stateUnsupportedDetail: "The display may have a new IP. Use \"Change display\" to find it again.",
    nowOnScreen: "On the display now",
    usage: "Usage",
    session: "5-hour session",
    weekly: "Weekly",
    resetsIn: "resets in {h}h{m}",
    resetsOn: "resets {day} at {time}",
    noWindow: "no active window",
    waiting: "Waiting for the first usage reading…",
    stale: "Showing numbers from {time}: Claude is limiting requests right now. It recovers by itself.",
    loginProblem: "Claude Code is signed out. Open a terminal and run {cmd} once.",
    usageProblem: "Usage is unavailable right now. It will try again in a minute.",
    weekSplit: "This week",
    display: "Display",
    address: "IP address",
    firmware: "Firmware",
    lastUpdate: "Last update",
    never: "not yet",
    changeDisplay: "Change display",
    handBack: "Give the display back",
    handBackConfirm: "Click again to confirm",
    handBackHint: "Brings back your previous photos and theme, and stops the panel.",
    handedBack: "Done: the display shows your previous photos again.",
    preferences: "Preferences",
    panelLang: "Panel language",
    showIp: "Show the IP on the display",
    showIpHint: "In small print under the logo, so you always know the display's address.",
    autostart: "Start with the computer",
    autostartOn: "The panel keeps updating after a restart.",
    autostartOff: "The panel only updates while this program is open.",
    autostartUnsupported: "Not available on this system.",
    saved: "Saved",
    activity: "Recent activity",
    noActivity: "Nothing to report.",
    bookmark: "Tip: bookmark this page ({url}) to come back anytime.",
    error: "Something went wrong: {msg}",
    offlineService: "The service is not running. Start claude-usage-smalltv again.",
    langName: { en: "English", pt: "Português" },
    weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  },
  pt: {
    subtitle: "Seu uso do Claude num display de mesa",
    step: "Passo {n} de {total}",
    next: "Continuar",
    back: "Voltar",
    cancel: "Cancelar",
    retry: "Verificar de novo",
    loginTitle: "Entre no Claude",
    loginIntro: "O painel usa o login do Claude Code deste computador. Nenhuma senha ou chave é pedida aqui.",
    loginOk: "Claude conectado",
    loginOkPlan: "Plano: {plan}",
    loginMissing: "Login do Claude Code não encontrado",
    loginHow: "Instale o Claude Code, abra um terminal e rode {cmd} uma vez para entrar com sua conta Pro ou Max. Depois volte aqui.",
    loginInstall: "Como instalar o Claude Code",
    displayTitle: "Encontre seu display",
    displayIntro: "Antes de procurar:",
    tipPower: "Ligue o display num carregador de celular (5 V / 1 A ou mais).",
    tipWifi: "Conecte-o ao mesmo Wi-Fi deste computador. Precisa ser uma rede de 2,4 GHz.",
    tipIp: "Logo depois de ligar, o display mostra o endereço IP na tela por alguns segundos.",
    scan: "Procurar na minha rede",
    scanning: "Procurando… pode levar até um minuto",
    scanNone: "Nenhum display respondeu. Ele pode estar dormindo: digite abaixo o IP que aparece na tela dele.",
    use: "Usar este",
    orType: "Ou digite o IP que aparece no display:",
    ipPlaceholder: "ex.: 192.168.1.50",
    test: "Conectar",
    testing: "Conectando…",
    found: "Encontrado: {firmware} em {host}",
    unreachable: "Nada respondeu em {host}",
    unreachableHow: "Confira se o display está ligado e no mesmo Wi-Fi, e se o IP está certo. Ele pode levar alguns segundos para acordar: tente de novo.",
    unsupported: "{host} respondeu, mas não é um display compatível",
    unsupportedHow: "Firmwares compatíveis: SD PRO e o original da GeekMagic (experimental). Confira o IP: pode ser outro aparelho da sua rede.",
    langTitle: "Escolha o idioma do painel",
    langIntro: "É isto que o display vai mostrar. Os números são o seu uso real.",
    confirmTitle: "Coloque o painel no display",
    confirmIntro: "O que acontece agora:",
    confirm1: "O painel é enviado e vira a única imagem na tela.",
    confirm2: "Suas outras fotos só ficam ocultas, nunca são apagadas. As configurações anteriores ficam salvas para você desfazer tudo depois.",
    confirm3: "A partir daí, o relógio atualiza a cada minuto e o uso a cada 5 minutos.",
    autostartLabel: "Iniciar sozinho quando eu entrar neste computador",
    autostartHint: "Recomendado. Sem isso, o display para de atualizar quando você fechar este programa.",
    install: "Colocar o painel no display",
    installing: "Configurando o display…",
    installed: "Pronto! Seu display agora mostra o seu uso do Claude.",
    stateOnline: "Display atualizado",
    stateOnlineDetail: "Última atualização às {time}.",
    stateConnecting: "Conectando ao display…",
    stateConnectingDetail: "Isso leva alguns segundos.",
    stateOffline: "O display não está respondendo",
    stateOfflineDetail: "Confira se ele está ligado e no Wi-Fi. Assim que voltar, ele atualiza sozinho, não precisa fazer nada aqui.",
    stateUnsupported: "O aparelho neste IP não é um display compatível",
    stateUnsupportedDetail: "O display pode ter mudado de IP. Use \"Trocar de display\" para encontrá-lo de novo.",
    nowOnScreen: "Na tela agora",
    usage: "Uso",
    session: "Sessão de 5 horas",
    weekly: "Semana",
    resetsIn: "renova em {h}h{m}",
    resetsOn: "renova {day} às {time}",
    noWindow: "sem janela ativa",
    waiting: "Aguardando a primeira leitura de uso…",
    stale: "Mostrando os números das {time}: o Claude está limitando as consultas agora. Volta sozinho.",
    loginProblem: "O Claude Code saiu da conta. Abra um terminal e rode {cmd} uma vez.",
    usageProblem: "O uso está indisponível agora. Uma nova tentativa é feita em um minuto.",
    weekSplit: "Nesta semana",
    display: "Display",
    address: "Endereço IP",
    firmware: "Firmware",
    lastUpdate: "Última atualização",
    never: "ainda não",
    changeDisplay: "Trocar de display",
    handBack: "Devolver o display",
    handBackConfirm: "Clique de novo para confirmar",
    handBackHint: "Traz de volta suas fotos e o tema anteriores, e para o painel.",
    handedBack: "Pronto: o display voltou a mostrar suas fotos anteriores.",
    preferences: "Preferências",
    panelLang: "Idioma do painel",
    showIp: "Mostrar o IP no display",
    showIpHint: "Em letra pequena, debaixo do logo, para você sempre saber o endereço do display.",
    autostart: "Iniciar com o computador",
    autostartOn: "O painel continua atualizando depois de reiniciar o computador.",
    autostartOff: "O painel só atualiza enquanto este programa estiver aberto.",
    autostartUnsupported: "Não disponível neste sistema.",
    saved: "Salvo",
    activity: "Atividade recente",
    noActivity: "Nada a relatar.",
    bookmark: "Dica: salve esta página ({url}) nos favoritos para voltar quando quiser.",
    error: "Algo deu errado: {msg}",
    offlineService: "O serviço não está rodando. Abra o claude-usage-smalltv de novo.",
    langName: { en: "English", pt: "Português" },
    weekdays: ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"],
  },
};

const STEPS = 4;
const app = document.getElementById("app");
const toastEl = document.getElementById("toast");

const state = {
  status: null,
  view: null, // "wizard" | "dashboard"
  step: 1,
  host: "",
  test: null,
  testing: false,
  scan: null,
  scanning: false,
  panelLang: null,
  autostart: true,
  installing: false,
  confirmHandBack: false,
  serviceDown: false,
};

let uiLang = pickLang();

// ------------------------------------------------------------------ helpers

function pickLang() {
  try {
    const saved = localStorage.getItem("ui-lang");
    if (saved && I18N[saved]) return saved;
  } catch (_) { /* storage blocked: fall back to the browser language */ }
  return (navigator.language || "en").toLowerCase().startsWith("pt") ? "pt" : "en";
}

function raw(key) {
  return I18N[uiLang][key] ?? I18N.en[key] ?? key;
}

function t(key, vars = {}) {
  const text = raw(key);
  return typeof text === "string" ? text.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "") : text;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Like t(), but HTML-escapes the variables and lets them carry markup (e.g. <code>).
function th(key, vars = {}) {
  return esc(raw(key)).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
}

function time(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString(uiLang === "pt" ? "pt-BR" : "en-US", {
    hour: "2-digit", minute: "2-digit",
  });
}

function resetText(win) {
  if (!win || !win.resets_at) return t("noWindow");
  const at = new Date(win.resets_at);
  const left = (at - Date.now()) / 1000;
  if (left < 24 * 3600) {
    const minutes = Math.max(0, Math.floor(left / 60));
    return t("resetsIn", { h: Math.floor(minutes / 60), m: String(minutes % 60).padStart(2, "0") });
  }
  return t("resetsOn", { day: t("weekdays")[at.getDay()], time: time(win.resets_at) });
}

function level(pct) {
  return pct >= 90 ? "danger" : pct >= 70 ? "warn" : "";
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  const resp = await fetch(path, options);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
  return data;
}

let toastTimer;
function toast(message, isError = false) {
  toastEl.textContent = message;
  toastEl.className = isError ? "toast error" : "toast";
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastEl.hidden = true; }, isError ? 7000 : 3500);
}

function previewUrl(lang) {
  // Changes once a minute, so the image follows the clock without flickering on every poll.
  return `/api/preview.png?lang=${encodeURIComponent(lang)}&t=${Math.floor(Date.now() / 60000)}`;
}

// ------------------------------------------------------------------- status

async function refresh() {
  try {
    state.status = await api("/api/status");
    state.serviceDown = false;
  } catch (_) {
    state.serviceDown = true;
  }
  if (state.status && state.view === null) {
    state.view = state.status.configured ? "dashboard" : "wizard";
    state.panelLang = state.status.configured ? state.status.lang : uiLang;
  }
  // Re-render the wizard only on the login step: elsewhere it would reset what is being typed.
  if (state.view === "dashboard" || state.step === 1 || state.serviceDown) render();
}

// ------------------------------------------------------------------- views

function render() {
  document.documentElement.lang = uiLang === "pt" ? "pt-BR" : "en";
  document.getElementById("subtitle").textContent = t("subtitle");
  document.querySelectorAll("[data-ui-lang]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.uiLang === uiLang));
  });
  if (state.status) document.getElementById("version").textContent = `v${state.status.version}`;

  if (state.serviceDown) {
    app.innerHTML = `<div class="note danger">${esc(t("offlineService"))}</div>`;
    return;
  }
  if (!state.status) return;
  app.innerHTML = state.view === "wizard" ? wizard() : dashboard();
}

function wizard() {
  const bars = Array.from({ length: STEPS }, (_, i) => {
    const cls = i + 1 < state.step ? "done" : i + 1 === state.step ? "current" : "";
    return `<li class="${cls}"></li>`;
  }).join("");
  const body = [stepLogin, stepDisplay, stepLanguage, stepConfirm][state.step - 1]();
  return `
    <section class="wizard">
      <ol class="steps" aria-hidden="true">${bars}</ol>
      <div class="card">
        <div class="step-label">${esc(t("step", { n: state.step, total: STEPS }))}</div>
        ${body}
      </div>
    </section>`;
}

function navButtons(canContinue, { back = state.step > 1, nextLabel = t("next") } = {}) {
  const left = back
    ? `<button class="btn" data-action="back">${esc(t("back"))}</button>`
    : state.status.configured
      ? `<button class="btn" data-action="cancel">${esc(t("cancel"))}</button>`
      : "<span></span>";
  return `
    <div class="actions">
      ${left}
      <button class="btn primary" data-action="next" ${canContinue ? "" : "disabled"}>${esc(nextLabel)}</button>
    </div>`;
}

function stepLogin() {
  const login = state.status.login;
  const result = login.ok
    ? `<div class="note ok"><strong>✓ ${esc(t("loginOk"))}</strong>${
      login.plan ? esc(t("loginOkPlan", { plan: login.plan.toUpperCase() })) : ""}</div>`
    : `<div class="note warn"><strong>${esc(t("loginMissing"))}</strong>
         ${th("loginHow", { cmd: "<code>claude</code>" })}
         <div class="row" style="margin-top:10px">
           <button class="btn" data-action="recheck">${esc(t("retry"))}</button>
           <a class="btn link" href="https://code.claude.com/docs/en/overview" target="_blank" rel="noopener">${esc(t("loginInstall"))}</a>
         </div>
       </div>`;
  return `
    <h2>${esc(t("loginTitle"))}</h2>
    <p class="muted">${esc(t("loginIntro"))}</p>
    ${result}
    ${navButtons(login.ok)}`;
}

function stepDisplay() {
  let scanBlock = "";
  if (state.scanning) {
    scanBlock = `<p class="row muted"><span class="spinner"></span>${esc(t("scanning"))}</p>`;
  } else if (state.scan && state.scan.length === 0) {
    scanBlock = `<div class="note">${esc(t("scanNone"))}</div>`;
  } else if (state.scan) {
    scanBlock = `<ul class="hosts">${state.scan.map((h) => `
      <li>
        <span><span class="ip">${esc(h.ip)}</span>
          ${h.smalltv ? '<span class="badge">SmallTV</span>' : ""}
          <br><span class="muted small">${esc(h.title || "—")}</span></span>
        <button class="btn" data-action="use-host" data-host="${esc(h.ip)}">${esc(t("use"))}</button>
      </li>`).join("")}</ul>`;
  }

  let result = "";
  if (state.testing) {
    result = `<p class="row muted"><span class="spinner"></span>${esc(t("testing"))}</p>`;
  } else if (state.test && state.test.ok) {
    result = `<div class="note ok"><strong>✓ ${esc(t("found", state.test))}</strong></div>`;
  } else if (state.test && state.test.reason === "unsupported") {
    result = `<div class="note danger"><strong>${esc(t("unsupported", state.test))}</strong>${esc(t("unsupportedHow"))}</div>`;
  } else if (state.test) {
    result = `<div class="note warn"><strong>${esc(t("unreachable", state.test))}</strong>${esc(t("unreachableHow"))}</div>`;
  }

  return `
    <h2>${esc(t("displayTitle"))}</h2>
    <p class="muted">${esc(t("displayIntro"))}</p>
    <ol class="tips">
      <li>${esc(t("tipPower"))}</li>
      <li>${esc(t("tipWifi"))}</li>
      <li>${esc(t("tipIp"))}</li>
    </ol>
    <p><button class="btn" data-action="scan" ${state.scanning ? "disabled" : ""}>${esc(t("scan"))}</button></p>
    ${scanBlock}
    <form class="row" data-form="test" style="margin-top:16px">
      <label for="host" class="small" style="flex-basis:100%">${esc(t("orType"))}</label>
      <input type="text" id="host" name="host" inputmode="decimal" autocomplete="off"
        placeholder="${esc(t("ipPlaceholder"))}" value="${esc(state.host)}">
      <button class="btn" type="submit" ${state.testing ? "disabled" : ""}>${esc(t("test"))}</button>
    </form>
    ${result}
    ${navButtons(Boolean(state.test && state.test.ok))}`;
}

function stepLanguage() {
  const options = state.status.languages.map((code) => `
    <label><input type="radio" name="panel-lang" value="${esc(code)}" data-change="panel-lang"
      ${code === state.panelLang ? "checked" : ""}> ${esc(t("langName")[code] || code)}</label>`).join("");
  return `
    <h2>${esc(t("langTitle"))}</h2>
    <p class="muted">${esc(t("langIntro"))}</p>
    <div class="choice">${options}</div>
    <img class="preview" src="${previewUrl(state.panelLang)}" alt="">
    ${navButtons(true)}`;
}

function stepConfirm() {
  const autostart = state.status.autostart.supported ? `
    <label class="check">
      <input type="checkbox" data-change="wizard-autostart" ${state.autostart ? "checked" : ""}>
      <span><strong>${esc(t("autostartLabel"))}</strong><br>
        <span class="muted small">${esc(t("autostartHint"))}</span></span>
    </label>` : "";
  const busy = state.installing
    ? `<p class="row muted"><span class="spinner"></span>${esc(t("installing"))}</p>` : "";
  return `
    <h2>${esc(t("confirmTitle"))}</h2>
    <p class="muted">${esc(t("confirmIntro"))}</p>
    <ol class="tips">
      <li>${esc(t("confirm1"))}</li>
      <li>${esc(t("confirm2"))}</li>
      <li>${esc(t("confirm3"))}</li>
    </ol>
    ${autostart}
    ${busy}
    <div class="actions">
      <button class="btn" data-action="back" ${state.installing ? "disabled" : ""}>${esc(t("back"))}</button>
      <button class="btn primary" data-action="install" ${state.installing ? "disabled" : ""}>${esc(t("install"))}</button>
    </div>`;
}

function dashboard() {
  const s = state.status;
  return `
    ${banner()}
    <div class="grid">
      <div class="stack">
        <div class="card">
          <h2>${esc(t("nowOnScreen"))}</h2>
          <img class="preview" style="margin-top:0" src="${previewUrl(s.lang)}" alt="">
        </div>
      </div>
      <div class="stack">
        ${usageCard()}
        ${displayCard()}
        ${preferencesCard()}
        ${activityCard()}
        <p class="muted small">${esc(t("bookmark", { url: location.origin }))}</p>
      </div>
    </div>`;
}

function banner() {
  const d = state.status.display;
  const map = {
    online: ["ok", "stateOnline", t("stateOnlineDetail", { time: time(d.pushed_at) })],
    connecting: ["", "stateConnecting", t("stateConnectingDetail")],
    offline: ["warn", "stateOffline", t("stateOfflineDetail")],
    unsupported: ["danger", "stateUnsupported", t("stateUnsupportedDetail")],
  };
  const [cls, title, detail] = map[d.state] || map.connecting;
  return `
    <div class="banner">
      <span class="dot ${cls}"></span>
      <div><strong>${esc(t(title))}</strong><span class="muted small">${esc(detail)}</span></div>
    </div>`;
}

function meter(label, win) {
  const pct = win ? win.percent : 0;
  return `
    <div class="meter">
      <div class="head"><span>${esc(label)}</span><span class="pct">${Math.round(pct)}%</span></div>
      <div class="bar"><span class="${level(pct)}" style="width:${Math.min(100, Math.max(0, pct))}%"></span></div>
      <div class="muted small">${esc(resetText(win))}</div>
    </div>`;
}

function usageCard() {
  const u = state.status.usage;
  let body;
  if (u.problem === "login") {
    body = `<div class="note danger">${th("loginProblem", { cmd: "<code>claude</code>" })}</div>`;
  } else if (!u.session && !u.weekly) {
    body = `<p class="muted">${esc(u.problem === "usage" ? t("usageProblem") : t("waiting"))}</p>`;
  } else {
    const split = u.breakdown.length
      ? `<p class="muted small" style="margin:14px 0 0">${esc(t("weekSplit"))}: ${
        u.breakdown.map(([name, pct]) => `${esc(name)} ${pct}%`).join(" · ")}</p>` : "";
    const stale = u.stale ? `<div class="note warn">${esc(t("stale", { time: time(u.fetched_at) }))}</div>` : "";
    body = meter(t("session"), u.session) + meter(t("weekly"), u.weekly) + split + stale;
  }
  return `<div class="card"><h2>${esc(t("usage"))}</h2>${body}</div>`;
}

function displayCard() {
  const s = state.status;
  return `
    <div class="card">
      <h2>${esc(t("display"))}</h2>
      <dl class="facts">
        <dt>${esc(t("address"))}</dt><dd>${esc(s.host)}</dd>
        <dt>${esc(t("firmware"))}</dt><dd>${esc(s.display.firmware || "—")}</dd>
        <dt>${esc(t("lastUpdate"))}</dt><dd>${esc(s.display.pushed_at ? time(s.display.pushed_at) : t("never"))}</dd>
      </dl>
      <div class="row" style="margin-top:16px">
        <button class="btn" data-action="change-display">${esc(t("changeDisplay"))}</button>
        <button class="btn danger ${state.confirmHandBack ? "confirm" : ""}" data-action="hand-back"
          title="${esc(t("handBackHint"))}">${esc(state.confirmHandBack ? t("handBackConfirm") : t("handBack"))}</button>
      </div>
      <p class="muted small" style="margin:8px 0 0">${esc(t("handBackHint"))}</p>
    </div>`;
}

function preferencesCard() {
  const s = state.status;
  const langs = s.languages.map((code) => `
    <option value="${esc(code)}" ${code === s.lang ? "selected" : ""}>${esc(t("langName")[code] || code)}</option>`).join("");
  const auto = s.autostart;
  const autoHint = !auto.supported ? t("autostartUnsupported") : auto.enabled ? t("autostartOn") : t("autostartOff");
  return `
    <div class="card">
      <h2>${esc(t("preferences"))}</h2>
      <div class="setting">
        <label for="panel-lang"><strong>${esc(t("panelLang"))}</strong></label>
        <select id="panel-lang" data-change="settings-lang">${langs}</select>
      </div>
      <div class="setting">
        <div><p><strong>${esc(t("showIp"))}</strong></p><p class="muted small">${esc(t("showIpHint"))}</p></div>
        <label class="switch"><input type="checkbox" role="switch" aria-label="${esc(t("showIp"))}"
          data-change="show-ip" ${s.show_ip ? "checked" : ""}><span></span></label>
      </div>
      <div class="setting">
        <div><p><strong>${esc(t("autostart"))}</strong></p><p class="muted small">${esc(autoHint)}</p></div>
        <label class="switch"><input type="checkbox" role="switch" aria-label="${esc(t("autostart"))}"
          data-change="autostart" ${auto.enabled ? "checked" : ""} ${auto.supported ? "" : "disabled"}><span></span></label>
      </div>
    </div>`;
}

function activityCard() {
  const items = state.status.activity.slice(0, 12).map((a) => `
    <li><time>${esc(time(a.time))}</time><span class="msg ${esc(a.level)}">${esc(a.message)}</span></li>`).join("");
  return `
    <div class="card">
      <h2>${esc(t("activity"))}</h2>
      ${items ? `<ul class="activity">${items}</ul>` : `<p class="muted small">${esc(t("noActivity"))}</p>`}
    </div>`;
}

// ------------------------------------------------------------------ actions

async function testHost(host) {
  state.host = host.trim();
  if (!state.host) return;
  state.testing = true;
  state.test = null;
  render();
  try {
    state.test = await api("/api/test", { host: state.host });
    if (state.test.ok) state.host = state.test.host;
  } catch (err) {
    toast(t("error", { msg: err.message }), true);
  } finally {
    state.testing = false;
    render();
  }
}

const actions = {
  recheck: () => refresh(),
  back: () => { state.step = Math.max(1, state.step - 1); render(); },
  next: () => { state.step = Math.min(STEPS, state.step + 1); render(); },
  cancel: () => { state.view = "dashboard"; render(); },

  scan: async () => {
    state.scanning = true;
    state.scan = null;
    render();
    try {
      state.scan = (await api("/api/scan", {})).hosts;
    } catch (err) {
      toast(t("error", { msg: err.message }), true);
    } finally {
      state.scanning = false;
      render();
    }
  },

  "use-host": (el) => testHost(el.dataset.host),

  install: async () => {
    state.installing = true;
    render();
    try {
      await api("/api/setup", { host: state.host, lang: state.panelLang });
      if (state.status.autostart.supported) {
        await api("/api/autostart", { enabled: state.autostart }).catch((err) => {
          toast(t("error", { msg: err.message }), true);
        });
      }
      state.view = "dashboard";
      toast(t("installed"));
    } catch (err) {
      toast(t("error", { msg: err.message }), true);
    } finally {
      state.installing = false;
      await refresh();
      render();
    }
  },

  "change-display": () => {
    Object.assign(state, { view: "wizard", step: 2, test: null, scan: null, host: "", panelLang: state.status.lang });
    render();
  },

  "hand-back": async () => {
    if (!state.confirmHandBack) {
      state.confirmHandBack = true;
      render();
      setTimeout(() => { state.confirmHandBack = false; render(); }, 5000);
      return;
    }
    state.confirmHandBack = false;
    try {
      await api("/api/restore", {});
      toast(t("handedBack"));
      Object.assign(state, { view: "wizard", step: 1, test: null, scan: null, host: "" });
    } catch (err) {
      toast(t("error", { msg: err.message }), true);
    }
    await refresh();
    render();
  },
};

async function saveSettings(settings) {
  try {
    await api("/api/settings", settings);
    toast(t("saved"));
  } catch (err) {
    toast(t("error", { msg: err.message }), true);
  }
  await refresh();
  // Show the change on the preview now instead of at the next minute.
  const img = app.querySelector("img.preview");
  if (img) img.src = `${previewUrl(state.status.lang)}&r=${Date.now()}`;
}

const changes = {
  "panel-lang": (el) => { state.panelLang = el.value; render(); },
  "wizard-autostart": (el) => { state.autostart = el.checked; },
  "settings-lang": (el) => saveSettings({ lang: el.value }),
  "show-ip": (el) => saveSettings({ show_ip: el.checked }),
  autostart: async (el) => {
    try {
      await api("/api/autostart", { enabled: el.checked });
      toast(t("saved"));
    } catch (err) {
      toast(t("error", { msg: err.message }), true);
    }
    refresh();
  },
};

app.addEventListener("click", (e) => {
  const el = e.target.closest("[data-action]");
  if (el && !el.disabled && actions[el.dataset.action]) actions[el.dataset.action](el);
});

app.addEventListener("change", (e) => {
  const handler = changes[e.target.dataset.change];
  if (handler) handler(e.target);
});

app.addEventListener("input", (e) => {
  if (e.target.id === "host") state.host = e.target.value;
});

app.addEventListener("submit", (e) => {
  if (e.target.dataset.form === "test") {
    e.preventDefault();
    testHost(new FormData(e.target).get("host") || "");
  }
});

document.querySelectorAll("[data-ui-lang]").forEach((button) => {
  button.addEventListener("click", () => {
    uiLang = button.dataset.uiLang;
    try { localStorage.setItem("ui-lang", uiLang); } catch (_) { /* not persisted */ }
    render();
  });
});

refresh();
setInterval(refresh, 10000);
