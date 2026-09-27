/* Platform-X — Booking form */

window.PX = window.PX || {};

PX.getToken = function () {
  try { return localStorage.getItem("px_token"); } catch (e) { return null; }
};

PX.authHeaders = function (slug) {
  var h = { "Content-Type": "application/json" };
  if (slug) h["X-Tenant-Slug"] = slug;
  var t = PX.getToken();
  if (t) h["Authorization"] = "Bearer " + t;
  return h;
};

PX.initBooking = function (slug) {
  var form = document.getElementById("booking-form");
  if (!form) return;

  var select = document.getElementById("service_id");
  var totalDisplay = document.getElementById("total-display");

  function refreshTotal() {
    var opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) {
      totalDisplay.textContent = "—";
      return;
    }
    var price = opt.getAttribute("data-price");
    var cur = opt.getAttribute("data-currency");
    totalDisplay.textContent = price + " " + cur;
  }

  select.addEventListener("change", refreshTotal);
  refreshTotal();

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();

    var token = PX.getToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    var opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) {
      PX.showAlert("Please choose a service");
      return;
    }

    var payload = {
      booking_type: "room",
      service_id: opt.value,
      service_name: opt.getAttribute("data-name"),
      check_in: form.check_in.value,
      check_out: form.check_out.value || null,
      guests: parseInt(form.guests.value, 10) || 1,
      amount: opt.getAttribute("data-price"),
      currency: opt.getAttribute("data-currency"),
      notes: form.notes.value || null,
    };

    try {
      var res = await fetch("/bookings", {
        method: "POST",
        headers: PX.authHeaders(slug),
        body: JSON.stringify(payload),
      });
      var data = await res.json();
      if (!res.ok) {
        var msg = data.detail;
        if (Array.isArray(msg)) msg = msg.map(function (e) { return e.msg; }).join(", ");
        PX.showAlert(msg || "Booking failed");
        return;
      }
      window.location.href = "/" + slug + "/pay?booking=" + data.id;
    } catch (err) {
      PX.showAlert("Network error. Try again.");
    }
  });
};
