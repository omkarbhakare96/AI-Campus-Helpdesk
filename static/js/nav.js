/* nav.js — renders nav links based on auth state and role */

function renderNav() {
  const nav = document.getElementById("navLinks");
  if (!nav) return;
  const user = API.getUser();

  let html = `<a href="/">Home</a>`;

  if (!user) {
    html += `<a href="/login">Login</a>`;
    html += `<a href="/register" class="nav-cta">Register</a>`;
  } else if (user.role === "admin") {
    html += `<a href="/admin">Dashboard</a>`;
    html += `<a href="/admin/analytics">Analytics</a>`;
    html += `<span style="color:#cdd3de;padding:8px 6px;font-size:0.85rem;">Hi, ${escapeHtml(user.name)}</span>`;
    html += `<button id="logoutBtn">Logout</button>`;
  } else {
    html += `<a href="/dashboard">Dashboard</a>`;
    html += `<a href="/submit-complaint">Submit Complaint</a>`;
    html += `<a href="/my-complaints">My Complaints</a>`;
    html += `<span style="color:#cdd3de;padding:8px 6px;font-size:0.85rem;">Hi, ${escapeHtml(user.name)}</span>`;
    html += `<button id="logoutBtn">Logout</button>`;
  }

  nav.innerHTML = html;

  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      API.clearToken();
      showToast("Logged out successfully.", "success");
      setTimeout(() => (window.location.href = "/"), 400);
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderNav();
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (toggle && links) {
    toggle.addEventListener("click", () => links.classList.toggle("open"));
  }
});
