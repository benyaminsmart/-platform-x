/* Platform-X — Partner application form */

window.PX = window.PX || {};

PX.initPartners = function () {
  var form = document.getElementById("partner-form");
  if (!form) return;

  var typeFields = document.querySelectorAll(".px-type-fields");
  var typeSpecificSection = document.getElementById("type-specific");
  var typeSpecificTitle = document.getElementById("type-specific-title");

  var TYPE_TITLES = {
    hotel: "Hotel details",
    restaurant: "Restaurant details",
    travel_agency: "Agency details",
    entertainment: "Venue details",
  };

  function refreshType() {
    var selected = form.querySelector('input[name="tenant_type"]:checked');
    if (!selected) {
      typeSpecificSection.style.display = "none";
      return;
    }
    var type = selected.value;
    typeSpecificSection.style.display = "block";
    typeSpecificTitle.textContent = TYPE_TITLES[type] || "Specifics";
    typeFields.forEach(function (block) {
      block.style.display = (block.getAttribute("data-type") === type) ? "block" : "none";
    });
  }

  form.querySelectorAll('input[name="tenant_type"]').forEach(function (radio) {
    radio.addEventListener("change", refreshType);
  });

  function collectDetails(type) {
    var details = {};
    var block = form.querySelector('.px-type-fields[data-type="' + type + '"]');
    if (!block) return details;

    var checkboxGroups = {};

    block.querySelectorAll("input, select, textarea").forEach(function (el) {
      var name = el.name;
      if (!name) return;

      if (el.type === "checkbox") {
        var cleanKey = name.replace(/^details_/, "");
        if (!checkboxGroups[cleanKey]) checkboxGroups[cleanKey] = [];
        if (el.checked) checkboxGroups[cleanKey].push(el.value);
        return;
      }

      if (el.value === "") return;

      var cleanName = name.replace(/^details_/, "");
      details[cleanName] = el.value;
    });

    Object.keys(checkboxGroups).forEach(function (k) {
      details[k] = checkboxGroups[k];
    });

    return details;
  }

  function collectLanguages() {
    var langs = [];
    form.querySelectorAll('input[name="languages"]:checked').forEach(function (el) {
      langs.push(el.value);
    });
    return langs;
  }

  function value(name) {
    var el = form.querySelector('[name="' + name + '"]');
    return el && el.value ? el.value.trim() : null;
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    PX.hideAlert();

    var selectedType = form.querySelector('input[name="tenant_type"]:checked');
    if (!selectedType) {
      PX.showAlert("Please choose a business type.");
      return;
    }
    var type = selectedType.value;

    var langs = collectLanguages();
    if (!langs.length) {
      PX.showAlert("Please select at least one language.");
      return;
    }

    var foundedYear = value("founded_year");
    var payload = {
      tenant_type: type,
      contact_name: value("contact_name"),
      contact_role: value("contact_role"),
      email: value("email"),
      phone: value("phone"),
      whatsapp: value("whatsapp"),
      business_name: value("business_name"),
      brand_name: value("brand_name"),
      city: value("city"),
      address: value("address"),
      website: value("website"),
      instagram: value("instagram"),
      founded_year: foundedYear ? parseInt(foundedYear, 10) : null,
      staff_count: value("staff_count"),
      tier_interest: value("tier_interest") || "professional",
      languages: langs,
      about: value("about"),
      motivation: value("motivation"),
      details: collectDetails(type),
    };

    try {
      var res = await fetch("/partners/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      var data = await res.json();
      if (!res.ok) {
        var msg = data.detail;
        if (Array.isArray(msg)) {
          msg = msg.map(function (e) {
            return (e.loc ? e.loc.join(".") + ": " : "") + e.msg;
          }).join(" | ");
        }
        PX.showAlert(typeof msg === "string" ? msg : "Submission failed");
        return;
      }
      window.location.href = "/partners/thanks";
    } catch (err) {
      PX.showAlert("Network error. Please try again.");
    }
  });
};
