function show_NGAS() {
    document.getElementById('NGAS').style.display = 'flex';
}
function hide_NGAS() {
    document.getElementById('NGAS').style.display = 'none';
}

function show_loan_df() {
    const modal = document.getElementById('loan_df');
    if (!modal) return;

    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}
function hide_loan_df() {
    const modal = document.getElementById('loan_df');
    if (!modal) return;

    modal.classList.add('hidden');
    modal.style.display = '';
}

const themeToggle = document.getElementById('theme-toggle');

function setTheme(theme) {
    const isDark = theme === 'dark';
    document.documentElement.classList.toggle('dark', isDark);

    if (themeToggle) {
        const label = isDark ? 'Switch to light theme' : 'Switch to dark theme';
        themeToggle.setAttribute('aria-pressed', String(isDark));
        themeToggle.setAttribute('aria-label', label);
        themeToggle.setAttribute('title', label);
        document.getElementById('theme-toggle-label').textContent = label;
    }
}

if (themeToggle) {
    setTheme(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    themeToggle.addEventListener('click', () => {
        const nextTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        setTheme(nextTheme);

        try {
            localStorage.setItem('portfolio-theme', nextTheme);
        } catch (_) {
            // The switch still works when storage is unavailable.
        }
    });
}

const ngasForm = document.getElementById('ngas_form');

if (ngasForm) ngasForm.addEventListener('submit', function (event) {
    for (let i = 1; i <= 3; i++) {
        const date1 = document.querySelector(`[name="input-date-${i}"]`).value;
        const date2 = document.querySelector(`[name="output-date-${i}"]`).value;

        if (date1 && !date2) {
            event.preventDefault();

            const error = document.getElementById('ngas_input_error');
            error.style.display = 'block';
            error.textContent = 'Withdrawal date is required when an injection date is set. Leave both blank if unused.';

            return false;
        }

        if (!date1 && date2) {
            event.preventDefault();

            const error = document.getElementById('ngas_input_error');
            error.style.display = 'block';
            error.textContent = 'Injection date is required when a withdrawal date is set. Leave both blank if unused.';

            return false;
        }

        if (date1 && date2 && date1 >= date2) {
            event.preventDefault();

            const error = document.getElementById('ngas_input_error');
            error.style.display = 'block';
            error.textContent = 'Injection date must be earlier than withdrawal date for each pair.';

            return false;
        }
    }
    const error = document.getElementById('ngas_input_error');
    error.style.display = 'none';
});
