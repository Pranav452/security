// Global variables
let currentUser = null;
let authToken = null;
let cart = { items: [], total_amount: 0 };

// API base URL
const API_BASE = '';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    // Check for stored auth token
    authToken = localStorage.getItem('authToken');
    if (authToken) {
        getCurrentUser();
    }
    
    // Update navigation
    updateNavigation();
    
    // Initialize page-specific functionality
    const path = window.location.pathname;
    if (path === '/') {
        initHomePage();
    } else if (path === '/medicines') {
        initMedicinesPage();
    } else if (path === '/cart') {
        initCartPage();
    } else if (path === '/orders') {
        initOrdersPage();
    } else if (path === '/prescriptions') {
        initPrescriptionsPage();
    } else if (path === '/profile') {
        initProfilePage();
    } else if (path === '/dashboard') {
        initDashboardPage();
    }
});

// Authentication functions
async function getCurrentUser() {
    try {
        const response = await fetch('/auth/me', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            currentUser = await response.json();
            updateNavigation();
            return currentUser;
        } else {
            // Invalid token
            logout();
        }
    } catch (error) {
        console.error('Error getting current user:', error);
        logout();
    }
}

async function login(username, password) {
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch('/auth/login', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            
            showAlert('Login successful!', 'success');
            updateNavigation();
            window.location.href = '/dashboard';
            return true;
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Login failed', 'error');
            return false;
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('Network error during login', 'error');
        return false;
    }
}

async function register(userData) {
    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
        
        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            
            showAlert('Registration successful!', 'success');
            updateNavigation();
            window.location.href = '/dashboard';
            return true;
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Registration failed', 'error');
            return false;
        }
    } catch (error) {
        console.error('Registration error:', error);
        showAlert('Network error during registration', 'error');
        return false;
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    updateNavigation();
    window.location.href = '/';
}

// Navigation functions
function updateNavigation() {
    const navLinks = document.querySelector('.nav-links');
    if (!navLinks) return;
    
    if (currentUser) {
        navLinks.innerHTML = `
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/medicines">Medicines</a></li>
            <li><a href="/cart">Cart</a></li>
            <li><a href="/prescriptions">Prescriptions</a></li>
            <li><a href="/orders">Orders</a></li>
            <li><a href="/profile">Profile</a></li>
            ${currentUser.role === 'admin' ? '<li><a href="/admin">Admin</a></li>' : ''}
            <li><a href="#" onclick="logout()">Logout</a></li>
        `;
    } else {
        navLinks.innerHTML = `
            <li><a href="/">Home</a></li>
            <li><a href="/medicines">Browse Medicines</a></li>
            <li><a href="/login">Login</a></li>
            <li><a href="/register">Register</a></li>
        `;
    }
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    // Insert at the top of main content
    const main = document.querySelector('.main .container');
    if (main) {
        main.insertBefore(alertDiv, main.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

function formatPrice(price) {
    return `$${parseFloat(price).toFixed(2)}`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// API request helper
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        }
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, mergedOptions);
        
        if (response.status === 401) {
            logout();
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('API request error:', error);
        showAlert('Network error', 'error');
        return null;
    }
}

// Page initialization functions
function initHomePage() {
    // Emergency delivery button
    const emergencyBtn = document.getElementById('emergency-btn');
    if (emergencyBtn) {
        emergencyBtn.addEventListener('click', function() {
            if (!currentUser) {
                showAlert('Please login to request emergency delivery', 'warning');
                window.location.href = '/login';
                return;
            }
            // Handle emergency delivery
            handleEmergencyDelivery();
        });
    }
}

function initMedicinesPage() {
    loadCategories();
    loadMedicines();
    
    // Search functionality
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            searchMedicines();
        });
    }
}

function initCartPage() {
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    loadCart();
}

function initOrdersPage() {
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    loadOrders();
}

function initPrescriptionsPage() {
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    loadPrescriptions();
    
    // File upload
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handlePrescriptionUpload);
    }
}

function initProfilePage() {
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    loadProfile();
}

function initDashboardPage() {
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    loadDashboard();
}

