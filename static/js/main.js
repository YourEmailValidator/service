document.addEventListener('DOMContentLoaded', function() {
    // Initialize FAQ toggles
    document.querySelectorAll('.toggle-faq').forEach(button => {
        button.addEventListener('click', () => {
            const content = button.nextElementSibling;
            content.classList.toggle('hidden');
            
            // Toggle the plus/minus icon
            const icon = button.querySelector('svg');
            if (content.classList.contains('hidden')) {
                icon.innerHTML = '<path d="M12 5v14M5 12h14"></path>';
            } else {
                icon.innerHTML = '<path d="M5 12h14"></path>';
            }
        });
    });

    // Add validation form handler
    const validateForm = document.getElementById('validateEmail');
    if (validateForm) {
        validateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            try {
                const response = await fetch(`/api/validate/${encodeURIComponent(email)}`);
                const result = await response.json();
                document.getElementById('result').textContent = 
                    result.is_valid ? 'Valid email!' : 'Invalid email!';
            } catch (error) {
                console.error('Error:', error);
            }
        });
    }
});