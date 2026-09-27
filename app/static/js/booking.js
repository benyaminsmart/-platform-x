/* Platform-X — Booking form (dynamic by business type) */

window.PX = window.PX || {};

PX.bookingTypeFor = function () {
  var el = document.querySelector("[data-tenant-type]");
  var t = el ? (el.getAttribute("data-tenant-type") || "").toLowerCase() : "hotel";
  if (t === "hotel") return "room";
  if (t === "restaurant") return "table";
  if (t === "travel_agency") return "package";
  if (t === "entertainment") return "event";
  return "room";
};

PX.initBooking = function (slug) {
  var form = document.getElementById("booking-form");
  if (!form) return;

  var select = document.getElementById("service_id");
  var totalDisplay = document.getElementById("summary-total");
  var serviceDisplay = document.getElementById("summary-service");
  var guestsDisplay = document.getElementById("summary-guests");
  var datesDisplay = document.getElementById("summary-dates");
  var guestsLabel = document.getElementById("summary-guests-label");
  var datesLabel = document.getElementById("summary-dates-label");
  var tenantType = form.closest("[data-tenant-type]").getAttribute("data-tenant-type") || "hotel";

  // Adjust label per type
  if (tenantType === "restaurant") {
    guestsLabel.textContent = "Guests";
    datesLabel.textContent = "When";
  } else if (tenantType === "travel_agency") {
    guestsLabel.textContent = "Passengers";
    datesLabel.textContent = "Departure";
  } else if (tenantType === "entertainment") {
    guestsLabel.textContent = "Tickets";
    datesLabel.textContent = "Visit";
  }

  function refreshSummary() {
    var opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) {
      totalDisplay.textContent = "—";
      serviceDisplay.textContent = "—";
    } else {
      totalDisplay.textContent = opt.getAttribute("data-price") + " " + opt.getAttribute("data-currency");
      serviceDisplay.textContent = opt.getAttribute("data-name");
    }

    if (form.guests) guestsDisplay.textContent = form.guests.value || "1";

    var ci = form.check_in ? form.check_in.value : "";
    var co = form.check_out ? form.check_out.value : "";
    var tm = form.booking_time ? form.booking_time.value : "";

    if ((tenantType === "restaurant" || tenantType === "entertainment") && ci && tm) {
      datesDisplay.textContent = ci + " @ " + tm;
    } else if (ci && co) {
      datesDisplay.textContent = ci + " → " + co;
    } else if (ci) {
      datesDisplay.textContent = ci;
    } else {
      datesDisplay.textContent = "—";
    }
  }

  select.addEventListener("change", refreshSummary);
  if (form.guests) form.guests.addEventListener("input", refreshSummary);
  if (form.check_in) form.check_in.addEventListener("change", refreshSummary);
  if (form.check_out) form.check_out.addEventListener("change", refreshSummary);
  if (form.booking_time) form.booking_time.addEventListener("change", refreshSummary);
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
      PX.showAlert("Please choose an option");
      return;
    }

    var notes = form.notes.value || "";
    if (form.booking_time && form.booking_time.value) {
      notes = "Time: " + form.booking_time.value + (notes ? "\n" + notes : "");
    }

    var payload = {
      booking_type: PX.bookingTypeFor(),
      service_id: opt.value,
      service_name: opt.getAttribute("data-name"),
      check_in: form.check_in.value,
      check_out: form.check_out && form.check_out.value ? form.check_out.value : null,
      guests: form.guests ? parseInt(form.guests.value, 10) || 1 : 1,
      amount: opt.getAttribute("data-price"),
      currency: opt.getAttribute("data-currency"),
      notes: notes || null,
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
