function show_NGAS() {
    document.getElementById('NGAS').style.display = 'flex';
}
function hide_NGAS() {
    document.getElementById('NGAS').style.display = 'none';
}

document.getElementById('ngas_form').addEventListener('submit', function (event) {
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