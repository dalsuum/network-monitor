(function() {
  const root = document.documentElement;
  const storedTheme = localStorage.getItem('theme');
  const preferredDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = storedTheme || (preferredDark ? 'dark' : 'light');
  root.dataset.theme = theme;

  function updateButton() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.textContent = root.dataset.theme === 'dark' ? 'Light Mode' : 'Dark Mode';
  }

  window.toggleTheme = function () {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = nextTheme;
    localStorage.setItem('theme', nextTheme);
    updateButton();
  };

  document.addEventListener('DOMContentLoaded', updateButton);
})();
