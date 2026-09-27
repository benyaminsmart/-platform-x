/* Platform-X — Order payment page */

window.PX = window.PX || {};

PX.initPaymentOrder = function (slug, orderId) {
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

  if (!orderId) {
    loadingPanel.style.display = "none";
    showAlert("No order specified.");
    return;
  }

  var token = PX.getToken();
  if (!token) {
    loadingPanel.style.display = "none";
    showAlert("Please sign in to continue.");
    return;
  }

  var headers = PX.authHeaders(slug);

  // User details
  fetch("/auth/me", { headers: headers })
    .then(function (r) { return r.ok ? r.json() : null; })
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

  // Order details
  fetch("/orders/" + orderId, { headers: headers })
    .then(function (res) {
      if (!res.ok) throw new Error("Cannot load order");
      return res.json();
    })
    .then(function (o) {
      loadingPanel.style.display = "none";
      paymentPanel.style.display = "block";
      document.getElementById("order-name").textContent = o.service_name;
      document.getElementById("order-qty").textContent = o.quantity;
      document.getElementById("order-notes").textContent = o.notes || "—";
      summaryTotal.textContent = o.amount + " " + o.currency;

      if (o.payment_status === "paid") {
        paymentPanel.style.display = "none";
        successPanel.style.display = "block";
        return;
      }

      document.getElementById("pay-button").addEventListener("click", function () {
        doPay(o);
      });
    })
    .catch(function (err) {
      loadingPanel.style.display = "none";
      showAlert(err.message || "Failed to load order");
    });

  async function doPay(order) {
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
          order_id: order.id,
          amount: order.amount,
          currency: order.currency,
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
