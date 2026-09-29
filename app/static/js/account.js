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
      list.innerHTML = '<p class="px-muted">' + (window.PX_I18N ? PX_I18N.no_activity : 'No activity yet.') + '</p>';
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
        document.getElementById("rewards-next-label").textContent = (window.PX_I18N && PX_I18N.top_tier) || "Top tier reached 🎉";
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
        list.innerHTML = '<p class="px-muted">' + (window.PX_I18N ? PX_I18N.no_referrals : 'No referrals yet.') + '</p>';
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
  fetch("/bookings?all=true&limit=50", { headers: headers })
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
        list.innerHTML = '<p class="px-muted">' + (window.PX_I18N ? PX_I18N.no_bookings : 'No bookings yet.') + '</p>';
      } else {
        var html = "";
        d.items.forEach(function (b) {
          var cancellable = (b.status === "pending" || b.status === "confirmed");
          var modifiable = cancellable && (new Date(b.check_in) > new Date());
          var actionHtml = "";
          if (modifiable) {
            actionHtml += '<button class="px-btn px-btn-ghost px-mod-btn" data-bid="' + esc(b.id) + '" style="margin-top:6px; font-size:12px; padding:4px 10px; margin-right:4px;">Modify</button>';
          }
          if (cancellable) {
            actionHtml += '<button class="px-btn px-btn-ghost px-cancel-btn" data-bid="' + esc(b.id) + '" style="margin-top:6px; font-size:12px; padding:4px 10px;">Cancel</button>';
          }
          html += '<div class="px-list-item" data-bid="' + esc(b.id) + '">' +
            '<div class="px-list-item-main">' +
              '<div class="px-list-item-title">' + esc(b.service_name) + "</div>" +
              '<div class="px-list-item-sub">' + esc(b.check_in) +
              (b.check_out ? " \u2192 " + esc(b.check_out) : "") + " \u00B7 " + b.guests + " guests" +
              (b.room_number ? (" \u00B7 Room " + esc(b.room_number)) : "") +
              '</div></div>" +
            '<div class="px-list-item-side">' + badge(b.status) +
              '<div class="px-list-item-amount">' + esc(b.total_amount) + " " + esc(b.currency) + "</div>" +
              actionHtml + "</div></div>";
        });
        list.innerHTML = html;
        list.querySelectorAll(".px-cancel-btn").forEach(function(btn){
          btn.addEventListener("click", function(){ handleCancel(btn); });
        });
        list.querySelectorAll(".px-mod-btn").forEach(function(btn){
          btn.addEventListener("click", function(){ handleModify(btn); });
        });
      }
      renderRecent();
    })
    .catch(function () {});

  // Orders
  fetch("/orders?all=true&limit=50", { headers: headers })
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
        list.innerHTML = '<p class="px-muted">' + (window.PX_I18N ? PX_I18N.no_orders : 'No orders yet.') + '</p>';
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
        list.innerHTML = '<p class="px-muted">' + (window.PX_I18N ? PX_I18N.no_rewards : 'No rewards yet.') + '</p>';
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


  // Notifications
  fetch("/notifications?limit=30", { headers: headers })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var list = document.getElementById("notifications-list");
      if (!list) return;

      // Update badge
      var unread = (d.items || []).filter(function(n){ return !n.read_at; }).length;
      var badge = document.getElementById("notif-badge");
      if (badge) {
        if (unread > 0) {
          badge.textContent = unread;
          badge.style.display = "inline-block";
        } else {
          badge.style.display = "none";
        }
      }

      if (!d.items || !d.items.length) {
        list.innerHTML = '<p class="px-muted">' + (window.PX_I18N ? PX_I18N.no_notifications : 'No notifications yet.') + '</p>';
        return;
      }
      var html = "";
      d.items.forEach(function (n) {
        var when = n.created_at ? new Date(n.created_at).toLocaleString() : "";
        var unreadStyle = !n.read_at ? 'border-left: 3px solid var(--px-brand);' : '';
        html += '<div class="px-list-item" style="' + unreadStyle + '">' +
          '<div class="px-list-item-main">' +
          '<div class="px-list-item-title">' + PX.esc(n.subject || n.template) + '</div>' +
          '<div class="px-list-item-sub">' + PX.esc(n.content) + '</div>' +
          '<div class="px-list-item-sub" style="margin-top: 4px; font-size: 11px;">' + PX.esc(when) + '</div>' +
          '</div>' +
          (n.read_at ? '' : '<div class="px-list-item-side"><button class="px-btn px-btn-ghost px-btn-sm" data-mark="' + n.id + '">Mark read</button></div>') +
          '</div>';
      });
      list.innerHTML = html;

      list.querySelectorAll("[data-mark]").forEach(function(btn){
        btn.addEventListener("click", async function(){
          var id = btn.getAttribute("data-mark");
          try {
            await fetch("/notifications/" + id + "/read", { method: "POST", headers: headers });
            window.location.reload();
          } catch(e) {}
        });
      });
    })
    .catch(function () {});
};

