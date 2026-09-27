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
  var collectedEvents = []; // {time, type, title, sub, amount, currency, badge}
  var totalBookings = 0;
  var totalOrders = 0;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function badge(status) {
    var cls = "px-cat";
    if (status === "confirmed" || status === "delivered" || status === "paid") cls += " px-cat-travel";
    else if (status === "pending" || status === "preparing") cls += " px-cat-restaurants";
    else if (status === "cancelled" || status === "failed") cls += " px-cat-restaurants";
    else cls += " px-cat-hotels";
    return '<span class="' + cls + '" style="text-transform: capitalize;">' + esc(status) + "</span>";
  }

  // Tabs
  document.querySelectorAll(".px-tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = btn.getAttribute("data-tab");
      document.querySelectorAll(".px-tab").forEach(function (b) { b.classList.remove("is-active"); });
      document.querySelectorAll(".px-tab-panel").forEach(function (p) { p.style.display = "none"; });
      btn.classList.add("is-active");
      var panel = document.getElementById("tab-" + target);
      if (panel) panel.style.display = "block";
    });
  });

  function renderRecent() {
    var list = document.getElementById("recent-list");
    var recent = collectedEvents
      .sort(function (a, b) { return new Date(b.time) - new Date(a.time); })
      .slice(0, 5);
    if (!recent.length) {
      list.innerHTML = '<p class="px-muted">No activity yet. Book something to see it here.</p>';
      return;
    }
    var html = "";
    recent.forEach(function (ev) {
      html += '<div class="px-list-item">' +
        '<div class="px-list-item-main">' +
        '<div class="px-list-item-title">' + esc(ev.title) + "</div>" +
        '<div class="px-list-item-sub">' + esc(ev.type) + " · " + esc(ev.sub) + "</div></div>" +
        '<div class="px-list-item-side">' + (ev.badge || "") +
        (ev.amount ? '<div class="px-list-item-amount">' + esc(ev.amount) + " " + esc(ev.currency) + "</div>" : "") +
        "</div></div>";
    });
    list.innerHTML = html;
  }

  // Profile + Rewards summary
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
      document.getElementById("stat-name").textContent = u.first_name + " " + u.last_name;
      document.getElementById("stat-email").textContent = u.email;
    })
    .catch(function () {});

  // Rewards summary with progress
  fetch("/rewards/me", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById("rewards-points").textContent = d.points + " pts";
      document.getElementById("rewards-tier").textContent = "Tier: " + d.tier;

      if (d.next_tier) {
        document.getElementById("rewards-next-label").textContent = "Progress to " + d.next_tier;
        document.getElementById("rewards-next-points").textContent = d.points_to_next_tier + " pts to go";
        document.getElementById("rewards-progress-bar").style.width = d.progress_percent + "%";
      } else {
        document.getElementById("rewards-next-label").textContent = "Top tier reached 🎉";
        document.getElementById("rewards-next-points").textContent = "";
        document.getElementById("rewards-progress-bar").style.width = "100%";
      }
    })
    .catch(function () {});

  // Referrals
  fetch("/referrals/me", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById("stat-referrals").textContent = d.completed_count;
      document.getElementById("rewards-referral-code").textContent = d.referral_code;

      var copyBtn = document.getElementById("referral-copy");
      copyBtn.addEventListener("click", function () {
        var code = d.referral_code;
        if (navigator.clipboard) {
          navigator.clipboard.writeText(code).then(function () {
            copyBtn.classList.add("is-copied");
            copyBtn.querySelector(".px-referral-copy-icon").textContent = "✓";
            setTimeout(function () {
              copyBtn.classList.remove("is-copied");
              copyBtn.querySelector(".px-referral-copy-icon").textContent = "📋";
            }, 1500);
          });
        } else {
          alert("Your referral code: " + code);
        }
      });

      var list = document.getElementById("referrals-list");
      if (!d.referrals || !d.referrals.length) {
        list.innerHTML = '<p class="px-muted">No referrals yet. Share your code with friends — you both earn points.</p>';
        return;
      }
      var html = "";
      d.referrals.forEach(function (r) {
        html += '<div class="px-list-item"><div class="px-list-item-main">' +
          '<div class="px-list-item-title">' + esc(r.referred_user_id.substring(0, 8)) + "…</div>" +
          '<div class="px-list-item-sub">' + esc(r.status) + "</div></div>" +
          '<div class="px-list-item-side"><div class="px-list-item-amount">+' + r.reward_points + " pts</div></div></div>";
      });
      list.innerHTML = html;
    })
    .catch(function () {});

  // Bookings
  fetch("/bookings?limit=50", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById("stat-bookings").textContent = d.total;
      d.items.forEach(function (b) {
        collectedEvents.push({
          time: b.created_at,
          type: "Booking",
          title: b.service_name,
          sub: b.check_in + (b.check_out ? " → " + b.check_out : ""),
          amount: b.total_amount,
          currency: b.currency,
          badge: badge(b.status),
        });
      });
      var list = document.getElementById("bookings-list");
      if (!d.items.length) {
        list.innerHTML = '<p class="px-muted">No bookings yet.</p>';
      } else {
        var html = "";
        d.items.forEach(function (b) {
          html += '<div class="px-list-item">' +
            '<div class="px-list-item-main">' +
            '<div class="px-list-item-title">' + esc(b.service_name) + "</div>" +
            '<div class="px-list-item-sub">' + esc(b.check_in) +
            (b.check_out ? " → " + esc(b.check_out) : "") + " · " + b.guests + " guests</div></div>" +
            '<div class="px-list-item-side">' + badge(b.status) +
            '<div class="px-list-item-amount">' + esc(b.total_amount) + " " + esc(b.currency) + "</div></div></div>";
        });
        list.innerHTML = html;
      }
      renderRecent();
    })
    .catch(function () {});

  // Orders
  fetch("/orders?limit=50", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById("stat-orders").textContent = d.total;
      d.items.forEach(function (o) {
        collectedEvents.push({
          time: o.created_at,
          type: "Order",
          title: o.service_name,
          sub: "Qty " + o.quantity,
          amount: o.amount,
          currency: o.currency,
          badge: badge(o.status),
        });
      });
      var list = document.getElementById("orders-list");
      if (!d.items.length) {
        list.innerHTML = '<p class="px-muted">No orders yet.</p>';
      } else {
        var html = "";
        d.items.forEach(function (o) {
          html += '<div class="px-list-item">' +
            '<div class="px-list-item-main">' +
            '<div class="px-list-item-title">' + esc(o.service_name) + "</div>" +
            '<div class="px-list-item-sub">Qty ' + o.quantity + "</div></div>" +
            '<div class="px-list-item-side">' + badge(o.status) +
            '<div class="px-list-item-amount">' + esc(o.amount) + " " + esc(o.currency) + "</div></div></div>";
        });
        list.innerHTML = html;
      }
      renderRecent();
    })
    .catch(function () {});

  // Rewards history
  fetch("/rewards/history?limit=50", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var list = document.getElementById("rewards-list");
      if (!d.items.length) {
        list.innerHTML = '<p class="px-muted">No rewards yet. Book something to earn points!</p>';
        return;
      }
      var html = "";
      d.items.forEach(function (rw) {
        var sign = rw.points > 0 ? "+" : "";
        html += '<div class="px-list-item">' +
          '<div class="px-list-item-main">' +
          '<div class="px-list-item-title">' + esc(rw.description || rw.reward_type) + "</div>" +
          '<div class="px-list-item-sub">' + new Date(rw.created_at).toLocaleDateString() + "</div></div>" +
          '<div class="px-list-item-side"><div class="px-list-item-amount">' + sign + rw.points + " pts</div></div></div>";
      });
      list.innerHTML = html;
    })
    .catch(function () {});
};
