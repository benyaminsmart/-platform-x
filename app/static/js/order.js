/* Platform-X — Restaurant order (menu + cart) */

window.PX = window.PX || {};

PX.initOrder = function (slug) {
  var section = document.querySelector(".px-order");
  if (!section) return;

  var cart = {}; // {service_id: {name, price, currency, qty}}
  var cartItemsEl = document.getElementById("cart-items");
  var cartCountEl = document.getElementById("cart-count");
  var cartTotalEl = document.getElementById("cart-total");
  var checkoutBtn = document.getElementById("checkout-btn");

  function fmt(amount, currency) {
    return Number(amount).toFixed(2) + " " + currency;
  }

  function updateCart() {
    var ids = Object.keys(cart);
    var count = 0;
    var total = 0;
    var currency = "AED";

    ids.forEach(function (id) {
      var item = cart[id];
      count += item.qty;
      total += item.qty * parseFloat(item.price);
      currency = item.currency;
    });

    cartCountEl.textContent = count;
    cartTotalEl.textContent = fmt(total, currency);
    checkoutBtn.disabled = count === 0;

    if (!ids.length) {
      cartItemsEl.innerHTML = '<p class="px-muted text-center" style="padding: 24px 0;">Your cart is empty.</p>';
      return;
    }

    var html = "";
    ids.forEach(function (id) {
      var item = cart[id];
      html += '<div class="px-cart-item" data-id="' + id + '">' +
        '<div class="px-cart-item-main">' +
        '<div class="px-cart-item-name">' + PX.esc(item.name) + '</div>' +
        '<div class="px-cart-item-price">' + fmt(item.price, item.currency) + '</div>' +
        '</div>' +
        '<div class="px-cart-item-controls">' +
        '<button type="button" class="px-qty-btn" data-action="dec" data-id="' + id + '">−</button>' +
        '<span class="px-qty-value">' + item.qty + '</span>' +
        '<button type="button" class="px-qty-btn" data-action="inc" data-id="' + id + '">+</button>' +
        '</div>' +
        '</div>';
    });
    cartItemsEl.innerHTML = html;

    cartItemsEl.querySelectorAll(".px-qty-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        var action = btn.getAttribute("data-action");
        if (!cart[id]) return;
        if (action === "inc") cart[id].qty += 1;
        else cart[id].qty -= 1;
        if (cart[id].qty <= 0) delete cart[id];
        updateCart();
      });
    });
  }

  function addToCart(id, name, price, currency) {
    if (cart[id]) cart[id].qty += 1;
    else cart[id] = { name: name, price: price, currency: currency, qty: 1 };
    updateCart();
  }

  document.querySelectorAll("[data-add]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var card = btn.closest(".px-menu-card");
      if (!card) return;
      addToCart(
        card.getAttribute("data-service-id"),
        card.getAttribute("data-name"),
        card.getAttribute("data-price"),
        card.getAttribute("data-currency")
      );
      btn.textContent = "Added ✓";
      btn.classList.add("is-added");
      setTimeout(function () {
        btn.textContent = "Add";
        btn.classList.remove("is-added");
      }, 900);
    });
  });

  // Checkout: create one order per cart item (simple approach for demo)
  checkoutBtn.addEventListener("click", async function () {
    var token = PX.getToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    var ids = Object.keys(cart);
    if (!ids.length) return;

    checkoutBtn.disabled = true;
    checkoutBtn.textContent = "Creating order…";

    var headers = PX.authHeaders(slug);
    var created = [];

    try {
      for (var i = 0; i < ids.length; i++) {
        var id = ids[i];
        var item = cart[id];
        var subtotal = (parseFloat(item.price) * item.qty).toFixed(2);
        var payload = {
          service_type: "dining",
          service_name: item.name + (item.qty > 1 ? " ×" + item.qty : ""),
          quantity: item.qty,
          amount: subtotal,
          currency: item.currency,
          notes: null,
        };
        var res = await fetch("/orders", {
          method: "POST",
          headers: headers,
          body: JSON.stringify(payload),
        });
        var data = await res.json();
        if (!res.ok) {
          var msg = data.detail;
          if (Array.isArray(msg)) msg = msg.map(function (e) { return e.msg; }).join(", ");
          PX.showAlert(msg || "Order failed");
          checkoutBtn.disabled = false;
          checkoutBtn.textContent = "Proceed to checkout";
          return;
        }
        created.push(data.id);
      }

      // For demo: pay the first order and redirect to /account
      if (created.length) {
        var firstId = created[0];
        // Get the order amount
        var orderRes = await fetch("/orders/" + firstId, { headers: headers });
        var order = await orderRes.json();
        var intentRes = await fetch("/payments/intent", {
          method: "POST",
          headers: headers,
          body: JSON.stringify({
            order_id: firstId,
            amount: order.amount,
            currency: order.currency,
            method: "card",
          }),
        });
        var intent = await intentRes.json();
        if (intentRes.ok && intent.redirect_url) {
          await fetch(intent.redirect_url);
        }
      }

      window.location.href = "/account";
    } catch (err) {
      PX.showAlert("Network error. Please try again.");
      checkoutBtn.disabled = false;
      checkoutBtn.textContent = "Proceed to checkout";
    }
  });

  updateCart();
};
