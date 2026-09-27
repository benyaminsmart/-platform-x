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
      // Aggregate all cart items into ONE order
      var total = 0;
      var currency = "AED";
      var lines = [];
      var totalQty = 0;

      ids.forEach(function (id) {
        var item = cart[id];
        var subtotal = parseFloat(item.price) * item.qty;
        total += subtotal;
        totalQty += item.qty;
        currency = item.currency;
        lines.push(item.qty + "× " + item.name);
      });

      var payload = {
        service_type: "dining",
        service_name: totalQty + " item" + (totalQty > 1 ? "s" : "") + " order",
        quantity: totalQty,
        amount: total.toFixed(2),
        currency: currency,
        notes: lines.join(", "),
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

      // Redirect to order payment page
      window.location.href = "/" + slug + "/pay/order?order=" + data.id;
    } catch (err) {
      PX.showAlert("Network error. Please try again.");
      checkoutBtn.disabled = false;
      checkoutBtn.textContent = "Proceed to checkout";
    }
  });

  updateCart();
};
