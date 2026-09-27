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



PX.bookingTypeFor = function (slug) {
  /* Map tenant config type to booking_type API value.
     Reads a data attribute set by the tenant template. */
  var el = document.querySelector('[data-tenant-type]');
  var t = el ? (el.getAttribute('data-tenant-type') || '').toLowerCase() : '';
  if (t === 'hotel') return 'room';
  if (t === 'restaurant') return 'table';
  if (t === 'travel_agency') return 'package';
  if (t === 'entertainment') return 'event';
  return 'room';
};

PX.initBooking = function (slug) {
  var form = document.getElementById("booking-form");
  if (!form) return;

  var select = document.getElementById("service_id");
  var totalDisplay = document.getElementById("summary-total");
  var serviceDisplay = document.getElementById("summary-service");
  var guestsDisplay = document.getElementById("summary-guests");
  var datesDisplay = document.getElementById("summary-dates");

  function refreshSummary() {
    var opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) {
      totalDisplay.textContent = "—";
      serviceDisplay.textContent = "—";
    } else {
      totalDisplay.textContent = opt.getAttribute("data-price") + " " + opt.getAttribute("data-currency");
      serviceDisplay.textContent = opt.getAttribute("data-name");
    }

    guestsDisplay.textContent = form.guests.value || "1";

    var ci = form.check_in.value;
    var co = form.check_out.value;
    if (ci && co) datesDisplay.textContent = ci + " → " + co;
    else if (ci) datesDisplay.textContent = ci;
    else datesDisplay.textContent = "—";
  }

  select.addEventListener("change", refreshSummary);
  form.guests.addEventListener("input", refreshSummary);
  form.check_in.addEventListener("change", refreshSummary);
  form.check_out.addEventListener("change", refreshSummary);
  refreshSummary();

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
      booking_type: PX.bookingTypeFor(slug),
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
