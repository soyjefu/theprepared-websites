// 공감 버튼 AJAX 토글 — 페이지 새로고침 없이 상태 전환
(function () {
  function init() {
    document.querySelectorAll("form[data-like-form]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        const btn = form.querySelector(".like-btn");
        if (!btn) return;
        const csrfInput = form.querySelector("[name=csrfmiddlewaretoken]");
        const csrf = csrfInput ? csrfInput.value : "";
        btn.disabled = true;
        fetch(form.action, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrf,
            "X-Requested-With": "fetch",
            "Accept": "application/json",
          },
          credentials: "same-origin",
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data || data.error) return;
            btn.classList.toggle("is-liked", !!data.liked);
            btn.setAttribute("aria-pressed", data.liked ? "true" : "false");
            const c = btn.querySelector(".like-count");
            if (c) c.textContent = data.count;
          })
          .catch(function () { /* 실패는 조용히 무시 */ })
          .finally(function () { btn.disabled = false; });
      });
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  window.addEventListener("spa:after-swap", init);
})();
