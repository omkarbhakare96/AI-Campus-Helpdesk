/* api.js — shared fetch wrapper, auth storage, and small UI helpers */

const API = {
  base: "",

  getToken() {
    return localStorage.getItem("ch_token");
  },
  setToken(token) {
    localStorage.setItem("ch_token", token);
  },
  clearToken() {
    localStorage.removeItem("ch_token");
    localStorage.removeItem("ch_user");
  },
  getUser() {
    const raw = localStorage.getItem("ch_user");
    return raw ? JSON.parse(raw) : null;
  },
  setUser(user) {
    localStorage.setItem("ch_user", JSON.stringify(user));
  },
  isLoggedIn() {
    return !!this.getToken();
  },

  async request(path, { method = "GET", body = null, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth && this.getToken()) {
      headers["Authorization"] = "Bearer " + this.getToken();
    }
    let res;
    try {
      res = await fetch(this.base + path, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null,
      });
    } catch (err) {
      throw new Error("Network error — could not reach the server. Please check your connection.");
    }

    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }

    if (!res.ok) {
      let message = "Something went wrong. Please try again.";
      if (data) {
        if (Array.isArray(data.detail)) {
          message = data.detail.join(" | ");
        } else if (typeof data.detail === "string") {
          message = data.detail;
        }
      }
      if (res.status === 401) {
        API.clearToken();
      }
      const err = new Error(message);
      err.status = res.status;
      throw err;
    }
    return data;
  },

  get(path, opts = {}) { return this.request(path, { ...opts, method: "GET" }); },
  post(path, body, opts = {}) { return this.request(path, { ...opts, method: "POST", body }); },
  put(path, body, opts = {}) { return this.request(path, { ...opts, method: "PUT", body }); },
};

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) { alert(message); return; }
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4200);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) +
    " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function priorityBadgeClass(p) {
  return {
    Low: "badge-priority-low",
    Medium: "badge-priority-medium",
    High: "badge-priority-high",
    Critical: "badge-priority-critical",
  }[p] || "badge-outline";
}

function statusBadgeClass(s) {
  return {
    "Pending": "badge-status-pending",
    "In Progress": "badge-status-in-progress",
    "Resolved": "badge-status-resolved",
    "Rejected": "badge-status-rejected",
  }[s] || "badge-outline";
}

function sentimentBadgeClass(s) {
  return {
    Positive: "badge-sentiment-positive",
    Neutral: "badge-sentiment-neutral",
    Negative: "badge-sentiment-negative",
  }[s] || "badge-outline";
}

function requireAuth(role = null) {
  if (!API.isLoggedIn()) {
    window.location.href = "/login";
    return false;
  }
  const user = API.getUser();
  if (role && user && user.role !== role) {
    window.location.href = user.role === "admin" ? "/admin" : "/dashboard";
    return false;
  }
  return true;
}
