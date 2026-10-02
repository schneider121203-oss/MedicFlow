const API_BASE = window.MEDIFLOW_API_BASE || window.location.origin;

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[char]);
}

function getToken() { return localStorage.getItem("mf_token"); }
function getMedico() { return JSON.parse(localStorage.getItem("mf_medico") || "null"); }
function setSession(token, medico) {
  localStorage.setItem("mf_token", token);
  localStorage.setItem("mf_medico", JSON.stringify(medico));
}
function clearSession() {
  localStorage.removeItem("mf_token");
  localStorage.removeItem("mf_medico");
}
function requireAuth() {
  if (!getToken()) { window.location.href = "/static/index.html"; }
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body instanceof FormData) delete headers["Content-Type"];
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) { clearSession(); window.location.href = "/static/index.html"; return; }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error desconocido" }));
    throw new Error(err.detail || "Error en la solicitud");
  }
  if (res.headers.get("content-type")?.includes("application/pdf")) return res.blob();
  if (res.headers.get("content-length") === "0") return null;
  return res.json();
}

// Toast notifications
function toast(msg, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }
  const t = document.createElement("div");
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  t.className = `toast toast-${type}`;
  const icon = document.createElement("span");
  icon.textContent = icons[type] || icons.info;
  const message = document.createElement("span");
  message.textContent = msg;
  t.append(icon, message);
  container.appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateX(20px)"; t.style.transition = "all 0.3s"; setTimeout(() => t.remove(), 300); }, 3500);
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" });
}
function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
function estadoBadge(estado) {
  const map = {
    programada: ["badge-cyan", "Programada"],
    en_consulta: ["badge-warning", "En consulta"],
    completada: ["badge-success", "Completada"],
    cancelada: ["badge-danger", "Cancelada"],
  };
  const [cls, label] = map[estado] || ["badge-muted", estado];
  return `<span class="badge ${cls}">${escapeHTML(label)}</span>`;
}

async function openAuthenticatedPdf(historiaId) {
  const blob = await apiFetch(`/api/consultas/${historiaId}/pdf`);
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

// Render sidebar activo
function setActiveNav(page) {
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.dataset.page === page);
  });
}

// Render medico en sidebar
function renderSidebarMedico() {
  const medico = getMedico();
  if (!medico) return;
  const el = document.getElementById("sidebar-medico");
  if (!el) return;
  const initials = medico.nombre.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  el.innerHTML = `
    <div class="medico-avatar">${escapeHTML(initials)}</div>
    <div class="medico-info">
      <div class="name">Dr. ${escapeHTML(medico.nombre.split(" ")[0])}</div>
      <div class="role">${escapeHTML(medico.especialidad)}</div>
    </div>
  `;
}