// Medicine functions
async function loadCategories() {
    const response = await apiRequest('/categories/');
    if (response && response.ok) {
        const categories = await response.json();
        const categorySelect = document.getElementById('category-filter');
        if (categorySelect) {
            categorySelect.innerHTML = '<option value="">All Categories</option>';
            categories.forEach(category => {
                categorySelect.innerHTML += `<option value="${category.id}">${category.name}</option>`;
            });
        }
    }
}

async function loadMedicines(searchParams = {}) {
    const queryParams = new URLSearchParams(searchParams);
    const response = await apiRequest(`/medicines/search?${queryParams}`);
    
    if (response && response.ok) {
        const medicines = await response.json();
        displayMedicines(medicines);
    }
}

function displayMedicines(medicines) {
    const container = document.getElementById('medicines-grid');
    if (!container) return;
    
    if (medicines.length === 0) {
        container.innerHTML = '<p class="text-center">No medicines found.</p>';
        return;
    }
    
    container.innerHTML = medicines.map(medicine => `
        <div class="medicine-card">
            <div class="medicine-name">${medicine.name}</div>
            <div class="medicine-price">${formatPrice(medicine.price)}</div>
            <p><strong>Brand:</strong> ${medicine.brand_name || 'Generic'}</p>
            <p><strong>Form:</strong> ${medicine.form || 'N/A'}</p>
            <p><strong>Dosage:</strong> ${medicine.dosage || 'N/A'}</p>
            <div class="medicine-stock ${medicine.stock_quantity < 10 ? 'low' : ''}">
                Stock: ${medicine.stock_quantity} units
            </div>
            ${medicine.prescription_required ? '<span class="prescription-badge">Prescription Required</span>' : ''}
            <div class="mt-2">
                ${medicine.stock_quantity > 0 ? 
                    `<button class="btn btn-primary" onclick="addToCart(${medicine.id}, '${medicine.name}', ${medicine.prescription_required})">
                        Add to Cart
                    </button>` :
                    '<button class="btn btn-secondary" disabled>Out of Stock</button>'
                }
            </div>
        </div>
    `).join('');
}

async function searchMedicines() {
    const searchTerm = document.getElementById('search-input').value;
    const category = document.getElementById('category-filter').value;
    const prescriptionRequired = document.getElementById('prescription-filter').value;
    
    const searchParams = {};
    if (searchTerm) searchParams.q = searchTerm;
    if (category) searchParams.category = category;
    if (prescriptionRequired !== '') searchParams.prescription_required = prescriptionRequired === 'true';
    
    await loadMedicines(searchParams);
}

// Cart functions
async function addToCart(medicineId, medicineName, prescriptionRequired) {
    if (!currentUser) {
        showAlert('Please login to add items to cart', 'warning');
        window.location.href = '/login';
        return;
    }
    
    let prescriptionId = null;
    if (prescriptionRequired) {
        prescriptionId = await selectPrescription();
        if (!prescriptionId) {
            showAlert('Prescription required for this medicine', 'warning');
            return;
        }
    }
    
    const response = await apiRequest('/cart/items', {
        method: 'POST',
        body: JSON.stringify({
            medicine_id: medicineId,
            quantity: 1,
            prescription_id: prescriptionId
        })
    });
    
    if (response && response.ok) {
        showAlert(`${medicineName} added to cart!`, 'success');
        updateCartBadge();
    } else {
        const error = await response.json();
        showAlert(error.detail || 'Failed to add to cart', 'error');
    }
}

async function loadCart() {
    const response = await apiRequest('/cart/');
    if (response && response.ok) {
        cart = await response.json();
        displayCart();
    }
}

