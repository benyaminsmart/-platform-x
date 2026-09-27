/* Platform-X — Payment page */

window.PX = window.PX || {};

PX.initPayment = function (slug, bookingId) {
  var alertBox = document.getElementById("alert-box");
  var loadingPanel = document.getElementById("loading");
  var paymentPanel = document.getElementById("payment-panel");
  var successPanel = document.getElementById("success-panel");
  var summaryTotal = document.getElementById("summary-total");

  function showAlert(msg) {
    if (!alertBox) { alert(msg); return; }
    alertBox.className = "alert alert-error";
    alertBox.textContent = msg;
    alertBox.style.display = "block";
    alertBox.style.padding = "12px 16px";
    alertBox.style.borderRadius = "var(--px-radius)";
    alertBox.style.background = "var(--px-error-soft)";
    alertBox.style.color = "var(--px-error)";
    alertBox.style.border = "1px solid rgba(229, 62, 62, 0.3)";
    alertBox.style.marginBottom = "20px";
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  if (!bookingId) {
    loadingPanel.style.display = "none";
    showAlert("No booking specified.");
    return;
  }

  var token = PX.getToken();
  if (!token) {
    loadingPanel.style.display = "none";
    showAlert("Please sign in to continue.");
    return;
  }

  var headers = PX.authHeaders(slug);

  // 1. Fetch user info and populate "Your details"
  fetch("/auth/me", { headers: headers })
    .then(function (r) {
      if (!r.ok) return null;
      return r.json();
    })
    .then(function (u) {
      if (!u) return;
      var nameEl = document.getElementById("user-name");
      var emailEl = document.getElementById("user-email");
      var phoneEl = document.getElementById("user-phone");
      if (nameEl) nameEl.textContent = ((u.first_name || "") + " " + (u.last_name || "")).trim() || "—";
      if (emailEl) emailEl.textContent = u.email || "—";
      if (phoneEl) phoneEl.textContent = u.phone || "Not provided";
    })
    .catch(function () {});

  // 2. Fetch booking details
  fetch("/bookings/" + bookingId, { headers: headers })
    .then(function (res) {
      if (!res.ok) throw new Error("Cannot load booking");
      return res.json();
    })
    .then(function (b) {
      loadingPanel.style.display = "none";
      paymentPanel.style.display = "block";
      document.getElementById("booking-service").textContent = b.service_name;
      document.getElementById("booking-checkin").textContent = b.check_in;
      document.getElementById("booking-checkout").textContent = b.check_out || "—";
      document.getElementById("booking-guests").textContent = b.guests;
      summaryTotal.textContent = b.total_amount + " " + b.currency;

      if (b.payment_status === "paid") {
        paymentPanel.style.display = "none";
        successPanel.style.display = "block";
        return;
      }

      document.getElementById("pay-button").addEventListener("click", function () {
        doPay(b);
      });
    })
    .catch(function (err) {
      loadingPanel.style.display = "none";
      showAlert(err.message || "Failed to load booking");
    });

  async function doPay(booking) {
    var methodEl = document.querySelector('input[name="method"]:checked');
    var method = methodEl ? methodEl.value : "card";
    var payBtn = document.getElementById("pay-button");
    payBtn.disabled = true;
    payBtn.textContent = "Processing…";

    try {
      var intentRes = await fetch("/payments/intent", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          booking_id: booking.id,
          amount: booking.total_amount,
          currency: booking.currency,
          method: method,
        }),
      });
      var intent = await intentRes.json();
      if (!intentRes.ok) throw new Error(intent.detail || "Payment intent failed");

      var confirmRes = await fetch(intent.redirect_url);
      if (!confirmRes.ok) throw new Error("Mock confirm failed");

      paymentPanel.style.display = "none";
      successPanel.style.display = "block";
    } catch (err) {
      payBtn.disabled = false;
      payBtn.textContent = "Pay now";
      showAlert(err.message || "Payment failed");
    }
  }
};