// ============================================================
// Cancellation flow (Phase 30 / Wave 0 part A)
// ============================================================
function handleCancel(btn) {
  var bid = btn.getAttribute("data-bid");
  if (!bid) return;
  var headers = window.PX_AUTH ? window.PX_AUTH.headers() : {};
  fetch("/bookings/" + encodeURIComponent(bid) + "/refund-preview", { headers: headers })
    .then(function(r){ return r.json(); })
    .then(function(p){
      if (!p || p.can_cancel === false) {
        alert("This booking cannot be cancelled.");
        return;
      }
      showCancelModal(bid, p);
    })
    .catch(function(){ alert("Could not load refund info."); });
}

function showCancelModal(bid, p) {
  var modalId = "px-cancel-modal";
  var old = document.getElementById(modalId);
  if (old) old.remove();
  var refundLine = (p.refund_pct > 0)
    ? ("You will receive a refund of " + p.refund_amount + " " + p.currency + " (" + p.refund_pct + "%).")
    : "No refund (less than 72 hours before check-in).";
  var html = '' +
    '<div id="' + modalId + '" style="position:fixed; inset:0; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:2000; padding:20px;">' +
      '<div style="background:#fff; border-radius:16px; padding:24px; max-width:440px; width:100%;">' +
        '<h3 style="font-family:var(--px-font-display); margin:0 0 12px; color:var(--px-navy);">Cancel this booking?</h3>' +
        '<p style="margin:0 0 10px; font-size:14px; color:#374151;">Check-in in <strong>' + p.days_until_check_in + ' day(s)</strong>. ' + refundLine + '</p>' +
        '<p style="margin:0 0 18px; font-size:13px; color:var(--px-muted);">' + p.reason + '</p>' +
        '<div style="display:flex; gap:8px; justify-content:flex-end;">' +
          '<button id="' + modalId + '-no" class="px-btn px-btn-ghost">Keep booking</button>' +
          '<button id="' + modalId + '-yes" class="px-btn px-btn-primary">Cancel booking</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  document.body.insertAdjacentHTML("beforeend", html);
  document.getElementById(modalId + "-no").addEventListener("click", function(){
    document.getElementById(modalId).remove();
  });
  document.getElementById(modalId + "-yes").addEventListener("click", function(){
    var headers = window.PX_AUTH ? window.PX_AUTH.headers() : {};
    fetch("/bookings/" + encodeURIComponent(bid) + "/cancel-with-refund", { method: "POST", headers: headers })
      .then(function(r){ return r.json(); })
      .then(function(res){
        document.getElementById(modalId).remove();
        if (res && res.status === "cancelled") {
          alert("Booking cancelled. Refund: " + res.refund_amount + " " + res.currency + " (" + res.refund_pct + "%).");
          location.reload();
        } else {
          alert("Could not cancel: " + (res && res.detail ? res.detail : "unknown"));
        }
      })
      .catch(function(){ alert("Network error."); });
  });
}

// ============================================================
// Booking modification flow (Phase 35 / Wave 1)
// ============================================================
function handleModify(btn) {
  var bid = btn.getAttribute("data-bid");
  if (!bid) return;
  var headers = window.PX_AUTH ? window.PX_AUTH.headers() : {};
  var t = new Date(); t.setDate(t.getDate() + 1);
  var t2 = new Date(); t2.setDate(t2.getDate() + 3);
  var iso = function(d){ return d.toISOString().slice(0,10); };
  showModifyModal(bid, iso(t), iso(t2), headers);
}