function displayCart() {
    const container = document.getElementById('cart-items');
    const totalContainer = document.getElementById('cart-total');
    
    if (!container) return;
    
    if (cart.items.length === 0) {
        container.innerHTML = '<p class="text-center">Your cart is empty.</p>';
        if (totalContainer) totalContainer.innerHTML = '';
        return;
    }
    
    container.innerHTML = cart.items.map(item => `
        <div class="cart-item">
            <div>
                <h4>${item.medicine.name}</h4>
                <p>${formatPrice(item.medicine.price)} each</p>
                ${item.medicine.prescription_required ? '<span class="prescription-badge">Prescription Required</span>' : ''}
            </div>
            <div class="quantity-controls">
                <button class="quantity-btn" onclick="updateCartItem(${item.id}, ${item.quantity - 1})">-</button>
                <span>${item.quantity}</span>
                <button class="quantity-btn" onclick="updateCartItem(${item.id}, ${item.quantity + 1})">+</button>
                <button class="btn btn-secondary" onclick="removeCartItem(${item.id})">Remove</button>
            </div>
        </div>
    `).join('');
    
    if (totalContainer) {
        totalContainer.innerHTML = `
            <div class="cart-total">
                <h3>Total: ${formatPrice(cart.total_amount)}</h3>
                ${cart.prescription_required_items > 0 ? 
                    `<p class="text-warning">${cart.prescription_required_items} items require prescriptions</p>` : ''
                }
                <button class="btn btn-primary" onclick="proceedToCheckout()">Proceed to Checkout</button>
            </div>
        `;
    }
}

async function updateCartItem(itemId, quantity) {
    if (quantity <= 0) {
        await removeCartItem(itemId);
        return;
    }
    
    const response = await apiRequest(`/cart/items/${itemId}`, {
        method: 'PUT',
        body: JSON.stringify({ quantity })
    });
    
    if (response && response.ok) {
        await loadCart();
    }
}

async function removeCartItem(itemId) {
    const response = await apiRequest(`/cart/items/${itemId}`, {
        method: 'DELETE'
    });
    
    if (response && response.ok) {
        await loadCart();
        showAlert('Item removed from cart', 'success');
    }
}

async function proceedToCheckout() {
    // Validate prescriptions first
    const response = await apiRequest('/cart/validate-prescriptions', {
        method: 'POST'
    });
    
    if (response && response.ok) {
        const validation = await response.json();
        if (validation.can_proceed_to_checkout) {
            // Show checkout form
            showCheckoutForm();
        } else {
            showAlert(`Cannot proceed: ${validation.total_issues} issues found`, 'error');
        }
    }
}

// Order functions
async function loadOrders() {
    const response = await apiRequest('/orders/');
    if (response && response.ok) {
        const orders = await response.json();
        displayOrders(orders);
    }
}

function displayOrders(orders) {
    const container = document.getElementById('orders-list');
    if (!container) return;
    
    if (orders.length === 0) {
        container.innerHTML = '<p class="text-center">No orders found.</p>';
        return;
    }
    
    container.innerHTML = orders.map(order => `
        <div class="card">
            <div class="card-header">
                <h4>Order #${order.order_number}</h4>
                <span class="status-badge status-${order.status}">${order.status}</span>
            </div>
            <p><strong>Total:</strong> ${formatPrice(order.total_amount)}</p>
            <p><strong>Ordered:</strong> ${formatDate(order.created_at)}</p>
            <p><strong>Estimated Delivery:</strong> ${order.estimated_delivery_time ? formatDate(order.estimated_delivery_time) : 'TBD'}</p>
            ${order.is_emergency ? '<span class="text-danger"><strong>EMERGENCY ORDER</strong></span>' : ''}
            <div class="mt-2">
                <button class="btn btn-primary" onclick="trackOrder(${order.id})">Track Order</button>
                <button class="btn btn-secondary" onclick="viewOrderDetails(${order.id})">View Details</button>
            </div>
        </div>
    `).join('');
}

// Prescription functions
async function loadPrescriptions() {
    const response = await apiRequest('/prescriptions/');
    if (response && response.ok) {
        const prescriptions = await response.json();
        displayPrescriptions(prescriptions);
    }
}

