/* Platform-X — Auth pages JS */

window.PX = window.PX || {};

PX.getTenantSlug = function () {
  /* Tenant slug from URL: /{slug}/... or null on platform pages */
  var reserved = ["docs","redoc","static","health","auth","tenants","services",
    "bookings","orders","payments","rewards","referrals","notifications",
    "analytics","platform","businesses","about","contact"];
  var parts = window.location.pathname.split("/").filter(Boolean);
  if (parts.length && reserved.indexOf(parts[0]) === -1) return parts[0];
  return null;
};

PX.apiHeaders = function () {
  var h = { "Content-Type": "application/json" };
  var slug = PX.getTenantSlug();
  if (slug) h["X-Tenant-Slug"] = slug;
  else h["X-Tenant-Slug"] = "trianon-hotel"; // dev fallback: pick a live tenant
  return h;
};

PX.showAlert = function (message, kind) {
  var box = document.getElementById("alert-box");
  if (!box) return;
  box.className = "alert alert-" + (kind || "error");
  box.textContent = message;
  box.style.display = "block";
  box.style.marginBottom = "var(--space-5)";
};

PX.hideAlert = function () {
  var box = document.getElementById("alert-box");
  if (box) box.style.display = "none";
};

PX.saveToken = function (token) {
  try { localStorage.setItem("px_token", token); } catch (e) {}
};

PX.initLogin = function () {
  var form = document.getElementById("login-form");
  if (!form) return;
  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    PX.hideAlert();
    var email = form.email.value.trim();
    var password = form.password.value;
    try {
      var res = await fetch("/auth/login", {
        method: "POST",
        headers: PX.apiHeaders(),
        body: JSON.stringify({ email: email, password: password }),
      });
      var data = await res.json();
      if (!res.ok) {
        PX.showAlert(data.detail || "Login failed");
        return;
      }
      PX.saveToken(data.access_token);
      var slug = PX.getTenantSlug();
      window.location.href = slug ? "/" + slug + "/" : "/businesses";
    } catch (err) {
      PX.showAlert("Network error. Try again.");
    }
  });
};

PX.initRegister = function () {
  var form = document.getElementById("register-form");
  if (!form) return;
  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    PX.hideAlert();
    var payload = {
      email: form.email.value.trim(),
      password: form.password.value,
      first_name: form.first_name.value.trim(),
      last_name: form.last_name.value.trim(),
    };
    try {
      var res = await fetch("/auth/register", {
        method: "POST",
        headers: PX.apiHeaders(),
        body: JSON.stringify(payload),
      });
      var data = await res.json();
      if (!res.ok) {
        var msg = data.detail;
        if (Array.isArray(msg)) msg = msg.map(function (e) { return e.msg; }).join(", ");
        PX.showAlert(msg || "Registration failed");
        return;
      }
      PX.saveToken(data.access_token);
      var slug = PX.getTenantSlug();
      window.location.href = slug ? "/" + slug + "/" : "/businesses";
    } catch (err) {
      PX.showAlert("Network error. Try again.");
    }
  });
};
