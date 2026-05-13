// 글 페이지: 스크롤 진행률 바 + 맨 위로 버튼 (vanilla JS)
(function () {
  function init() {
    // article(post)이 있는 페이지에서만 동작
    const article = document.querySelector("article.post");
    if (!article) return;

    // 진행률 바 삽입
    const bar = document.createElement("div");
    bar.className = "scroll-progress";
    bar.innerHTML = '<div class="scroll-progress__fill"></div>';
    document.body.appendChild(bar);
    const fill = bar.querySelector(".scroll-progress__fill");

    // 맨 위로 버튼 삽입
    const top = document.createElement("button");
    top.className = "top-btn";
    top.type = "button";
    top.setAttribute("aria-label", "맨 위로");
    top.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5l-7 7M12 5l7 7M12 5v14"/></svg>';
    document.body.appendChild(top);

    top.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    let ticking = false;
    function update() {
      ticking = false;
      const rect = article.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      const scrolled = -rect.top;
      let p = total > 0 ? Math.max(0, Math.min(1, scrolled / total)) : 0;
      fill.style.width = (p * 100).toFixed(1) + "%";
      // 200px 이상 스크롤 시 top 버튼 표시
      top.classList.toggle("is-visible", window.scrollY > 200);
    }
    function onScroll() {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    update();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