function displayPrescriptions(prescriptions) {
    const container = document.getElementById('prescriptions-list');
    if (!container) return;
    
    if (prescriptions.length === 0) {
        container.innerHTML = '<p class="text-center">No prescriptions found.</p>';
        return;
    }
    
    container.innerHTML = prescriptions.map(prescription => `
        <div class="card">
            <h4>Dr. ${prescription.doctor_name}</h4>
            <p><strong>Hospital:</strong> ${prescription.hospital_name || 'N/A'}</p>
            <p><strong>Date:</strong> ${formatDate(prescription.prescription_date)}</p>
            <p><strong>Status:</strong> <span class="status-badge status-${prescription.status}">${prescription.status}</span></p>
            <p><strong>Uploaded:</strong> ${formatDate(prescription.created_at)}</p>
            ${prescription.verification_notes ? `<p><strong>Notes:</strong> ${prescription.verification_notes}</p>` : ''}
        </div>
    `).join('');
}

async function handlePrescriptionUpload(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    
    const response = await fetch('/prescriptions/upload', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${authToken}`
        },
        body: formData
    });
    
    if (response.ok) {
        showAlert('Prescription uploaded successfully!', 'success');
        await loadPrescriptions();
        event.target.reset();
    } else {
        const error = await response.json();
        showAlert(error.detail || 'Upload failed', 'error');
    }
}

// Profile functions
async function loadProfile() {
    if (currentUser) {
        displayProfile(currentUser);
    }
}

function displayProfile(user) {
    const container = document.getElementById('profile-form');
    if (!container) return;
    
    container.innerHTML = `
        <form onsubmit="updateProfile(event)">
            <div class="form-group">
                <label class="form-label">Full Name</label>
                <input type="text" name="full_name" class="form-input" value="${user.full_name || ''}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Phone</label>
                <input type="tel" name="phone" class="form-input" value="${user.phone || ''}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Age</label>
                <input type="number" name="age" class="form-input" value="${user.age || ''}" min="1" max="120">
            </div>
            <div class="form-group">
                <label class="form-label">Medical Conditions</label>
                <textarea name="medical_conditions" class="form-textarea">${user.medical_conditions || ''}</textarea>
            </div>
            <div class="form-group">
                <label class="form-label">Allergies</label>
                <textarea name="allergies" class="form-textarea">${user.allergies || ''}</textarea>
            </div>
            <div class="form-group">
                <label class="form-label">Address</label>
                <textarea name="address" class="form-textarea">${user.address || ''}</textarea>
            </div>
            <div class="form-group">
                <label class="form-label">City</label>
                <input type="text" name="city" class="form-input" value="${user.city || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">State</label>
                <input type="text" name="state" class="form-input" value="${user.state || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">ZIP Code</label>
                <input type="text" name="zip_code" class="form-input" value="${user.zip_code || ''}">
            </div>
            <button type="submit" class="btn btn-primary">Update Profile</button>
        </form>
    `;
}

async function updateProfile(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const profileData = Object.fromEntries(formData.entries());
    
    const response = await apiRequest('/auth/profile', {
        method: 'PUT',
        body: JSON.stringify(profileData)
    });
    
    if (response && response.ok) {
        currentUser = await response.json();
        showAlert('Profile updated successfully!', 'success');
    } else {
        const error = await response.json();
        showAlert(error.detail || 'Update failed', 'error');
    }
}

// Dashboard functions
async function loadDashboard() {
    const container = document.getElementById('dashboard-content');
    if (!container) return;
    
    container.innerHTML = `
        <div class="grid grid-3">
            <div class="card">
                <h3>Quick Order</h3>
                <p>Search and order medicines quickly</p>
                <a href="/medicines" class="btn btn-primary">Browse Medicines</a>
            </div>
            <div class="card">
                <h3>My Cart</h3>
                <p>Review items in your cart</p>
                <a href="/cart" class="btn btn-primary">View Cart</a>
            </div>
            <div class="card">
                <h3>Prescriptions</h3>
                <p>Upload and manage prescriptions</p>
                <a href="/prescriptions" class="btn btn-primary">Manage Prescriptions</a>
            </div>
            <div class="card">
                <h3>Order History</h3>
                <p>Track your orders and deliveries</p>
                <a href="/orders" class="btn btn-primary">View Orders</a>
            </div>
            <div class="card">
                <h3>Emergency Delivery</h3>
                <p>Get medicines delivered in 10 minutes</p>
                <button class="btn btn-emergency" onclick="handleEmergencyDelivery()">Emergency Order</button>
            </div>
            <div class="card">
                <h3>Profile</h3>
                <p>Update your medical profile</p>
                <a href="/profile" class="btn btn-primary">Edit Profile</a>
            </div>
        </div>
    `;
}

// Helper functions
async function selectPrescription() {
    // In a real app, this would show a modal with prescription options
    // For now, return null to prompt user to upload prescriptions
    return null;
}

function showCheckoutForm() {
    // Show checkout modal/form
    const modal = document.createElement('div');
    modal.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
            <div style="background: white; padding: 2rem; border-radius: 10px; max-width: 500px; width: 90%;">
                <h3>Checkout</h3>
                <form onsubmit="completeOrder(event)">
                    <div class="form-group">
                        <label class="form-label">Delivery Address</label>
                        <textarea name="delivery_address" class="form-textarea" required>${currentUser.address || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Delivery Phone</label>
                        <input type="tel" name="delivery_phone" class="form-input" required value="${currentUser.phone || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Payment Method</label>
                        <select name="payment_method" class="form-select" required>
                            <option value="cash_on_delivery">Cash on Delivery</option>
                            <option value="card">Credit/Debit Card</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="is_emergency"> Emergency Delivery (+$10, 10 minutes)
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Delivery Notes</label>
                        <textarea name="delivery_notes" class="form-textarea"></textarea>
                    </div>
                    <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                        <button type="button" onclick="this.closest('div').remove()" class="btn btn-secondary">Cancel</button>
                        <button type="submit" class="btn btn-primary">Place Order</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

async function completeOrder(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const orderData = {
        delivery_address: formData.get('delivery_address'),
        delivery_phone: formData.get('delivery_phone'),
        payment_method: formData.get('payment_method'),
        is_emergency: formData.has('is_emergency'),
        delivery_notes: formData.get('delivery_notes')
    };
    
    const response = await apiRequest('/orders/', {
        method: 'POST',
        body: JSON.stringify(orderData)
    });
    
    if (response && response.ok) {
        const order = await response.json();
        showAlert(`Order placed successfully! Order #${order.order_number}`, 'success');
        
        // Close modal and redirect
        event.target.closest('div').remove();
        window.location.href = '/orders';
    } else {
        const error = await response.json();
        showAlert(error.detail || 'Order failed', 'error');
    }
}

