/* Platform-X — Payment page */

window.PX = window.PX || {};

PX.initPayment = function (slug, bookingId) {
  var alertBox = document.getElementById("alert-box");
  var loadingPanel = document.getElementById("loading");
  var paymentPanel = document.getElementById("payment-panel");
  var successPanel = document.getElementById("success-panel");

  function showAlert(msg) {
    alertBox.className = "alert alert-error";
    alertBox.textContent = msg;
    alertBox.style.display = "block";
  }

  if (!bookingId) {
    loadingPanel.style.display = "none";
    showAlert("No booking specified.");
    return;
  }

  var headers = PX.authHeaders(slug);

  // 1. Fetch booking details
  fetch("/bookings/" + bookingId, { headers: headers })
    .then(function (res) {
      if (!res.ok) throw new Error("Cannot load booking");
      return res.json();
    })
    .then(function (b) {
      loadingPanel.style.display = "none";
      paymentPanel.style.display = "block";
      document.getElementById("service-name").textContent = b.service_name;
      document.getElementById("check-in").textContent = b.check_in;
      document.getElementById("check-out").textContent = b.check_out || "—";
      document.getElementById("guests").textContent = b.guests;
      document.getElementById("total").textContent = b.total_amount + " " + b.currency;

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
    var method = document.getElementById("method").value;
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

      // Mock confirm: hit the redirect URL directly
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
