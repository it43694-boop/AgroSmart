// Admin Dashboard JavaScript

let currentUser = null;

// Check authentication
async function checkAuth() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            window.location.href = '/login';
            return false;
        }

        const response = await fetch('/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            currentUser = await response.json();
            if (currentUser.role !== 'admin') {
                window.location.href = '/login';
                return false;
            }
            return true;
        } else {
            window.location.href = '/login';
            return false;
        }
    } catch (error) {
        console.error('Erreur auth:', error);
        window.location.href = '/login';
        return false;
    }
}

// Show section
function showSection(event, sectionId) {
    if (event) {
        event.preventDefault();
    }

    // Hide all sections
    document.querySelectorAll('.dashboard-section').forEach(section => {
        section.style.display = 'none';
    });

    // Show selected section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.style.display = 'block';
    }

    // Update active menu link
    document.querySelectorAll('.menu-link').forEach(link => {
        link.classList.remove('active');
    });
    if (event && event.target) {
        event.target.classList.add('active');
    }
}

// Logout
function logout() {
    localStorage.removeItem('accessToken');
    window.location.href = '/login';
}

// Initialize dashboard
async function initDashboard() {
    const authenticated = await checkAuth();
    if (!authenticated) {
        return;
    }

    // Load dashboard data
    await loadDashboardStats();
    showSection(null, 'dashboard');
}

// Load dashboard statistics
async function loadDashboardStats() {
    try {
        const token = localStorage.getItem('accessToken');
        
        // Load users count
        const usersResponse = await fetch('/api/admin/users', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (usersResponse.ok) {
            const users = await usersResponse.json();
            const usersCount = document.getElementById('users-count');
            if (usersCount) {
                usersCount.textContent = users.length || 0;
            }
        }

        // Load farmers count
        const farmersResponse = await fetch('/api/admin/users?role=farmer', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (farmersResponse.ok) {
            const farmers = await farmersResponse.json();
            const farmersCount = document.getElementById('farmers-count');
            if (farmersCount) {
                farmersCount.textContent = farmers.length || 0;
            }
        }

    } catch (error) {
        console.error('Erreur chargement stats:', error);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