async function handleEmergencyDelivery() {
    // Show emergency delivery form
    const modal = document.createElement('div');
    modal.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
            <div style="background: white; padding: 2rem; border-radius: 10px; max-width: 500px; width: 90%;">
                <h3 style="color: #ff6b6b;">Emergency Delivery</h3>
                <p>Get essential medicines delivered in 10 minutes</p>
                <form onsubmit="submitEmergencyOrder(event)">
                    <div class="form-group">
                        <label class="form-label">Medicine Names (one per line)</label>
                        <textarea name="medicine_names" class="form-textarea" placeholder="Paracetamol&#10;Insulin&#10;Aspirin" required></textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Urgent Notes</label>
                        <textarea name="urgent_notes" class="form-textarea" placeholder="Describe the emergency situation..." required></textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Delivery Address</label>
                        <textarea name="delivery_address" class="form-textarea" required>${currentUser?.address || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Emergency Contact</label>
                        <input type="tel" name="delivery_phone" class="form-input" required value="${currentUser?.phone || ''}">
                    </div>
                    <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                        <button type="button" onclick="this.closest('div').remove()" class="btn btn-secondary">Cancel</button>
                        <button type="submit" class="btn btn-emergency">Request Emergency Delivery</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

async function submitEmergencyOrder(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const emergencyData = {
        medicine_names: formData.get('medicine_names').split('\n').filter(name => name.trim()),
        urgent_notes: formData.get('urgent_notes'),
        delivery_address: formData.get('delivery_address'),
        delivery_phone: formData.get('delivery_phone')
    };
    
    const response = await apiRequest('/delivery/emergency', {
        method: 'POST',
        body: JSON.stringify(emergencyData)
    });
    
    if (response && response.ok) {
        const result = await response.json();
        showAlert(`Emergency order created! Order #${result.order_number}. Estimated delivery: ${formatDate(result.estimated_delivery_time)}`, 'success');
        
        // Close modal and redirect
        event.target.closest('div').remove();
        window.location.href = '/orders';
    } else {
        const error = await response.json();
        showAlert(error.detail || 'Emergency order failed', 'error');
    }
}

async function trackOrder(orderId) {
    const response = await apiRequest(`/orders/${orderId}/track`);
    if (response && response.ok) {
        const trackingData = await response.json();
        
        // Show tracking modal
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; padding: 2rem; border-radius: 10px; max-width: 500px; width: 90%;">
                    <h3>Order Tracking</h3>
                    <p><strong>Order #:</strong> ${trackingData.order_number}</p>
                    <p><strong>Status:</strong> ${trackingData.status}</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${trackingData.progress_percentage}%"></div>
                    </div>
                    <p><strong>Progress:</strong> ${trackingData.progress_percentage}%</p>
                    <p><strong>Tracking #:</strong> ${trackingData.tracking_number}</p>
                    ${trackingData.estimated_delivery_time ? `<p><strong>Estimated Delivery:</strong> ${formatDate(trackingData.estimated_delivery_time)}</p>` : ''}
                    ${trackingData.delivery_partner ? `<p><strong>Delivery Partner:</strong> ${trackingData.delivery_partner.name} (${trackingData.delivery_partner.phone})</p>` : ''}
                    ${trackingData.delivery_notes ? `<p><strong>Notes:</strong> ${trackingData.delivery_notes}</p>` : ''}
                    <div style="text-align: center; margin-top: 1rem;">
                        <button onclick="this.closest('div').remove()" class="btn btn-primary">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
}

async function viewOrderDetails(orderId) {
    const response = await apiRequest(`/orders/${orderId}`);
    if (response && response.ok) {
        const order = await response.json();
        
        // Show order details modal
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; padding: 2rem; border-radius: 10px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;">
                    <h3>Order Details</h3>
                    <p><strong>Order #:</strong> ${order.order_number}</p>
                    <p><strong>Status:</strong> <span class="status-badge status-${order.status}">${order.status}</span></p>
                    <p><strong>Total:</strong> ${formatPrice(order.total_amount)}</p>
                    <p><strong>Delivery Fee:</strong> ${formatPrice(order.delivery_fee)}</p>
                    <p><strong>Tax:</strong> ${formatPrice(order.tax_amount)}</p>
                    <p><strong>Payment Method:</strong> ${order.payment_method}</p>
                    <p><strong>Delivery Address:</strong> ${order.delivery_address}</p>
                    <p><strong>Ordered:</strong> ${formatDate(order.created_at)}</p>
                    
                    <h4>Items:</h4>
                    <div>
                        ${order.order_items.map(item => `
                            <div style="border-bottom: 1px solid #eee; padding: 0.5rem 0;">
                                <strong>${item.medicine.name}</strong> - ${formatPrice(item.price)} x ${item.quantity}
                                ${item.prescription_id ? '<span class="prescription-badge">Prescription</span>' : ''}
                            </div>
                        `).join('')}
                    </div>
                    
                    <div style="text-align: center; margin-top: 1rem;">
                        <button onclick="this.closest('div').remove()" class="btn btn-primary">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
}

async function updateCartBadge() {
    if (!currentUser) return;
    
    const response = await apiRequest('/cart/summary');
    if (response && response.ok) {
        const summary = await response.json();
        
        // Update cart badge if it exists
        const cartBadge = document.getElementById('cart-badge');
        if (cartBadge) {
            cartBadge.textContent = summary.total_items;
            cartBadge.style.display = summary.total_items > 0 ? 'inline' : 'none';
        }
    }
} 