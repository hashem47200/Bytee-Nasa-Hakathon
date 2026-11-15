(function () {
  const copy = document.getElementById('copy-link');
  if (copy) copy.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(copy.dataset.url); copy.textContent = 'Link copied ✓'; }
    catch (e) { window.prompt('Copy this link:', copy.dataset.url); }
  });
  document.querySelectorAll('[data-print]').forEach(b => b.addEventListener('click', () => window.print()));
  if (document.body.dataset.autoPrint === '1') window.addEventListener('load', () => setTimeout(() => window.print(), 400));
})();
