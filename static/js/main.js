document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Show flash messages with fade-out effect
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(function(message) {
        // Auto-dismiss flash messages after 5 seconds
        setTimeout(function() {
            const alert = new bootstrap.Alert(message);
            alert.close();
        }, 5000);
    });

    // Add animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(function(card, index) {
        card.classList.add('fade-in');
        card.style.animationDelay = (index * 0.1) + 's';
    });

    // Countdown timer for tender deadlines
    const deadlineElements = document.querySelectorAll('.tender-deadline');
    deadlineElements.forEach(function(element) {
        const deadlineDate = new Date(element.getAttribute('data-deadline'));
        
        // Update the countdown every second
        const countdownInterval = setInterval(function() {
            const now = new Date().getTime();
            const distance = deadlineDate - now;
            
            // Time calculations
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            // Display the result
            if (distance > 0) {
                element.innerHTML = days + "d " + hours + "h " + minutes + "m " + seconds + "s";
                
                // Add color coding for urgency
                if (days < 1) {
                    element.classList.add('text-danger');
                } else if (days < 3) {
                    element.classList.add('text-warning');
                }
            } else {
                clearInterval(countdownInterval);
                element.innerHTML = "EXPIRED";
                element.classList.add('text-danger', 'fw-bold');
            }
        }, 1000);
    });

    // Form validation for tender applications
    const tenderApplicationForm = document.getElementById('tender-application-form');
    if (tenderApplicationForm) {
        tenderApplicationForm.addEventListener('submit', function(event) {
            const proposalField = document.getElementById('proposal');
            const priceQuoteField = document.getElementById('price_quote');
            const completionTimeField = document.getElementById('completion_time');
            
            let isValid = true;
            
            // Simple validation
            if (proposalField.value.trim().length < 50) {
                showFieldError(proposalField, 'Your proposal should be at least 50 characters long');
                isValid = false;
            } else {
                clearFieldError(proposalField);
            }
            
            if (isNaN(priceQuoteField.value) || priceQuoteField.value <= 0) {
                showFieldError(priceQuoteField, 'Please enter a valid positive number');
                isValid = false;
            } else {
                clearFieldError(priceQuoteField);
            }
            
            if (isNaN(completionTimeField.value) || completionTimeField.value <= 0) {
                showFieldError(completionTimeField, 'Please enter a valid positive number of days');
                isValid = false;
            } else {
                clearFieldError(completionTimeField);
            }
            
            if (!isValid) {
                event.preventDefault();
            }
        });
    }
    
    // Helper functions for form validation
    function showFieldError(field, message) {
        field.classList.add('is-invalid');
        
        // Create or update error message
        let errorDiv = field.nextElementSibling;
        if (!errorDiv || !errorDiv.classList.contains('invalid-feedback')) {
            errorDiv = document.createElement('div');
            errorDiv.classList.add('invalid-feedback');
            field.parentNode.insertBefore(errorDiv, field.nextSibling);
        }
        errorDiv.textContent = message;
    }
    
    function clearFieldError(field) {
        field.classList.remove('is-invalid');
        
        // Remove error message if it exists
        const errorDiv = field.nextElementSibling;
        if (errorDiv && errorDiv.classList.contains('invalid-feedback')) {
            errorDiv.textContent = '';
        }
    }

    // Mobile navigation toggle for admin sidebar
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            const sidebar = document.querySelector('.admin-sidebar');
            sidebar.classList.toggle('show');
        });
    }

    // Initialize date-time pickers if present
    const dateTimeInputs = document.querySelectorAll('input[type="datetime-local"]');
    dateTimeInputs.forEach(function(input) {
        // Set min attribute to current date-time
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        
        input.setAttribute('min', `${year}-${month}-${day}T${hours}:${minutes}`);
    });
});

// Function to confirm actions like delete
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to perform this action?');
}
