/* Platform-X — Admin Panel JS */

window.PX = window.PX || {};

PX.getAdminToken = function () {
  try { return localStorage.getItem("px_admin_token"); } catch (e) { return null; }
};

PX.clearAdminToken = function () {
  try { localStorage.removeItem("px_admin_token"); } catch (e) {}
};

PX.adminHeaders = function () {
  var h = { "Content-Type": "application/json" };
  var t = PX.getAdminToken();
  if (t) h["Authorization"] = "Bearer " + t;
  return h;
};

PX.requireAdmin = function () {
  if (!PX.getAdminToken()) {
    window.location.href = "/admin/login";
    return false;
  }
  return true;
};

PX.adminFetch = async function (path) {
  var res = await fetch(path, { headers: PX.adminHeaders() });
  if (res.status === 401 || res.status === 403) {
    PX.clearAdminToken();
    window.location.href = "/admin/login";
    return null;
  }
  return res;
};

/* ---------- Dashboard ---------- */

PX.initAdminDashboard = async function () {
  if (!PX.requireAdmin()) return;

  // Sidebar footer: logout
  var logoutBtn = document.getElementById("admin-logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", function () {
      PX.clearAdminToken();
      window.location.href = "/admin/login";
    });
  }

  // Load admin info
  try {
    var res = await PX.adminFetch("/platform/me");
    if (res && res.ok) {
      var me = await res.json();
      var el = document.getElementById("admin-user");
      if (el) el.textContent = me.name || me.email;
    }
  } catch (e) {}

  // Load analytics
  try {
    var res2 = await PX.adminFetch("/platform/analytics");
    if (res2 && res2.ok) {
      var data = await res2.json();
      document.getElementById("stat-tenants").textContent = data.tenants.total;
      document.getElementById("stat-active").textContent = data.tenants.active;
      document.getElementById("stat-users").textContent = data.users.total;
      document.getElementById("stat-bookings").textContent = data.bookings.total;
    }
  } catch (e) {}
};

/* Sidebar logout for any page */
document.addEventListener("DOMContentLoaded", function () {
  var logoutBtn = document.getElementById("admin-logout");
  if (logoutBtn && !logoutBtn.dataset.bound) {
    logoutBtn.dataset.bound = "1";
    logoutBtn.addEventListener("click", function () {
      PX.clearAdminToken();
      window.location.href = "/admin/login";
    });
  }
});
