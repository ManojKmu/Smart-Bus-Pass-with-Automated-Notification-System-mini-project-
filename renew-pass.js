document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('renewForm');
    const submitBtn = document.querySelector('.submit-btn');
    const emailInput = document.getElementById('email');

    form.addEventListener('submit', function(e) {
        const email = emailInput.value.trim();
        
        if (!email) {
            e.preventDefault();
            alert('Please enter your email address');
            return;
        }

        if (!isValidEmail(email)) {
            e.preventDefault();
            alert('Please enter a valid email address');
            return;
        }

        // Show loading state
        submitBtn.textContent = 'Sending OTP...';
        submitBtn.disabled = true;
        form.classList.add('loading');
    });

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Auto-focus on email input
    emailInput.focus();
});