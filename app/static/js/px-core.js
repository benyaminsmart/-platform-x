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

/* Count-up animation for stats */
PX.pxCountUp = function () {
  var els = document.querySelectorAll("[data-count]");
  if (!els.length) return;

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) return;

  function animate(el) {
    var target = parseInt(el.getAttribute("data-count"), 10);
    if (isNaN(target) || target <= 0) return;
    var start = 0;
    var duration = 1200;
    var startTime = null;

    function step(ts) {
      if (!startTime) startTime = ts;
      var progress = Math.min((ts - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var value = Math.floor(start + (target - start) * eased);
      el.textContent = value.toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(step);
  }

  if ("IntersectionObserver" in window) {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animate(entry.target);
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    els.forEach(function (el) { obs.observe(el); });
  } else {
    els.forEach(animate);
  }
};

document.addEventListener("DOMContentLoaded", function () {
  PX.pxCountUp();
});

/* ---------- Language Switcher ---------- */

PX.initLangSwitcher = function () {
  var toggle = document.getElementById("px-lang-toggle");
  var menu = document.getElementById("px-lang-menu");

  if (!toggle || !menu) return;

  var currentLang = document.documentElement.getAttribute("lang") || "en";

  // Mark active option
  menu.querySelectorAll(".px-lang-option").forEach(function (opt) {
    if (opt.getAttribute("data-lang") === currentLang) {
      opt.classList.add("is-active");
    }
  });

  toggle.addEventListener("click", function (e) {
    e.stopPropagation();
    var open = menu.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  document.addEventListener("click", function () {
    menu.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
  });

  // When user clicks a language, persist to cookie + reload
  menu.querySelectorAll(".px-lang-option").forEach(function (opt) {
    opt.addEventListener("click", function (e) {
      e.preventDefault();
      var lang = opt.getAttribute("data-lang");
      // Set cookie for 1 year
      document.cookie = "px_lang=" + lang + "; max-age=31536000; path=/; SameSite=Lax";
      // Reload without ?lang query (cookie will be used)
      var url = window.location.pathname;
      window.location.href = url;
    });
  });
};

document.addEventListener("DOMContentLoaded", function () {
  PX.initLangSwitcher();
});
