// 글 본문의 picture[data-full]을 클릭하면 큰 이미지로 lightbox 갤러리.
// vanilla JS, ESC/좌우 화살표/스와이프 지원.
(function () {
  function init() {
    const items = Array.from(document.querySelectorAll("picture[data-full]"));
    if (items.length === 0) return;

    // 오버레이 생성 (lazy)
    let overlay = null;
    let currentIndex = -1;

    function buildOverlay() {
      overlay = document.createElement("div");
      overlay.className = "lightbox";
      overlay.innerHTML = `
        <button class="lightbox__close" aria-label="닫기">×</button>
        <button class="lightbox__prev" aria-label="이전">‹</button>
        <button class="lightbox__next" aria-label="다음">›</button>
        <div class="lightbox__stage"><img class="lightbox__img" alt=""></div>
        <div class="lightbox__caption"></div>
        <div class="lightbox__counter"></div>
      `;
      document.body.appendChild(overlay);
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) close();
      });
      overlay.querySelector(".lightbox__close").addEventListener("click", close);
      overlay.querySelector(".lightbox__prev").addEventListener("click", function (e) { e.stopPropagation(); show(currentIndex - 1); });
      overlay.querySelector(".lightbox__next").addEventListener("click", function (e) { e.stopPropagation(); show(currentIndex + 1); });
      document.addEventListener("keydown", function (e) {
        if (!overlay.classList.contains("is-open")) return;
        if (e.key === "Escape") close();
        else if (e.key === "ArrowLeft") show(currentIndex - 1);
        else if (e.key === "ArrowRight") show(currentIndex + 1);
      });

      // 스와이프
      let startX = 0;
      overlay.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; });
      overlay.addEventListener("touchend", function (e) {
        const dx = e.changedTouches[0].clientX - startX;
        if (Math.abs(dx) > 50) show(currentIndex + (dx < 0 ? 1 : -1));
      });
    }

    function show(i) {
      if (i < 0) i = items.length - 1;
      if (i >= items.length) i = 0;
      currentIndex = i;
      const pic = items[i];
      const img = overlay.querySelector(".lightbox__img");
      img.src = pic.dataset.full;
      img.alt = pic.dataset.alt || "";
      overlay.querySelector(".lightbox__caption").textContent = pic.dataset.alt || "";
      overlay.querySelector(".lightbox__counter").textContent = (i + 1) + " / " + items.length;
      overlay.classList.add("is-open");
      document.body.classList.add("lightbox-open");
    }

    function close() {
      if (!overlay) return;
      overlay.classList.remove("is-open");
      document.body.classList.remove("lightbox-open");
    }

    items.forEach(function (pic, i) {
      pic.style.cursor = "zoom-in";
      pic.addEventListener("click", function (e) {
        e.preventDefault();
        if (!overlay) buildOverlay();
        show(i);
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
