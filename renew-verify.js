document.addEventListener('DOMContentLoaded', function() {
    const otpInputs = document.querySelectorAll('.otp-input');
    const form = document.getElementById('verifyForm');
    const submitBtn = document.querySelector('.submit-btn');
    const otpValue = document.getElementById('otpValue');
    const resendBtn = document.querySelector('.resend-btn');

    // Get email from URL or form
    const urlParams = new URLSearchParams(window.location.search);
    const email = urlParams.get('email') || document.querySelector('input[name="email"]').value;

    // Auto-focus first input
    otpInputs[0].focus();

    // Handle OTP input
    otpInputs.forEach((input, index) => {
        input.addEventListener('input', function(e) {
            const value = e.target.value;
            
            // Only allow numbers
            if (!/^\d$/.test(value)) {
                e.target.value = '';
                return;
            }

            // Add filled class
            e.target.classList.add('filled');

            // Move to next input
            if (value && index < otpInputs.length - 1) {
                otpInputs[index + 1].focus();
            }

            // Update hidden input and check if complete
            updateOTPValue();
        });

        input.addEventListener('keydown', function(e) {
            // Handle backspace
            if (e.key === 'Backspace' && !e.target.value && index > 0) {
                otpInputs[index - 1].focus();
                otpInputs[index - 1].classList.remove('filled');
            }
        });

        input.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedData = e.clipboardData.getData('text');
            const digits = pastedData.replace(/\D/g, '').slice(0, 6);
            
            digits.split('').forEach((digit, i) => {
                if (otpInputs[i]) {
                    otpInputs[i].value = digit;
                    otpInputs[i].classList.add('filled');
                }
            });
            
            updateOTPValue();
            
            // Focus last filled input or next empty
            const lastIndex = Math.min(digits.length - 1, otpInputs.length - 1);
            otpInputs[lastIndex].focus();
        });
    });

    function updateOTPValue() {
        const otp = Array.from(otpInputs).map(input => input.value).join('').trim();
        if (otpValue) otpValue.value = otp;
        
        console.log('Current OTP entered:', otp, 'Length:', otp.length);
        
        // Enable submit button if OTP is complete
        if (otp.length === 6) {
            submitBtn.disabled = false;
        } else {
            submitBtn.disabled = true;
        }
    }

    // Handle form submission
    if (form) {
        form.addEventListener('submit', function(e) {
            const enteredOTP = Array.from(otpInputs).map(input => input.value).join('').trim();
            
            if (enteredOTP.length !== 6) {
                e.preventDefault();
                showError('Please enter the complete 6-digit OTP');
                return;
            }

            // Update the hidden OTP field and let the form submit to server
            if (otpValue) {
                otpValue.value = enteredOTP;
            }
            
            // Show loading state
            submitBtn.textContent = 'Verifying...';
            submitBtn.disabled = true;
            
            // Let the form submit naturally to the server
            // Don't prevent default - let it go to /verify-renew-otp
        });
    }

    // Resend OTP functionality
    let resendTimer = 0;
    
    function startResendTimer() {
        resendTimer = 30;
        if (resendBtn) {
            resendBtn.disabled = true;
            
            const interval = setInterval(() => {
                resendBtn.textContent = `Resend OTP (${resendTimer}s)`;
                resendTimer--;
                
                if (resendTimer < 0) {
                    clearInterval(interval);
                    resendBtn.disabled = false;
                    resendBtn.textContent = 'Resend OTP';
                }
            }, 1000);
        }
    }

    // Start timer on page load
    startResendTimer();

    function showError(message) {
        let errorDiv = document.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            if (form) form.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }

    // Initialize submit button state
    updateOTPValue();
});

function resendOTP(email) {
    const resendBtn = document.querySelector('.resend-btn');
    
    if (resendBtn && resendBtn.disabled) return;
    
    if (resendBtn) {
        resendBtn.textContent = 'Sending...';
        resendBtn.disabled = true;
    }
    
    console.log('Resending OTP to:', email);
    
    // Make AJAX request to resend OTP
    fetch('/resend-renew-otp', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({email: email})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            let successDiv = document.querySelector('.success-message');
            if (!successDiv) {
                successDiv = document.createElement('div');
                successDiv.className = 'success-message';
                document.querySelector('.form-box').appendChild(successDiv);
            }
            successDiv.textContent = 'OTP sent successfully!';
            successDiv.style.display = 'block';
            
            setTimeout(() => {
                successDiv.style.display = 'none';
            }, 3000);
            
            // Restart timer
            startResendTimer();
        } else {
            throw new Error(data.error || 'Failed to send OTP');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        
        // Show error message
        let errorDiv = document.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            document.querySelector('.form-box').appendChild(errorDiv);
        }
        errorDiv.textContent = 'Failed to resend OTP. Please try again.';
        errorDiv.style.display = 'block';
        
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
        
        if (resendBtn) {
            resendBtn.textContent = 'Resend OTP';
            resendBtn.disabled = false;
        }
    });
}