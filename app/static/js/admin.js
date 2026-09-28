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

/* ---------- Audit Logs ---------- */

PX.initAdminAuditLogs = async function () {
  if (!PX.requireAdmin()) return;
  var tbody = document.getElementById("audit-tbody");
  var pag = document.getElementById("audit-pagination");
  var currentPage = 1;
  var limit = 50;
  var total = 0;

  async function load(page) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--adm-muted); padding: 40px;">Loading…</td></tr>';
    try {
      var res = await PX.adminFetch("/platform/audit-logs?page=" + page + "&limit=" + limit);
      if (res && res.ok) {
        var data = await res.json();
        total = data.total;
        render(data.items || []);
        renderPagination();
      }
    } catch (e) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--adm-error); padding: 40px;">Failed to load.</td></tr>';
    }
  }

  function render(items) {
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--adm-muted); padding: 40px;">No entries.</td></tr>';
      return;
    }
    var html = "";
    items.forEach(function (l) {
      var when = l.created_at ? new Date(l.created_at).toLocaleString() : "—";
      var target = l.target_table ? l.target_table + (l.target_id ? " (" + l.target_id.slice(0, 8) + "…)" : "") : "—";
      var changes = l.changes ? JSON.stringify(l.changes).slice(0, 80) : "—";
      html += '<tr>' +
        '<td style="font-size: 12px; color: var(--adm-muted);">' + PX.esc(when) + '</td>' +
        '<td><span class="admin-badge admin-badge-info">' + PX.esc(l.actor_type) + '</span></td>' +
        '<td><strong style="color: var(--adm-text);">' + PX.esc(l.action) + '</strong></td>' +
        '<td style="font-family: var(--adm-font-mono); font-size: 12px;">' + PX.esc(target) + '</td>' +
        '<td style="font-family: var(--adm-font-mono); font-size: 11px; color: var(--adm-muted);">' + PX.esc(changes) + '</td>' +
        '</tr>';
    });
    tbody.innerHTML = html;
  }

  function renderPagination() {
    var totalPages = Math.ceil(total / limit);
    if (totalPages <= 1) { pag.innerHTML = ""; return; }
    pag.innerHTML =
      '<button class="admin-btn" ' + (currentPage === 1 ? "disabled" : "") + ' id="pg-prev">← Prev</button>' +
      '<span style="align-self: center; color: var(--adm-muted); font-size: 13px;">Page ' + currentPage + " of " + totalPages + '</span>' +
      '<button class="admin-btn" ' + (currentPage >= totalPages ? "disabled" : "") + ' id="pg-next">Next →</button>';
    var pv = document.getElementById("pg-prev");
    var nx = document.getElementById("pg-next");
    if (pv) pv.addEventListener("click", function () { currentPage--; load(currentPage); });
    if (nx) nx.addEventListener("click", function () { currentPage++; load(currentPage); });
  }

  await load(1);
};

/* ---------- Subscriptions ---------- */

PX.initAdminSubscriptions = async function () {
  if (!PX.requireAdmin()) return;

  var tbody = document.getElementById("subs-tbody");
  var form = document.getElementById("new-sub-form");
  var btnNew = document.getElementById("btn-new-sub");
  var btnCancel = document.getElementById("btn-cancel-sub");
  var btnCreate = document.getElementById("btn-create-sub");
  var tenantSelect = document.getElementById("sub-tenant");
  var alertBox = document.getElementById("sub-alert");
  var tenantsById = {};

  btnNew.addEventListener("click", function () {
    form.style.display = "block";
    btnNew.disabled = true;
  });
  btnCancel.addEventListener("click", function () {
    form.style.display = "none";
    alertBox.style.display = "none";
    btnNew.disabled = false;
  });

  async function loadTenants() {
    try {
      var res = await PX.adminFetch("/platform/tenants");
      if (res && res.ok) {
        var tenants = await res.json();
        tenants.forEach(function (t) { tenantsById[t.id] = t.name; });
        tenantSelect.innerHTML = tenants
          .filter(function (t) { return t.status === "active"; })
          .map(function (t) { return '<option value="' + t.id + '">' + PX.esc(t.name) + '</option>'; })
          .join("");
      }
    } catch (e) {}
  }

  async function load() {
    try {
      var res = await PX.adminFetch("/platform/subscriptions");
      if (res && res.ok) {
        var subs = await res.json();
        if (!subs.length) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--adm-muted); padding: 40px;">No subscriptions yet.</td></tr>';
          return;
        }
        var html = "";
        subs.forEach(function (s) {
          var badgeCls = s.status === "active" ? "admin-badge-success" : "admin-badge-warning";
          var period = s.current_period_start && s.current_period_end
            ? new Date(s.current_period_start).toLocaleDateString() + " → " + new Date(s.current_period_end).toLocaleDateString()
            : "—";
          var tenantName = tenantsById[s.tenant_id] || s.tenant_id.slice(0, 8) + "…";
          html += '<tr>' +
            '<td><strong style="color: var(--adm-text);">' + PX.esc(tenantName) + '</strong></td>' +
            '<td>' + PX.esc(s.plan) + '</td>' +
            '<td><span class="admin-badge ' + badgeCls + '">' + PX.esc(s.status) + '</span></td>' +
            '<td>' + PX.esc(s.price) + " " + PX.esc(s.currency) + '</td>' +
            '<td>' + PX.esc(s.billing_cycle) + '</td>' +
            '<td style="font-size: 12px;">' + PX.esc(period) + '</td>' +
            '</tr>';
        });
        tbody.innerHTML = html;
      }
    } catch (e) {}
  }

  btnCreate.addEventListener("click", async function () {
    alertBox.style.display = "none";
    var payload = {
      tenant_id: tenantSelect.value,
      plan: document.getElementById("sub-plan").value,
      price: document.getElementById("sub-price").value,
      currency: "AED",
      billing_cycle: document.getElementById("sub-cycle").value,
    };
    try {
      var res = await fetch("/platform/subscriptions", {
        method: "POST",
        headers: PX.adminHeaders(),
        body: JSON.stringify(payload),
      });
      var data = await res.json();
      if (!res.ok) {
        alertBox.textContent = data.detail || "Failed to create";
        alertBox.style.display = "block";
        return;
      }
      form.style.display = "none";
      btnNew.disabled = false;
      await load();
    } catch (e) {
      alertBox.textContent = "Network error";
      alertBox.style.display = "block";
    }
  });

  await loadTenants();
  await load();
};
