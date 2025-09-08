// Healthcare24/7 - Main JavaScript File

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeFormValidation();
    initializeNotifications();
    initializeSearchFunctionality();
    initializeCartFunctionality();
    initializeDateTimeInputs();
    initializeModalHandlers();
    initializeAutoRefresh();
});

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!validateForm(this)) {
                event.preventDefault();
                event.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'This field is required');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Email validation
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            showFieldError(field, 'Please enter a valid email address');
            isValid = false;
        }
    });
    
    // Phone validation
    const phoneFields = form.querySelectorAll('input[type="tel"]');
    phoneFields.forEach(field => {
        if (field.value && !isValidPhone(field.value)) {
            showFieldError(field, 'Please enter a valid phone number');
            isValid = false;
        }
    });
    
    // Password confirmation
    const passwordField = form.querySelector('input[name="password"]');
    const confirmPasswordField = form.querySelector('input[name="password2"]');
    
    if (passwordField && confirmPasswordField) {
        if (passwordField.value !== confirmPasswordField.value) {
            showFieldError(confirmPasswordField, 'Passwords do not match');
            isValid = false;
        }
    }
    
    return isValid;
}

function showFieldError(field, message) {
    clearFieldError(field);
    
    field.classList.add('is-invalid');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidPhone(phone) {
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    return phoneRegex.test(phone.replace(/[\s\-\(\)]/g, ''));
}

// Notifications and Alerts
function initializeNotifications() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });
    
    // Update notification counts periodically
    if (document.querySelector('[data-user-authenticated="true"]')) {
        updateNotificationCounts();
        setInterval(updateNotificationCounts, 60000); // Update every minute
    }
}

function updateNotificationCounts() {
    // Update unread message count
    fetch('/api/unread-messages-count')
        .then(response => response.json())
        .then(data => {
            const messageCountElements = document.querySelectorAll('.message-count, #message-count');
            messageCountElements.forEach(element => {
                element.textContent = data.count || 0;
                element.style.display = data.count > 0 ? 'inline' : 'none';
            });
        })
        .catch(error => console.log('Error updating message count:', error));
    
    // Update notification count
    fetch('/api/unread-notifications-count')
        .then(response => response.json())
        .then(data => {
            const notificationCountElements = document.querySelectorAll('.notification-count, #notification-count');
            notificationCountElements.forEach(element => {
                element.textContent = data.count || 0;
                element.style.display = data.count > 0 ? 'inline' : 'none';
            });
        })
        .catch(error => console.log('Error updating notification count:', error));
}

function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
    }
    return container;
}

// Search Functionality
function initializeSearchFunctionality() {
    const searchForms = document.querySelectorAll('form[action*="search"]');
    
    searchForms.forEach(form => {
        const searchInput = form.querySelector('input[name="query"]');
        if (searchInput) {
            // Add autocomplete functionality
            addSearchAutocomplete(searchInput);
        }
    });
}

function addSearchAutocomplete(input) {
    let timeout;
    
    input.addEventListener('input', function() {
        clearTimeout(timeout);
        const query = this.value.trim();
        
        if (query.length >= 2) {
            timeout = setTimeout(() => {
                // In a real implementation, you would fetch suggestions from the server
                // For now, we'll just show a loading indicator
                showSearchLoading(input);
            }, 300);
        }
    });
}

function showSearchLoading(input) {
    // Add loading spinner to search input
    if (!input.parentNode.querySelector('.search-loading')) {
        const loadingSpinner = document.createElement('div');
        loadingSpinner.className = 'search-loading position-absolute';
        loadingSpinner.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        loadingSpinner.style.cssText = 'right: 10px; top: 50%; transform: translateY(-50%); z-index: 10;';
        
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(loadingSpinner);
        
        setTimeout(() => {
            loadingSpinner.remove();
        }, 1000);
    }
}

// Cart Functionality
function initializeCartFunctionality() {
    const cartButtons = document.querySelectorAll('[href*="add-to-cart"]');
    
    cartButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            
            const url = this.href;
            
            // Show loading state
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adding...';
            this.disabled = true;
            
            // Simulate adding to cart (in real implementation, this would be a fetch request)
            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-check me-1"></i>Added';
                this.classList.remove('btn-primary');
                this.classList.add('btn-success');
                
                // Update cart count
                updateCartCount();
                
                showToast('Item added to cart successfully!', 'success');
                
                // Reset button after 2 seconds
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('btn-success');
                    this.classList.add('btn-primary');
                    this.disabled = false;
                }, 2000);
            }, 1000);
        });
    });
}

function updateCartCount() {
    const cartCountElements = document.querySelectorAll('#cart-count, .cart-count');
    cartCountElements.forEach(element => {
        const currentCount = parseInt(element.textContent) || 0;
        element.textContent = currentCount + 1;
    });
}

// Date and Time Inputs
function initializeDateTimeInputs() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const datetimeInputs = document.querySelectorAll('input[type="datetime-local"]');
    
    // Set minimum date to today for appointment booking
    const today = new Date().toISOString().split('T')[0];
    dateInputs.forEach(input => {
        if (input.name.includes('appointment') || input.name.includes('booking')) {
            input.min = today;
        }
    });
    
    // Set minimum datetime to now for appointment booking
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    const nowString = now.toISOString().slice(0, 16);
    
    datetimeInputs.forEach(input => {
        if (input.name.includes('appointment') || input.name.includes('booking')) {
            input.min = nowString;
        }
    });
}

