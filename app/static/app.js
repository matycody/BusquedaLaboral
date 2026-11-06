"use strict";

const $ = (id) => document.getElementById(id);
const state = { cfg: null, jobs: [], tab: "activas", sort: "score", openId: null, cv: "" };

const TABS = [
  ["activas", "Activas"],
  ["interesa", "Me interesa"],
  ["aplicada", "Aplicadas"],
  ["descartada", "Descartadas"],
];

/* ---------- utilidades ---------- */
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, method = "GET", body) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error("El servidor respondió " + res.status);
  return res.json();
}

let toastTimer;
function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 4000);
}

function ago(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return "Hoy";
  if (days === 1) return "Ayer";
  if (days < 30) return `Hace ${days} días`;
  return d.toLocaleDateString("es-AR");
}

const cvLabel = (k) => state.cfg?.profiles?.[k]?.label || k;
const debounce = (fn, ms = 250) => {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
};

/* ---------- empresas de interés ---------- */
const isMyCompany = (name) => {
  const n = norm(name || "");
  return !!n && (state.cfg?.empresas || []).some((e) => norm(e.name) && n.includes(norm(e.name)));
};
const norm = (t) => String(t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

function renderCompanies() {
  const list = state.cfg.empresas || [];
  $("companies").innerHTML = list.length
    ? list
        .map((e) => {
          const main = e.url || "https://www.google.com/search?q=" + encodeURIComponent(e.name + " trabajá con nosotros");
          const li = "https://www.linkedin.com/jobs/search/?keywords=" + encodeURIComponent(e.name);
          return `<li class="company"><a href="${esc(main)}" target="_blank" rel="noopener noreferrer" title="${e.url ? "Página de empleos" : "Buscar su página de empleos"}">${esc(e.name)}</a>
            <a class="alt" href="${esc(li)}" target="_blank" rel="noopener noreferrer">LinkedIn</a></li>`;
        })
        .join("")
    : `<li class="hint">Agregalas en Configuración.</li>`;
}

/* ---------- carga y filtros ---------- */
async function loadJobs() {
  const p = new URLSearchParams({
    q: $("fQ").value.trim(),
    location: $("fLoc").value.trim(),
    cv: state.cv,
    min_score: $("fMin").value,
  });
  try {
    state.jobs = await api("/api/jobs?" + p);
  } catch (e) {
    toast("No se pudieron cargar las ofertas. ¿Sigue corriendo run.py?");
    state.jobs = [];
  }
  render();
}

function filtersActive() {
  return !!($("fOnlyEmp").checked || $("fQ").value.trim() || $("fLoc").value.trim() || state.cv || Number($("fMin").value));
}

function renderCvFilter() {
  const opts = [["", "Todos", ""], ...Object.entries(state.cfg.profiles).map(([k, p]) => [k, p.label, k])];
  $("fCv").innerHTML = opts
    .map(
      ([v, label, dot]) => `<label class="seg-option">
        <input type="radio" name="cv" value="${esc(v)}" ${state.cv === v ? "checked" : ""}>
        ${dot ? `<span class="dot dot-${esc(dot)}"></span>` : ""}${esc(label)}</label>`
    )
    .join("");
}

/* ---------- render ---------- */
function inTab(j, tab) {
  return tab === "activas" ? j.status !== "descartada" && j.status !== "aplicada" : j.status === tab;
}

function render() {
  // pestañas con contador
  $("tabs").innerHTML = TABS.map(([k, label]) => {
    const n = state.jobs.filter((j) => inTab(j, k)).length;
    return `<button class="tab" role="tab" data-tab="${k}" aria-selected="${state.tab === k}">${label}<span class="tab-count">${n}</span></button>`;
  }).join("");

  const onlyEmp = $("fOnlyEmp").checked;
  const rows = state.jobs.filter((j) => inTab(j, state.tab) && (!onlyEmp || isMyCompany(j.company)));
  rows.sort((a, b) =>
    state.sort === "recent"
      ? String(b.posted || b.created).localeCompare(String(a.posted || a.created))
      : b.score - a.score
  );

  $("count").textContent = rows.length === 1 ? "1 oferta" : `${rows.length} ofertas`;

  if (!rows.length) {
    $("list").innerHTML = `<li>${emptyState()}</li>`;
    return;
  }
  $("list").innerHTML = rows.map(jobHtml).join("");
}

function emptyState() {
  if (filtersActive()) {
    return `<div class="empty"><h3>Ninguna oferta coincide</h3>
      <p>Probá con menos filtros o bajá el puntaje mínimo.</p>
      <div class="row"><button class="btn" data-act="clear">Limpiar filtros</button></div></div>`;
  }
  if (state.tab === "activas" && !state.jobs.length) {
    return `<div class="empty"><h3>Todavía no hay ofertas</h3>
      <p>Cargá las de ejemplo para ver cómo funciona, agregá un aviso a mano o configurá fuentes RSS para buscar solo.</p>
      <div class="row">
        <button class="btn btn-primary" data-act="demo">Cargar ofertas de ejemplo</button>
        <button class="btn" data-act="add">Agregar oferta</button>
        <button class="btn" data-act="config">Configurar fuentes</button>
      </div></div>`;
  }
  const msg = {
    activas: "No quedan ofertas por revisar.",
    interesa: "Marcá una oferta con Me interesa y aparece acá.",
    aplicada: "Cuando marques una oferta como Aplicada la vas a ver acá.",
    descartada: "No descartaste ninguna oferta.",
  }[state.tab];
  return `<div class="empty"><h3>${esc(msg)}</h3></div>`;
}

function meter(score) {
  const on = Math.round(score / 10);
  const tier = score >= 70 ? "high" : score >= 40 ? "mid" : "low";
  return `<div class="meter ${tier}" aria-hidden="true">${Array.from({ length: 10 }, (_, i) => `<i class="${i < on ? "on" : ""}"></i>`).join("")}</div>`;
}

const STATUS_LABEL = { interesa: "Me interesa", aplicada: "Aplicada", descartada: "Descartada" };

function jobHtml(j) {
  const open = state.openId === j.id;
  const meta = [j.company || "Empresa no indicada", j.location || "Lugar no indicado", ago(j.posted)].filter(Boolean);
  return `<li class="job ${open ? "open" : ""}" data-id="${j.id}" data-cv="${esc(j.cv)}" data-status="${esc(j.status)}">
    <button class="job-head" data-act="toggle" aria-expanded="${open}" aria-controls="body-${j.id}">
      <div class="score" role="img" aria-label="Puntaje ${j.score} de 100">
        <div class="score-num">${j.score}<small>/100</small></div>${meter(j.score)}
      </div>
      <div class="job-main">
        <h3 class="job-title">${esc(j.title)}</h3>
        <div class="job-meta">${meta.map((m) => `<span>${esc(m)}</span>`).join("")}</div>
      </div>
      <span class="chip chip-cv chip-${esc(j.cv)}">${esc(cvLabel(j.cv))}</span>
      <span class="job-flags">
        ${STATUS_LABEL[j.status] ? `<span class="chip chip-${esc(j.status)}">${STATUS_LABEL[j.status]}</span>` : ""}
        ${isMyCompany(j.company) ? `<span class="chip chip-empresa">Mi empresa</span>` : ""}
        ${j.sources.length > 1 ? `<span class="chip">${j.sources.length} portales</span>` : ""}
        <span class="chevron" aria-hidden="true">&#9656;</span>
      </span>
    </button>
    ${open ? detailHtml(j) : ""}
  </li>`;
}

function detailHtml(j) {
  const best = j.cv;
  const bars = Object.entries(j.cv_scores)
    .map(
      ([k, v]) => `<div class="cv-bar ${k === best ? "best" : ""}">
        <span>${esc(cvLabel(k))}</span>
        <div class="cv-bar-track"><div class="cv-bar-fill" style="width:${v}%"></div></div>
        <span>${v}</span></div>`
    )
    .join("");
  const sources = j.sources
    .map((s) => `<li>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.name)}</a>` : esc(s.name)}</li>`)
    .join("");
  const btn = (status, label) =>
    j.status === status
      ? `<button class="btn btn-sm" data-act="status" data-status="nueva">Quitar "${label}"</button>`
      : `<button class="btn btn-sm" data-act="status" data-status="${status}">${label}</button>`;
  return `<div class="job-body" id="body-${j.id}">
    ${j.description ? `<p class="job-desc">${esc(j.description)}</p>` : `<p class="hint">Esta oferta no tiene descripción.</p>`}
    <div class="detail-grid">
      <div class="detail-block"><h4>Qué CV conviene usar</h4><div class="cv-bars">${bars}</div></div>
      <div class="detail-block"><h4>Dónde está publicada</h4><ul class="sources">${sources}</ul></div>
    </div>
    <div class="detail-block"><h4>Mis notas</h4>
      <textarea class="input" data-notes rows="2" placeholder="Contacto, fecha de entrevista, lo que quieras recordar">${esc(j.notes)}</textarea></div>
    <div class="job-actions">${btn("interesa", "Me interesa")}${btn("aplicada", "Marcar como aplicada")}${btn("descartada", "Descartar")}</div>
  </div>`;
}

/* ---------- acciones ---------- */
async function setStatus(id, status) {
  await api("/api/jobs/" + id, "POST", { status });
  const j = state.jobs.find((x) => x.id === id);
  if (j) j.status = status;
  if (status === "descartada" || status === "aplicada") state.openId = null;
  render();
}

async function runBusy(btn, busyText, fn) {
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = busyText;
  try {
    await fn();
  } catch (e) {
    toast("Algo falló: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = label;
  }
}

async function doSearch() {
  await runBusy($("btnSearch"), "Buscando…", async () => {
    const r = await api("/api/search", "POST");
    if (r.aviso) {
      toast(r.aviso);
    } else {
      const vacias = (r.empresas || []).filter((x) => !x.encontradas);
      const fallas = (r.portales || []).filter((x) => x.nota);
      const errs = r.errores?.length ? ` ${r.errores.length} feed(s) fallaron.` : "";
      const emp = vacias.length ? ` Sin resultados legibles en: ${vacias.map((x) => x.empresa).join(", ")}; abrilas desde el panel Mis empresas.` : "";
      const por = fallas.length ? ` ${fallas[0].portal} falló en ${fallas.length} búsqueda(s): ${fallas[0].nota}` : "";
      toast(`${r.agregadas} ofertas nuevas.${errs}${por}${emp}`);
      console.info("Revisión", { empresas: r.empresas, portales: r.portales, errores: r.errores });
    }
    await loadJobs();
  });
}

async function loadDemo() {
  const r = await api("/api/demo", "POST");
  toast(`${r.agregadas} ofertas de ejemplo cargadas.`);
  await loadJobs();
}

/* ---------- diálogos ---------- */
function openDialog(dlg) {
  dlg.showModal();
}

function linesToObj(text) {
  const out = {};
  text.split("\n").forEach((line) => {
    const i = line.lastIndexOf(":");
    const key = (i === -1 ? line : line.slice(0, i)).trim();
    if (!key) return;
    const n = i === -1 ? NaN : parseFloat(line.slice(i + 1));
    out[key] = Number.isNaN(n) ? 5 : n;
  });
  return out;
}
const objToLines = (o) => Object.entries(o).map(([k, v]) => `${k}: ${v}`).join("\n");
const textToList = (t) => t.split("\n").map((s) => s.trim()).filter(Boolean);

function openConfig() {
  const c = state.cfg;
  $("cLocation").value = c.location || "";
  $("cLocs").value = (c.locations_ok || []).join("\n");
  $("cRss").value = (c.rss_feeds || []).join("\n");
  const ct = (c.portales || {}).computrabajo || {};
  $("cCtOn").checked = !!ct.enabled;
  $("cCtRegion").value = ct.region || "buenos-aires-gba";
  $("cCtPages").value = ct.max_pages || 2;
  $("cCtQ").value = (ct.queries || []).join("\n");
  const bu = (c.portales || {}).bumeran || {};
  $("cBuOn").checked = !!bu.enabled;
  $("cBuPages").value = bu.max_pages || 2;
  $("cBuZonas").value = (bu.zonas || []).join("\n");
  $("cBuQ").value = (bu.queries || []).join("\n");
  $("cEmp").value = (c.empresas || []).map((e) => (e.url ? `${e.name} | ${e.url}` : e.name)).join("\n");
  $("cPen").value = objToLines(c.penalize || {});
  $("cProfiles").innerHTML = Object.entries(c.profiles)
    .map(
      ([k, p]) => `<div class="field">
        <label for="kw-${esc(k)}"><span class="dot dot-${esc(k)}" style="display:inline-block;margin-right:6px"></span>${esc(p.label)}</label>
        <textarea class="input" id="kw-${esc(k)}" data-profile="${esc(k)}" rows="7">${esc(objToLines(p.keywords))}</textarea></div>`
    )
    .join("");
  openDialog($("dConfig"));
}

async function saveConfig(ev) {
  ev.preventDefault();
  const cfg = structuredClone(state.cfg);
  cfg.location = $("cLocation").value.trim();
  cfg.locations_ok = textToList($("cLocs").value);
  cfg.rss_feeds = textToList($("cRss").value);
  cfg.portales = {
    ...(cfg.portales || {}),
    computrabajo: {
      enabled: $("cCtOn").checked,
      region: $("cCtRegion").value.trim() || "buenos-aires-gba",
      max_pages: Math.min(5, Math.max(1, Number($("cCtPages").value) || 2)),
      queries: textToList($("cCtQ").value),
    },
    bumeran: {
      enabled: $("cBuOn").checked,
      max_pages: Math.min(5, Math.max(1, Number($("cBuPages").value) || 2)),
      zonas: textToList($("cBuZonas").value),
      queries: textToList($("cBuQ").value),
    },
  };
  cfg.empresas = textToList($("cEmp").value).map((l) => {
    const [name, ...rest] = l.split("|");
    return { name: name.trim(), url: rest.join("|").trim() };
  }).filter((e) => e.name);
  cfg.penalize = linesToObj($("cPen").value);
  document.querySelectorAll("[data-profile]").forEach((ta) => {
    cfg.profiles[ta.dataset.profile].keywords = linesToObj(ta.value);
  });
  try {
    await api("/api/config", "POST", cfg);
    state.cfg = cfg;
    $("dConfig").close();
    toast("Configuración guardada. Puntajes recalculados.");
    renderCompanies();
    await loadJobs();
  } catch (e) {
    toast("No se pudo guardar: " + e.message);
  }
}

async function saveOffer(ev) {
  ev.preventDefault();
  const body = {
    title: $("aTitle").value.trim(),
    company: $("aCompany").value.trim(),
    location: $("aLocation").value.trim(),
    description: $("aDesc").value.trim(),
    posted: new Date().toISOString(),
    source: "Manual",
    url: $("aUrl").value.trim(),
  };
  if (!body.title) return;
  try {
    const r = await api("/api/jobs", "POST", body);
    $("dAdd").close();
    toast(r.agregadas ? "Oferta guardada." : "Esa oferta ya estaba cargada.");
    await loadJobs();
  } catch (e) {
    toast("No se pudo guardar: " + e.message);
  }
}

function clearFilters() {
  $("fQ").value = "";
  $("fLoc").value = "";
  $("fMin").value = 0;
  $("fOnlyEmp").checked = false;
  $("fMinOut").textContent = "0";
  state.cv = "";
  renderCvFilter();
  loadJobs();
}

/* ---------- eventos ---------- */
function bind() {
  const reload = debounce(loadJobs);
  $("fQ").addEventListener("input", reload);
  $("fLoc").addEventListener("input", reload);
  $("fMin").addEventListener("input", () => {
    $("fMinOut").textContent = $("fMin").value;
    reload();
  });
  $("fCv").addEventListener("change", (e) => {
    state.cv = e.target.value;
    loadJobs();
  });
  $("fOnlyEmp").addEventListener("change", render);
  $("fSort").addEventListener("change", (e) => {
    state.sort = e.target.value;
    render();
  });
  $("btnClear").addEventListener("click", clearFilters);
  const fp = $("filters");
  if (matchMedia("(max-width: 900px)").matches) fp.classList.add("collapsed");
  $("btnFilters").addEventListener("click", () => {
    const hidden = fp.classList.toggle("collapsed");
    $("btnFilters").setAttribute("aria-expanded", String(!hidden));
  });
  $("btnSearch").addEventListener("click", doSearch);
  $("btnAdd").addEventListener("click", () => {
    $("formAdd").reset();
    openDialog($("dAdd"));
  });
  $("btnConfig").addEventListener("click", openConfig);
  $("formAdd").addEventListener("submit", saveOffer);
  $("formConfig").addEventListener("submit", saveConfig);

  document.querySelectorAll("[data-close]").forEach((b) =>
    b.addEventListener("click", () => b.closest("dialog").close())
  );

  $("btnDemo").addEventListener("click", async () => {
    await loadDemo();
  });
  $("btnRecalc").addEventListener("click", async () => {
    const r = await api("/api/recalc", "POST");
    toast(`${r.recalculadas} ofertas recalculadas.`);
    await loadJobs();
  });
  $("btnWipe").addEventListener("click", async () => {
    if (!confirm("¿Borrar todas las ofertas guardadas? Esto no se puede deshacer.")) return;
    await api("/api/clear", "POST");
    $("dConfig").close();
    toast("Se borraron todas las ofertas.");
    await loadJobs();
  });

  $("tabs").addEventListener("click", (e) => {
    const t = e.target.closest("[data-tab]");
    if (!t) return;
    state.tab = t.dataset.tab;
    state.openId = null;
    render();
  });

  $("list").addEventListener("click", (e) => {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const li = el.closest(".job");
    const id = li ? Number(li.dataset.id) : null;
    switch (el.dataset.act) {
      case "toggle":
        state.openId = state.openId === id ? null : id;
        render();
        break;
      case "status":
        setStatus(id, el.dataset.status);
        break;
      case "demo":
        loadDemo();
        break;
      case "add":
        $("btnAdd").click();
        break;
      case "config":
        openConfig();
        break;
      case "clear":
        clearFilters();
        break;
    }
  });

  // las notas se guardan al salir del campo
  $("list").addEventListener("focusout", async (e) => {
    if (!e.target.matches("[data-notes]")) return;
    const id = Number(e.target.closest(".job").dataset.id);
    const j = state.jobs.find((x) => x.id === id);
    if (j && j.notes !== e.target.value) {
      j.notes = e.target.value;
      try {
        await api("/api/jobs/" + id, "POST", { notes: j.notes });
        toast("Nota guardada.");
      } catch (err) {
        toast("No se pudo guardar la nota.");
      }
    }
  });
}

async function init() {
  try {
    state.cfg = await api("/api/config");
  } catch (e) {
    toast("No se pudo leer la configuración. ¿Sigue corriendo run.py?");
    return;
  }
  renderCvFilter();
  renderCompanies();
  bind();
  loadJobs();
}
init();
