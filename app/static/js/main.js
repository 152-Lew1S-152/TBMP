// Main JavaScript file for MTS site

document.addEventListener('DOMContentLoaded', function() {
    console.log('MTS site loaded successfully');
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add to cart functionality with AJAX
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(form);
            const productId = form.getAttribute('data-product-id');
            const url = form.getAttribute('action');
            
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show notification
                    const notification = document.createElement('div');
                    notification.className = 'toast align-items-center text-white bg-success border-0 position-fixed bottom-0 end-0 m-3';
                    notification.setAttribute('role', 'alert');
                    notification.setAttribute('aria-live', 'assertive');
                    notification.setAttribute('aria-atomic', 'true');
                    
                    notification.innerHTML = `
                        <div class="d-flex">
                            <div class="toast-body">
                                Товар успешно добавлен в корзину
                            </div>
                            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                        </div>
                    `;
                    
                    document.body.appendChild(notification);
                    const toast = new bootstrap.Toast(notification);
                    toast.show();
                    
                    // Update cart counter if exists
                    const cartCounter = document.querySelector('.cart-counter');
                    if (cartCounter) {
                        let count = parseInt(cartCounter.textContent || '0');
                        cartCounter.textContent = count + 1;
                    }
                }
            })
            .catch(error => {
                console.error('Error adding to cart:', error);
            });
        });
    });
    
    // Quantity input controls
    const quantityInputs = document.querySelectorAll('.quantity-input');
    quantityInputs.forEach(input => {
        const decreaseBtn = input.parentElement.querySelector('.decrease-btn');
        const increaseBtn = input.parentElement.querySelector('.increase-btn');
        
        if (decreaseBtn) {
            decreaseBtn.addEventListener('click', function() {
                if (input.value > 1) {
                    input.value = parseInt(input.value) - 1;
                }
            });
        }
        
        if (increaseBtn) {
            increaseBtn.addEventListener('click', function() {
                const max = input.getAttribute('max');
                if (!max || parseInt(input.value) < parseInt(max)) {
                    input.value = parseInt(input.value) + 1;
                }
            });
        }
    });
});
