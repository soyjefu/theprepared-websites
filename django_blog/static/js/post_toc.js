// 글 본문에 h2/h3가 3개 이상이면 자동 목차(TOC)를 본문 상단에 삽입.
(function () {
  function slugify(text) {
    return text.toLowerCase()
      .replace(/[\s\W-]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'h';
  }

  function init() {
    var body = document.querySelector('.post-body');
    if (!body) return;
    var headings = body.querySelectorAll('h2, h3');
    if (headings.length < 3) return;

    var used = Object.create(null);
    var items = [];
    headings.forEach(function (h, idx) {
      var id = h.id;
      if (!id) {
        var base = slugify(h.textContent);
        id = base;
        var n = 1;
        while (used[id]) { id = base + '-' + (++n); }
        h.id = id;
      }
      used[id] = true;
      items.push({ tag: h.tagName.toLowerCase(), text: h.textContent, id: id });
    });

    var toc = document.createElement('details');
    toc.className = 'post-toc';
    toc.open = true;
    var lines = items.map(function (it) {
      return '<li class="post-toc__item post-toc__item--' + it.tag + '">' +
             '<a href="#' + it.id + '">' + it.text.replace(/</g, '&lt;') + '</a></li>';
    }).join('');
    toc.innerHTML =
      '<summary class="post-toc__title">목차 <span class="post-toc__count">(' + items.length + ')</span></summary>' +
      '<ol class="post-toc__list">' + lines + '</ol>';

    body.insertBefore(toc, body.firstChild);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  window.addEventListener('spa:after-swap', init);
})();
