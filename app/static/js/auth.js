/* Platform-X — Auth pages JS (login + register handlers only)
   Shared utilities live in px-core.js */

window.PX = window.PX || {};

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

    var password = form.password.value;
    var confirm = form.confirm_password.value;

    if (password !== confirm) {
      PX.showAlert("Passwords do not match.");
      return;
    }

    var payload = {
      email: form.email.value.trim(),
      password: password,
      first_name: form.first_name.value.trim(),
      last_name: form.last_name.value.trim(),
      phone: form.phone.value.trim() || null,
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
