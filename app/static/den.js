/* The few behaviours the shell needs. No framework, no build step. */
(function () {
  // Sidebar rail state is applied before paint by the inline script in base.html;
  // this just wires the toggle.
  var toggle = document.querySelector(".holt-sidebar-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var rail = document.body.classList.toggle("is-rail");
      try { localStorage.setItem("den.sidebar", rail ? "rail" : "full"); } catch (e) {}
    });
  }

  // Mobile "More" sheet.
  var more = document.querySelector("[data-more]");
  var sheet = document.querySelector(".holt-sheet");
  if (more && sheet) {
    more.addEventListener("click", function (ev) {
      ev.preventDefault();
      sheet.classList.toggle("is-open");
    });
    document.addEventListener("click", function (ev) {
      if (!sheet.contains(ev.target) && !more.contains(ev.target)) sheet.classList.remove("is-open");
    });
  }

  // Toasts: window.denToast("text", "positive" | "warning")
  window.denToast = function (text, tone) {
    var host = document.querySelector(".holt-toasts");
    if (!host) { host = document.createElement("div"); host.className = "holt-toasts"; document.body.appendChild(host); }
    var el = document.createElement("div");
    el.className = "holt-toast holt-glass-float" + (tone ? " is-" + tone : "");
    el.textContent = text;
    host.appendChild(el);
    setTimeout(function () { el.remove(); }, 4000);
  };

  // Dialogs: any [data-open-dialog="id"] opens <dialog id>, [data-close-dialog] closes its dialog.
  document.addEventListener("click", function (ev) {
    var opener = ev.target.closest("[data-open-dialog]");
    if (opener) { var d = document.getElementById(opener.getAttribute("data-open-dialog")); if (d) { ev.preventDefault(); d.showModal(); } }
    var closer = ev.target.closest("[data-close-dialog]");
    if (closer) { var dd = closer.closest("dialog"); if (dd) { ev.preventDefault(); dd.close(); } }
  });

  // Poster images: drop a broken image so the striped placeholder shows through.
  document.querySelectorAll(".holt-poster img, .holt-thumb img").forEach(function (img) {
    img.addEventListener("error", function () { img.remove(); });
  });
})();
