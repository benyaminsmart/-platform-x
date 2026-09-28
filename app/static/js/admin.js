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

  // Recent tenants
  try {
    var res3 = await PX.adminFetch("/platform/tenants");
    if (res3 && res3.ok) {
      var tenants = await res3.json();
      var recent = tenants.slice(0, 5);
      var html = "";
      if (!recent.length) {
        html = '<p style="color: var(--adm-muted);">No tenants yet.</p>';
      } else {
        recent.forEach(function (t) {
          var badgeCls = t.status === "active" ? "admin-badge-success" : "admin-badge-warning";
          html += '<div class="admin-list-item">' +
            '<div class="admin-list-item-main">' +
            '<div class="admin-list-item-title">' + PX.esc(t.name) + '</div>' +
            '<div class="admin-list-item-sub">' + PX.esc(t.slug) + " · " + PX.esc(t.tier) + '</div></div>' +
            '<div class="admin-list-item-side"><span class="admin-badge ' + badgeCls + '">' + PX.esc(t.status) + '</span></div>' +
            '</div>';
        });
      }
      document.getElementById("recent-tenants").innerHTML = html;
    }
  } catch (e) {}

  // Recent applications
  try {
    var res4 = await PX.adminFetch("/platform/applications?limit=5");
    if (res4 && res4.ok) {
      var apps = await res4.json();
      var items = apps.items || [];
      var html = "";
      if (!items.length) {
        html = '<p style="color: var(--adm-muted);">No applications yet.</p>';
      } else {
        items.forEach(function (a) {
          html += '<div class="admin-list-item">' +
            '<div class="admin-list-item-main">' +
            '<div class="admin-list-item-title">' + PX.esc(a.business_name) + '</div>' +
            '<div class="admin-list-item-sub">' + PX.esc(a.tenant_type) + " · " + PX.esc(a.city) + '</div></div>' +
            '<div class="admin-list-item-side"><span class="admin-badge admin-badge-info">' + PX.esc(a.status) + '</span></div>' +
            '</div>';
        });
      }
      document.getElementById("recent-applications").innerHTML = html;
    }
  } catch (e) {}

  // Recent audit
  try {
    var res5 = await PX.adminFetch("/platform/audit-logs?limit=5");
    if (res5 && res5.ok) {
      var logs = await res5.json();
      var items = logs.items || [];
      var html = "";
      if (!items.length) {
        html = '<p style="color: var(--adm-muted);">No audit entries yet.</p>';
      } else {
        items.forEach(function (l) {
          html += '<div class="admin-list-item">' +
            '<div class="admin-list-item-main">' +
            '<div class="admin-list-item-title">' + PX.esc(l.action) + '</div>' +
            '<div class="admin-list-item-sub">' + PX.esc(l.actor_type) + '</div></div>' +
            '<div class="admin-list-item-side">' + new Date(l.created_at).toLocaleString() + '</div>' +
            '</div>';
        });
      }
      document.getElementById("recent-audit").innerHTML = html;
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
