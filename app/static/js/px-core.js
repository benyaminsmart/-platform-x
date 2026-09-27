/* Platform-X — Core utilities (loaded on every page) */

window.PX = window.PX || {};

PX.RESERVED_SLUGS = [
  "docs", "redoc", "static", "health", "auth", "tenants", "services",
  "bookings", "orders", "payments", "rewards", "referrals", "notifications",
  "analytics", "platform", "businesses", "about", "contact",
  "login", "register", "hotels", "restaurants", "travel", "entertainment"
];

PX.getTenantSlug = function () {
  var parts = window.location.pathname.split("/").filter(Boolean);
  if (parts.length && PX.RESERVED_SLUGS.indexOf(parts[0]) === -1) return parts[0];
  return null;
};

PX.getToken = function () {
  try { return localStorage.getItem("px_token"); } catch (e) { return null; }
};

PX.saveToken = function (token) {
  try { localStorage.setItem("px_token", token); } catch (e) {}
};

PX.clearToken = function () {
  try { localStorage.removeItem("px_token"); } catch (e) {}
};

PX.isLoggedIn = function () {
  return !!PX.getToken();
};

PX.apiHeaders = function () {
  var h = { "Content-Type": "application/json" };
  var slug = PX.getTenantSlug();
  h["X-Tenant-Slug"] = slug || "trianon-hotel";
  return h;
};

PX.authHeaders = function (slug) {
  var h = { "Content-Type": "application/json" };
  h["X-Tenant-Slug"] = slug || PX.getTenantSlug() || "trianon-hotel";
  var t = PX.getToken();
  if (t) h["Authorization"] = "Bearer " + t;
  return h;
};

PX.showAlert = function (message, kind) {
  var box = document.getElementById("alert-box");
  if (!box) { alert(message); return; }
  box.className = "alert alert-" + (kind || "error");
  box.textContent = message;
  box.style.display = "block";
  box.style.padding = "12px 16px";
  box.style.borderRadius = "var(--px-radius)";
  box.style.marginBottom = "20px";
  if ((kind || "error") === "error") {
    box.style.background = "var(--px-error-soft, #fdeded)";
    box.style.color = "var(--px-error, #e53e3e)";
    box.style.border = "1px solid rgba(229, 62, 62, 0.3)";
  } else {
    box.style.background = "var(--px-success-soft, #e9f7ef)";
    box.style.color = "var(--px-success, #38a169)";
    box.style.border = "1px solid rgba(56, 161, 105, 0.3)";
  }
};

PX.hideAlert = function () {
  var box = document.getElementById("alert-box");
  if (box) box.style.display = "none";
};

PX.esc = function (s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
};

PX.formatDate = function (iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleDateString(); } catch (e) { return iso; }
};

/* Logout: clears token and goes home */
PX.logout = function () {
  PX.clearToken();
  window.location.href = "/";
};

/* Header auth widget: swaps Login/Get started for avatar+logout when logged in */
PX.initHeaderAuth = function () {
  var slot = document.getElementById("px-auth-slot");
  if (!slot) return;

  if (!PX.isLoggedIn()) {
    slot.innerHTML =
      '<a href="/login" class="px-btn px-btn-ghost">Sign in</a>' +
      '<a href="/register" class="px-btn px-btn-primary">Get started</a>';
    return;
  }

  // Logged in: fetch user info for initials
  var slug = PX.getTenantSlug() || "trianon-hotel";
  fetch("/auth/me", { headers: PX.authHeaders(slug) })
    .then(function (r) { if (!r.ok) throw new Error("auth"); return r.json(); })
    .then(function (u) {
      var initials = (u.first_name ? u.first_name[0] : "") + (u.last_name ? u.last_name[0] : "");
      initials = initials.toUpperCase() || "U";
      var accountHref = "/account";
      slot.innerHTML =
        '<div class="px-user-menu">' +
          '<button class="px-user-avatar" id="px-user-toggle" aria-haspopup="true" aria-expanded="false" title="Account">' +
            '<span>' + initials + '</span>' +
          '</button>' +
          '<div class="px-user-dropdown" id="px-user-dropdown">' +
            '<div class="px-user-info">' +
              '<strong>' + PX.esc(u.first_name + " " + u.last_name) + '</strong>' +
              '<span>' + PX.esc(u.email) + '</span>' +
            '</div>' +
            '<a href="' + accountHref + '">My Account</a>' +
            '<a href="' + accountHref + '">Rewards (' + (u.points || 0) + ' pts)</a>' +
            '<button type="button" class="px-logout-btn" id="px-logout-btn">Log out</button>' +
          '</div>' +
        '</div>';

      var toggle = document.getElementById("px-user-toggle");
      var dd = document.getElementById("px-user-dropdown");
      toggle.addEventListener("click", function (e) {
        e.stopPropagation();
        var open = dd.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
      document.addEventListener("click", function () {
        dd.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
      document.getElementById("px-logout-btn").addEventListener("click", PX.logout);
    })
    .catch(function () {
      slot.innerHTML =
        '<a href="/login" class="px-btn px-btn-ghost">Sign in</a>' +
        '<a href="/register" class="px-btn px-btn-primary">Get started</a>';
    });
};

/* Auto-init on DOM ready */
document.addEventListener("DOMContentLoaded", function () {
  PX.initHeaderAuth();
});
