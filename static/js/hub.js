/* Instant client-side category filtering for the hub. Shareable via #mars, #moon, #space ... */
(function () {
  const tabs = Array.from(document.querySelectorAll('[data-filter]'));
  const cards = Array.from(document.querySelectorAll('[data-category]'));
  const blurb = document.getElementById('blurb');
  if (!tabs.length) return;
  function apply(slug) {
    tabs.forEach(t => t.setAttribute('aria-selected', String(t.dataset.filter === slug)));
    cards.forEach(c => { c.hidden = slug !== 'all' && c.dataset.category !== slug; });
    const active = tabs.find(t => t.dataset.filter === slug);
    if (blurb && active) blurb.textContent = active.dataset.desc || '';
  }
  tabs.forEach(t => t.addEventListener('click', () => {
    apply(t.dataset.filter);
    history.replaceState(null, '', t.dataset.filter === 'all' ? location.pathname : '#' + t.dataset.filter);
  }));
  const start = location.hash.slice(1);
  apply(tabs.some(t => t.dataset.filter === start) ? start : 'all');
})();
