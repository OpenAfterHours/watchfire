// watchfire landing — vanilla JS for interactive bits.
//
// The React mock used a <InstallPill> component with state-driven copy
// feedback; this is the same thing without React. One IIFE, runs on DOM
// ready, wires every .install-pill button to its sibling <span.cmd>.

(function () {
  function wireCopyButtons() {
    var buttons = document.querySelectorAll(".watchfire-landing .install-pill .copy-btn");
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var pill = btn.closest(".install-pill");
        if (!pill) return;
        var cmd = pill.querySelector(".cmd");
        if (!cmd) return;
        var text = cmd.textContent.trim();

        var done = function () {
          var original = btn.dataset.originalText || btn.textContent;
          btn.dataset.originalText = original;
          btn.textContent = "COPIED";
          btn.classList.add("copied");
          setTimeout(function () {
            btn.textContent = original;
            btn.classList.remove("copied");
          }, 1400);
        };

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () {});
        } else {
          // Fallback for older browsers.
          var area = document.createElement("textarea");
          area.value = text;
          area.style.position = "fixed";
          area.style.opacity = "0";
          document.body.appendChild(area);
          area.select();
          try { document.execCommand("copy"); done(); } catch (_) {}
          document.body.removeChild(area);
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireCopyButtons);
  } else {
    wireCopyButtons();
  }
})();
