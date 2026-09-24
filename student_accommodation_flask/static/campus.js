(function () {
  function fillUniversities(regionSelect, universitySelect, selected) {
    if (!regionSelect || !universitySelect) return;
    var map = window.UNIVERSITIES_BY_REGION || {};
    var region = regionSelect.value;
    var names = region ? (map[region] || []) : Object.values(map).reduce(function (all, list) {
      return all.concat(list);
    }, []);
    var current = selected || universitySelect.value;
    universitySelect.innerHTML = "";
    var placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = region ? "Select university" : "All universities";
    universitySelect.appendChild(placeholder);
    names.forEach(function (name) {
      var opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      if (name === current) opt.selected = true;
      universitySelect.appendChild(opt);
    });
  }

  function bindPair(regionSelect) {
    var universitySelect = document.querySelector(regionSelect.dataset.universityTarget);
    if (!universitySelect) return;
    var selected = universitySelect.dataset.selected || "";
    fillUniversities(regionSelect, universitySelect, selected);
    regionSelect.addEventListener("change", function () {
      fillUniversities(regionSelect, universitySelect, "");
    });
  }

  document.querySelectorAll("[data-university-target]").forEach(bindPair);

  var toggle = document.querySelector(".nav-toggle");
  var header = document.querySelector(".navbar");
  if (toggle && header) {
    toggle.addEventListener("click", function () {
      var open = header.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
  }

  document.querySelectorAll("input[data-preview]").forEach(function (input) {
    input.addEventListener("change", function () {
      var box = input.closest(".upload-panel");
      var previews = box ? box.querySelector(".upload-previews") : null;
      if (!previews) return;
      previews.innerHTML = "";
      Array.from(input.files || []).forEach(function (file) {
        if (!file.type || file.type.indexOf("image/") !== 0) return;
        var img = document.createElement("img");
        img.alt = file.name;
        img.src = URL.createObjectURL(file);
        previews.appendChild(img);
      });
    });
  });
})();
