/* Step-by-step exam cards. Without JS every question is shown at once and the form still submits. */
(function () {
  const form = document.getElementById('exam-form');
  if (!form) return;
  document.documentElement.classList.add('js');
  const steps = Array.from(form.querySelectorAll('.q-step'));
  const bar = document.getElementById('exam-bar');
  const label = document.getElementById('exam-step-label');
  const back = document.getElementById('btn-back');
  const next = document.getElementById('btn-next');
  const submit = document.getElementById('btn-submit');
  let i = 0;

  const answered = () => !!steps[i].querySelector('input:checked');
  function show(n) {
    i = Math.max(0, Math.min(steps.length - 1, n));
    steps.forEach((s, k) => s.classList.toggle('is-active', k === i));
    label.textContent = 'Question ' + (i + 1) + ' of ' + steps.length;
    bar.style.width = ((i + 1) / steps.length * 100) + '%';
    back.hidden = i === 0;
    const last = i === steps.length - 1;
    next.hidden = last; submit.hidden = !last;
    refresh();
    const first = steps[i].querySelector('input'); if (first && !answered()) first.focus({preventScroll: true});
  }
  function refresh() { next.disabled = !answered(); submit.disabled = !answered(); }

  form.addEventListener('change', refresh);
  next.addEventListener('click', () => answered() && show(i + 1));
  back.addEventListener('click', () => show(i - 1));
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' && e.target.type !== 'radio') return;
    const n = parseInt(e.key, 10), opts = steps[i].querySelectorAll('input');
    if (n >= 1 && n <= opts.length) { opts[n - 1].checked = true; refresh(); }
  });
  form.addEventListener('submit', e => {
    const missing = steps.findIndex(s => !s.querySelector('input:checked'));
    if (missing !== -1) { e.preventDefault(); show(missing); }
  });
  show(0);
})();
