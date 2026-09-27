/* Platform-X — Account dashboard */

window.PX = window.PX || {};

PX.initAccount = function (slug) {
  var token = PX.getToken();
  var notLoggedIn = document.getElementById("not-logged-in");
  var dashboard = document.getElementById("dashboard");

  if (!token) {
    notLoggedIn.style.display = "block";
    return;
  }
  dashboard.style.display = "block";

  var headers = PX.authHeaders(slug);

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function badge(status) {
    var cls = "badge";
    if (status === "confirmed" || status === "delivered") cls += " badge-success";
    else if (status === "pending" || status === "preparing") cls += " badge-warning";
    else if (status === "cancelled" || status === "failed") cls += " badge-error";
    else cls += " badge-info";
    return '<span class="' + cls + '">' + esc(status) + "</span>";
  }

  // 1. Profile
  fetch("/auth/me", { headers: headers })
    .then(function (r) {
      if (r.status === 401) {
        notLoggedIn.style.display = "block";
        dashboard.style.display = "none";
        throw new Error("unauthorized");
      }
      return r.json();
    })
    .then(function (u) {
      document.getElementById("user-name").textContent =
        u.first_name + " " + u.last_name;
      document.getElementById("user-email").textContent = u.email;
      document.getElementById("user-points").textContent = u.points + " pts";
      document.getElementById("user-tier").textContent = u.tier;
    })
    .catch(function () {});

  // 2. Referral code
  fetch("/referrals/me", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById("referral-code").textContent = d.referral_code;
      var list = document.getElementById("referrals-list");
      if (!d.referrals.length) {
        list.innerHTML = '<p class="text-muted">No referrals yet. Share your code.</p>';
        return;
      }
      var html = '<div style="display: grid; gap: var(--space-3);">';
      d.referrals.forEach(function (r) {
        html += '<div class="card-flat" style="display: flex; justify-content: space-between;">' +
          "<span>" + esc(r.referred_user_id.substring(0, 8)) + "…</span>" +
          '<span class="text-gold">+' + r.reward_points + " pts</span></div>";
      });
      html += "</div>";
      list.innerHTML = html;
    })
    .catch(function () {});

  // 3. Bookings
  fetch("/bookings?limit=20", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var list = document.getElementById("bookings-list");
      if (!d.items.length) {
        list.innerHTML = '<p class="text-muted">No bookings yet.</p>';
        return;
      }
      var html = '<div style="display: grid; gap: var(--space-3);">';
      d.items.forEach(function (b) {
        html += '<div class="card-flat">' +
          '<div style="display: flex; justify-content: space-between; align-items: center;">' +
          "<div><strong>" + esc(b.service_name) + "</strong>" +
          '<div class="text-sm text-muted">' + esc(b.check_in) +
          (b.check_out ? " → " + esc(b.check_out) : "") + "</div></div>" +
          "<div style=\"text-align: right;\">" +
          badge(b.status) + "<br>" +
          '<span class="text-sm text-gold" style="margin-top: var(--space-2); display: inline-block;">' +
          esc(b.total_amount) + " " + esc(b.currency) + "</span>" +
          "</div></div></div>";
      });
      html += "</div>";
      list.innerHTML = html;
    })
    .catch(function () {});

  // 4. Orders
  fetch("/orders?limit=20", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var list = document.getElementById("orders-list");
      if (!d.items.length) {
        list.innerHTML = '<p class="text-muted">No orders yet.</p>';
        return;
      }
      var html = '<div style="display: grid; gap: var(--space-3);">';
      d.items.forEach(function (o) {
        html += '<div class="card-flat" style="display: flex; justify-content: space-between; align-items: center;">' +
          "<div><strong>" + esc(o.service_name) + "</strong>" +
          '<div class="text-sm text-muted">Qty ' + o.quantity + "</div></div>" +
          "<div style=\"text-align: right;\">" +
          badge(o.status) +
          '<div class="text-sm text-gold" style="margin-top: var(--space-2);">' +
          esc(o.amount) + " " + esc(o.currency) + "</div>" +
          "</div></div>";
      });
      html += "</div>";
      list.innerHTML = html;
    })
    .catch(function () {});
};
