// Modified from the color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
// Copyright 2011-2024 The Bootstrap Authors
// Licensed under the Creative Commons Attribution 3.0 Unported License.
function setTheme() {
  document.documentElement.setAttribute('data-bs-theme',
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
  );
}
setTheme();
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', setTheme);