// Modal Handlers
function initializeModalHandlers() {
    // Appointment confirmation modal
    const appointmentForms = document.querySelectorAll('form[action*="book-appointment"]');
    appointmentForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const doctorSelect = form.querySelector('select[name="doctor_id"]');
            const dateInput = form.querySelector('input[name="appointment_date"]');
            const reasonInput = form.querySelector('input[name="reason"]');
            
            if (doctorSelect && dateInput && reasonInput) {
                const doctorName = doctorSelect.options[doctorSelect.selectedIndex].text;
                const appointmentDate = new Date(dateInput.value);
                const reason = reasonInput.value;
                
                const confirmMessage = `
                    Confirm appointment booking:
                    
                    Doctor: ${doctorName}
                    Date: ${appointmentDate.toLocaleDateString()}
                    Time: ${appointmentDate.toLocaleTimeString()}
                    Reason: ${reason}
                    Fee: $150.00
                `;
                
                if (!confirm(confirmMessage)) {
                    event.preventDefault();
                }
            }
        });
    });
}

// Auto-refresh functionality for dashboards
function initializeAutoRefresh() {
    // Refresh dashboard data every 5 minutes if on dashboard page
    if (window.location.pathname.includes('dashboard')) {
        setInterval(() => {
            // Refresh notification counts
            updateNotificationCounts();
            
            // Refresh recent appointments and messages (in a real app, this would use AJAX)
            const lastUpdate = document.querySelector('#last-update');
            if (lastUpdate) {
                lastUpdate.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
            }
        }, 300000); // 5 minutes
    }
}

// Utility Functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatDateTime(datetime) {
    return new Date(datetime).toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

// Staff-specific functionality
if (window.location.pathname.includes('staff')) {
    document.addEventListener('DOMContentLoaded', function() {
        initializeStaffFeatures();
    });
}

function initializeStaffFeatures() {
    // Quick appointment status updates
    const statusButtons = document.querySelectorAll('[onclick*="updateAppointmentStatus"]');
    statusButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const onclick = this.getAttribute('onclick');
            const match = onclick.match(/updateAppointmentStatus\((\d+), '(\w+)'\)/);
            
            if (match) {
                const appointmentId = match[1];
                const status = match[2];
                updateAppointmentStatus(appointmentId, status);
            }
        });
    });
    
    // Patient search with live filtering
    const patientSearchInput = document.querySelector('input[name="search"]');
    if (patientSearchInput && window.location.pathname.includes('patients')) {
        let searchTimeout;
        
        patientSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            searchTimeout = setTimeout(() => {
                if (query.length >= 2 || query.length === 0) {
                    // Submit the form automatically
                    this.form.submit();
                }
            }, 500);
        });
    }
}

function updateAppointmentStatus(appointmentId, status) {
    if (confirm(`Are you sure you want to ${status} this appointment?`)) {
        // In a real implementation, this would make an AJAX call
        showToast(`Appointment status updated to: ${status}`, 'success');
        
        // Reload the page to reflect changes
        setTimeout(() => {
            location.reload();
        }, 1500);
    }
}

// Patient-specific functionality
if (window.location.pathname.includes('patient') || (!window.location.pathname.includes('staff') && !window.location.pathname.includes('admin'))) {
    document.addEventListener('DOMContentLoaded', function() {
        initializePatientFeatures();
    });
}

function initializePatientFeatures() {
    // Medicine quantity selectors
    const quantityInputs = document.querySelectorAll('input[name="quantity"]');
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const price = parseFloat(this.dataset.price || 0);
            const quantity = parseInt(this.value || 1);
            const totalElement = this.parentNode.querySelector('.total-price');
            
            if (totalElement) {
                totalElement.textContent = formatCurrency(price * quantity);
            }
        });
    });
    
    // Lab test preparation info toggle
    const prepInfoButtons = document.querySelectorAll('.prep-info-toggle');
    prepInfoButtons.forEach(button => {
        button.addEventListener('click', function() {
            const prepInfo = this.parentNode.querySelector('.preparation-info');
            if (prepInfo) {
                prepInfo.style.display = prepInfo.style.display === 'none' ? 'block' : 'none';
            }
        });
    });
}

// Error handling
window.addEventListener('error', function(event) {
    console.error('JavaScript error:', event.error);
    
    // Show user-friendly error message for critical errors
    if (event.error && event.error.message && !event.error.message.includes('Script error')) {
        showToast('An error occurred. Please refresh the page and try again.', 'danger');
    }
});

// Prevent form double submission
document.addEventListener('submit', function(event) {
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
    
    if (submitButton && !submitButton.disabled) {
        setTimeout(() => {
            submitButton.disabled = true;
            submitButton.innerHTML = submitButton.innerHTML.replace(/Submit|Save|Book|Send|Order/, '$& <i class="fas fa-spinner fa-spin"></i>');
        }, 100);
    }
});

// Initialize tooltips and popovers if Bootstrap is available
if (typeof bootstrap !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    });
}

// Export functions for global access
window.showToast = showToast;
window.updateAppointmentStatus = updateAppointmentStatus;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
