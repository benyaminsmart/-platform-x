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

/* ---------- Tenants List ---------- */

PX.initAdminTenants = async function () {
  if (!PX.requireAdmin()) return;

  var tbody = document.getElementById("tenants-tbody");
  var filter = document.getElementById("filter-status");
  var allTenants = [];

  function render() {
    var selected = filter ? filter.value : "";
    var rows = allTenants.filter(function (t) { return !selected || t.status === selected; });

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--adm-muted); padding: 40px;">No tenants match the filter.</td></tr>';
      return;
    }

    var html = "";
    rows.forEach(function (t) {
      var badgeCls = t.status === "active" ? "admin-badge-success"
        : t.status === "suspended" ? "admin-badge-warning"
        : "admin-badge-error";
      var btype = (t.config && t.config.type) || "—";
      var created = t.created_at ? new Date(t.created_at).toLocaleDateString() : "—";
      html += '<tr style="cursor: pointer;" onclick="window.location.href=\'/admin/tenants/' + t.id + '\'">' +
        '<td><strong style="color: var(--adm-text);">' + PX.esc(t.name) + '</strong></td>' +
        '<td><span style="font-family: var(--adm-font-mono); font-size: 12px;">' + PX.esc(t.slug) + '</span></td>' +
        '<td>' + PX.esc(btype) + '</td>' +
        '<td>' + PX.esc(t.tier) + '</td>' +
        '<td><span class="admin-badge ' + badgeCls + '">' + PX.esc(t.status) + '</span></td>' +
        '<td>' + PX.esc(created) + '</td>' +
        '</tr>';
    });
    tbody.innerHTML = html;
  }

  if (filter) filter.addEventListener("change", render);

  try {
    var res = await PX.adminFetch("/platform/tenants");
    if (res && res.ok) {
      allTenants = await res.json();
      render();
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--adm-error); padding: 40px;">Failed to load tenants.</td></tr>';
  }
};

/* ---------- Tenant Detail ---------- */

PX.initAdminTenantDetail = async function (tenantId) {
  if (!PX.requireAdmin()) return;
  var el = document.getElementById("tenant-detail");
  if (!el) return;

  try {
    var res = await PX.adminFetch("/platform/tenants");
    if (!res || !res.ok) throw new Error("load failed");
    var tenants = await res.json();
    var t = tenants.find(function (x) { return x.id === tenantId; });
    if (!t) {
      el.innerHTML = '<div class="admin-card"><h2>Tenant not found</h2></div>';
      return;
    }

    var badgeCls = t.status === "active" ? "admin-badge-success" : "admin-badge-warning";
    var btype = (t.config && t.config.type) || "—";
    var created = t.created_at ? new Date(t.created_at).toLocaleString() : "—";

    el.innerHTML =
      '<div class="admin-card" style="margin-bottom: 24px;">' +
      '<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">' +
      '<div>' +
      '<div style="color: var(--adm-muted); font-size: 12px; margin-bottom: 6px;"><a href="/admin/tenants">← Back to tenants</a></div>' +
      '<h2 style="font-size: 24px;">' + PX.esc(t.name) + '</h2>' +
      '<p class="admin-card-sub">' + PX.esc(t.slug) + ' · ' + PX.esc(btype) + ' · ' + PX.esc(t.tier) + '</p>' +
      '</div>' +
      '<span class="admin-badge ' + badgeCls + '" style="font-size: 13px; padding: 8px 16px;">' + PX.esc(t.status) + '</span>' +
      '</div>' +
      '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 16px;">' +
      '<div><div class="admin-stat-label">ID</div><div style="font-family: var(--adm-font-mono); font-size: 12px; color: var(--adm-text-soft); word-break: break-all;">' + PX.esc(t.id) + '</div></div>' +
      '<div><div class="admin-stat-label">Created</div><div style="color: var(--adm-text-soft);">' + PX.esc(created) + '</div></div>' +
      '</div>' +
      '</div>' +

      '<div class="admin-card">' +
      '<h2>Actions</h2>' +
      '<p class="admin-card-sub">Change tenant status. Use with caution.</p>' +
      '<div style="display: flex; gap: 12px; flex-wrap: wrap;">' +
      '<button class="admin-btn" id="btn-activate" ' + (t.status === "active" ? "disabled" : "") + '>Activate</button>' +
      '<button class="admin-btn" id="btn-suspend" style="background: #f59e0b;" ' + (t.status === "suspended" ? "disabled" : "") + '>Suspend</button>' +
      '<button class="admin-btn" id="btn-delete" style="background: #dc2626;">Soft Delete</button>' +
      '</div>' +
      '</div>';

    function setStatus(newStatus) {
      fetch("/platform/tenants/" + tenantId + "/status?new_status=" + newStatus, {
        method: "PATCH",
        headers: PX.adminHeaders(),
      })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status) {
          window.location.reload();
        } else {
          alert(d.detail || "Update failed");
        }
      })
      .catch(function () { alert("Network error"); });
    }

    var ba = document.getElementById("btn-activate");
    var bs = document.getElementById("btn-suspend");
    var bd = document.getElementById("btn-delete");
    if (ba && !ba.disabled) ba.addEventListener("click", function () { setStatus("active"); });
    if (bs && !bs.disabled) bs.addEventListener("click", function () { setStatus("suspended"); });
    if (bd) bd.addEventListener("click", function () {
      if (confirm("Soft delete this tenant? Users will no longer see it.")) setStatus("deleted");
    });
  } catch (e) {
    el.innerHTML = '<div class="admin-card"><h2>Error</h2><p>Failed to load tenant.</p></div>';
  }
};

/* ---------- Applications ---------- */

PX.initAdminApplications = async function () {
  if (!PX.requireAdmin()) return;
  var tbody = document.getElementById("apps-tbody");
  var filter = document.getElementById("filter-status");
  var all = [];

  function render() {
    var sel = filter ? filter.value : "";
    var rows = all.filter(function (a) { return !sel || a.status === sel; });
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--adm-muted); padding: 40px;">No applications found.</td></tr>';
      return;
    }
    var html = "";
    rows.forEach(function (a) {
      var badgeCls = a.status === "new" ? "admin-badge-info"
        : a.status === "approved" ? "admin-badge-success"
        : a.status === "rejected" ? "admin-badge-error"
        : "admin-badge-warning";
      var date = a.created_at ? new Date(a.created_at).toLocaleDateString() : "—";
      html += '<tr>' +
        '<td><strong style="color: var(--adm-text);">' + PX.esc(a.business_name) + '</strong></td>' +
        '<td>' + PX.esc(a.tenant_type) + '</td>' +
        '<td>' + PX.esc(a.contact_name) + '<br><span style="color: var(--adm-muted); font-size: 12px;">' + PX.esc(a.email) + '</span></td>' +
        '<td>' + PX.esc(a.city) + '</td>' +
        '<td><span class="admin-badge ' + badgeCls + '">' + PX.esc(a.status) + '</span></td>' +
        '<td>' + PX.esc(date) + '</td>' +
        '</tr>';
    });
    tbody.innerHTML = html;
  }

  if (filter) filter.addEventListener("change", render);

  try {
    var res = await PX.adminFetch("/platform/applications?limit=200");
    if (res && res.ok) {
      var data = await res.json();
      all = data.items || [];
      render();
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--adm-error); padding: 40px;">Failed to load applications.</td></tr>';
  }
};
