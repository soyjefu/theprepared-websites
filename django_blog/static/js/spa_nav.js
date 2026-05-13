// SPA 페이지네이션 — 페이지네이션 링크 클릭 시 main 영역만 교체.
// 스크롤 위치 유지, 깜빡임 제거, View Transitions API로 부드러운 fade.
// 다른 링크(글 카드 등)는 일반 navigation 유지.
(function () {
  if (window.__spaNavInit) return;
  window.__spaNavInit = true;

  const PAGER_SELECTOR = ".pagination a, .section-pager a";
  const REGION = "main";

  function swap(href) {
    return fetch(href, {
      headers: { "X-Spa-Nav": "1", Accept: "text/html" },
      credentials: "same-origin",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then(function (html) {
        const doc = new DOMParser().parseFromString(html, "text/html");
        const newMain = doc.querySelector(REGION);
        const curMain = document.querySelector(REGION);
        if (!newMain || !curMain) {
          window.location.href = href;
          return;
        }
        const apply = function () {
          curMain.replaceWith(newMain);
          if (doc.title) document.title = doc.title;
          history.pushState({ spa: true }, "", href);
          // 다른 스크립트들이 새 DOM에 이벤트 재attach할 수 있도록 알림
          window.dispatchEvent(new CustomEvent("spa:after-swap"));
        };
        if (document.startViewTransition) {
          document.startViewTransition(apply);
        } else {
          apply();
        }
      })
      .catch(function () {
        // 실패 시 일반 navigation으로 폴백
        window.location.href = href;
      });
  }

  document.addEventListener("click", function (e) {
    const a = e.target.closest(PAGER_SELECTOR);
    if (!a) return;
    // 새 탭 / 외부 / 수정자 키는 무시
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target === "_blank") return;
    if (!a.href) return;
    try {
      const url = new URL(a.href);
      if (url.origin !== window.location.origin) return;
    } catch (_) { return; }
    e.preventDefault();
    swap(a.href);
  });

  window.addEventListener("popstate", function () {
    swap(window.location.href);
  });
})();