function showModifyModal(bid, ci, co, headers) {
  var modalId = "px-mod-modal";
  var old = document.getElementById(modalId);
  if (old) old.remove();

  var html = '' +
    '<div id="' + modalId + '" style="position:fixed; inset:0; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:2000; padding:20px;">' +
      '<div style="background:#fff; border-radius:16px; padding:24px; max-width:480px; width:100%;">' +
        '<h3 style="font-family:var(--px-font-display); margin:0 0 12px; color:var(--px-navy);">Modify booking dates</h3>' +
        '<label style="display:block; font-size:12px; color:#6b7280; margin-bottom:4px;">New check-in</label>' +
        '<input type="date" id="' + modalId + '-ci" value="' + ci + '" style="width:100%; padding:10px; border:1px solid #e5e7eb; border-radius:8px; font-family:inherit; font-size:14px; margin-bottom:12px;">' +
        '<label style="display:block; font-size:12px; color:#6b7280; margin-bottom:4px;">New check-out</label>' +
        '<input type="date" id="' + modalId + '-co" value="' + co + '" style="width:100%; padding:10px; border:1px solid #e5e7eb; border-radius:8px; font-family:inherit; font-size:14px; margin-bottom:12px;">' +
        '<div id="' + modalId + '-preview" style="font-size:13px; color:#374151; padding:10px 12px; background:#f5f3ef; border-radius:8px; margin-bottom:14px;">Select dates to see price change.</div>' +
        '<div style="display:flex; gap:8px; justify-content:flex-end;">' +
          '<button id="' + modalId + '-no" class="px-btn px-btn-ghost">Cancel</button>' +
          '<button id="' + modalId + '-save" class="px-btn px-btn-primary">Apply</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  document.body.insertAdjacentHTML("beforeend", html);

  var ciEl = document.getElementById(modalId + "-ci");
  var coEl = document.getElementById(modalId + "-co");
  var prevEl = document.getElementById(modalId + "-preview");

  function refreshPreview() {
    var ci = ciEl.value, co = coEl.value;
    if (!ci) return;
    prevEl.textContent = "Loading…";
    var url = "/bookings/" + encodeURIComponent(bid) + "/modify-preview?new_check_in=" + encodeURIComponent(ci);
    if (co) url += "&new_check_out=" + encodeURIComponent(co);
    fetch(url, { headers: headers })
      .then(function(r){ return r.json(); })
      .then(function(d){
        if (!d.can_modify) { prevEl.textContent = "Cannot modify: " + (d.reason || "unknown"); return; }
        var delta = parseFloat(d.delta_amount || "0");
        var sign = delta > 0 ? "+" : "";
        var cls = delta > 0 ? "#991b1b" : (delta < 0 ? "#166534" : "#6b7280");
        prevEl.innerHTML = 'Current: ' + d.current_total + ' ' + d.currency +
          '<br>New total: <strong>' + d.new_total + ' ' + d.currency + '</strong>' +
          '<br><span style="color:' + cls + '; font-weight:600;">Delta: ' + sign + d.delta_amount + ' ' + d.currency + '</span>';
      })
      .catch(function(){ prevEl.textContent = "Network error."; });
  }

  ciEl.addEventListener("change", refreshPreview);
  coEl.addEventListener("change", refreshPreview);
  refreshPreview();

  document.getElementById(modalId + "-no").addEventListener("click", function(){
    document.getElementById(modalId).remove();
  });
  document.getElementById(modalId + "-save").addEventListener("click", function(){
    var ci2 = ciEl.value, co2 = coEl.value;
    if (!ci2) { alert("Check-in is required"); return; }
    fetch("/bookings/" + encodeURIComponent(bid) + "/modify", {
      method: "POST", headers: headers,
      body: JSON.stringify({ new_check_in: ci2, new_check_out: co2 || null }),
    })
      .then(function(r){ return r.json(); })
      .then(function(res){
        if (!res.ok) { alert("Cannot modify: " + (res.reason || "unknown")); return; }
        document.getElementById(modalId).remove();
        alert("Dates updated. Delta: " + res.delta_amount + " " + res.currency);
        location.reload();
      })
      .catch(function(){ alert("Network error."); });
  });
}

