// client-dashboard.js - Logique pour le dashboard client

// ===== UTILITY: Image Management =====
class ImageManager {
    /**
     * Normalize images from API response (CSV string) to array
     * @param {string|array} images - CSV string or array of image URLs
     * @returns {array} Array of image URLs
     */
    static normalize(images) {
        if (!images) return [];
        if (Array.isArray(images)) return images.filter(img => img && img.trim());
        if (typeof images === 'string') {
            return images
                .split(',')
                .map(url => url.trim())
                .filter(url => url && url.length > 0);
        }
        return [];
    }

    /**
     * Get first image or placeholder
     * @param {array} images - Array of image URLs
     * @returns {string} First image URL or placeholder SVG data URI
     */
    static getMainImage(images) {
        const normalized = this.normalize(images);
        if (normalized.length > 0) return normalized[0];
        return this.getPlaceholder();
    }

    /**
     * Get placeholder SVG for missing images
     * @returns {string} SVG data URI
     */
    static getPlaceholder() {
        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
                <rect width="300" height="300" fill="#f0f0f0"/>
                <text x="150" y="150" font-size="20" fill="#999" text-anchor="middle" dominant-baseline="middle">
                    📸 Pas d'image
                </text>
            </svg>
        `;

        // Encode SVG safely for a data URI without using btoa on UTF-8 characters.
        const encoded = encodeURIComponent(svg)
            .replace(/'/g, '%27')
            .replace(/"/g, '%22');

        return `data:image/svg+xml;charset=utf-8,${encoded}`;
    }
}

// ===== CLIENT DASHBOARD CLASS =====

class ClientDashboard {
    constructor() {
        this.currentUser = null;
        this.currentListings = [];
        this.pendingOrder = null;  // For order confirmation flow
        this.pendingReviewOrder = null;  // For review flow
        this.init();
    }

    async init() {
        await this.checkAuth();
        this.setupEventListeners();
        this.loadDashboardData();
    }

    async checkAuth() {
        try {
            const response = await fetch('/api/me', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                localStorage.removeItem('accessToken');
                window.location.href = '/login';
                return;
            }

            this.currentUser = await response.json();

            // Vérifier que c'est un client ou admin
            const userRole = this.currentUser.role || this.currentUser.account_type;
            if (userRole !== 'client' && !this.currentUser.is_admin) {
                console.error('Access denied: not a client. Role:', userRole);
                localStorage.removeItem('accessToken');
                if (userRole === 'farmer') {
                    window.location.href = '/farmer-dashboard';
                } else if (userRole === 'bank') {
                    window.location.href = '/bank-dashboard';
                } else if (userRole === 'insurance') {
                    window.location.href = '/insurance-dashboard';
                } else if (userRole === 'admin') {
                    window.location.href = '/admin';
                } else {
                    window.location.href = '/login';
                }
                return;
            }

            document.getElementById('user-name').textContent = this.currentUser.full_name;
        } catch (error) {
            console.error('Erreur authentification:', error);
            localStorage.removeItem('accessToken');
            window.location.href = '/login';
        }
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.showSection(e.target.getAttribute('href').substring(1));
            });
        });

        const bestOffersBtn = document.getElementById('best-offers-btn');
        if (bestOffersBtn) {
            bestOffersBtn.addEventListener('click', () => {
                this.showSection('marketplace');
                this.loadMarketplace();
            });
        }

        // Filtres marketplace
        const searchBtn = document.getElementById('search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.searchListings());
        }

        // Déconnexion
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }

        // Modals
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', () => this.closeModals());
        });
    }

    showSection(sectionId) {
        // Masquer toutes les sections
        document.querySelectorAll('.dashboard-section').forEach(section => {
            section.classList.remove('active');
        });

        // Masquer tous les liens de navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        // Afficher la section demandée
        document.getElementById(sectionId).classList.add('active');
        document.querySelector(`[href="#${sectionId}"]`).classList.add('active');

        // Charger les données de la section si nécessaire
        switch(sectionId) {
            case 'marketplace':
                this.loadMarketplace();
                break;
            case 'orders':
                this.loadOrders();
                break;
            case 'requests':
                this.loadRequests();
                break;
            case 'favorites':
                this.loadFavorites();
                break;
            case 'reviews':
                this.loadReviews();
                break;
        }
    }

    async loadDashboardData() {
        try {
            const [ordersResponse, requestsResponse] = await Promise.all([
                fetch('/api/client/orders/', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                    }
                }),
                fetch('/api/client/requests/', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                    }
                })
            ]);

            const orders = ordersResponse.ok ? await ordersResponse.json() : [];
            const requests = requestsResponse.ok ? await requestsResponse.json() : { loan_requests: [], insurance_requests: [] };
            this.updateOverview(orders, requests);
            this.loadMarketplace();
        } catch (error) {
            console.error('Erreur chargement dashboard:', error);
        }
    }

    updateOverview(orders, requests) {
        const totalOrders = orders.length;
        const totalSpent = orders.reduce((sum, order) => sum + (order.total_price || 0), 0);
        const totalLoanRequests = (requests.loan_requests || []).length;
        const totalInsuranceRequests = (requests.insurance_requests || []).length;

        document.getElementById('total-orders').textContent = totalOrders;
        document.getElementById('total-spent').textContent = `${totalSpent.toLocaleString()} XOF`;
        document.getElementById('reviews-count').textContent = '0';
        document.getElementById('favorites-count').textContent = '0';

        if (!document.getElementById('request-summary')) {
            const summaryCard = document.createElement('div');
            summaryCard.className = 'stat-card';
            summaryCard.innerHTML = `<h3>Demandes en cours</h3><div class="stat-value" id="request-summary"></div>`;
            document.querySelector('.stats-grid').appendChild(summaryCard);
        }

        document.getElementById('request-summary').textContent = `${totalLoanRequests} prêts, ${totalInsuranceRequests} assurances`;

        this.loadGamificationStats();
        this.createSpendingChart(orders);
        this.createOrdersChart(orders);
    }

    async loadGamificationStats() {
        try {
            const response = await fetch('/api/gamification/stats', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const stats = await response.json();
                this.displayGamificationWidget(stats);
            }
        } catch (error) {
            console.error('Erreur chargement gamification:', error);
        }
    }

    displayGamificationWidget(stats) {
        const container = document.querySelector('.stats-grid');
        
        if (!document.getElementById('gamification-widget')) {
            const widget = document.createElement('div');
            widget.id = 'gamification-widget';
            widget.className = 'stat-card';
            widget.innerHTML = `
                <h3>🎮 Gamification</h3>
                <div class="gamification-stats">
                    <div class="gam-item">
                        <span class="gam-label">Points</span>
                        <span class="gam-value" id="gam-points">0</span>
                    </div>
                    <div class="gam-item">
                        <span class="gam-label">Niveau</span>
                        <span class="gam-value" id="gam-level">1</span>
                    </div>
                    <div class="gam-item">
                        <span class="gam-label">Badges</span>
                        <span class="gam-value" id="gam-badges">0</span>
                    </div>
                    <div class="gam-item">
                        <span class="gam-label">Réputation</span>
                        <span class="gam-value" id="gam-reputation">0</span>
                    </div>
                </div>
            `;
            container.appendChild(widget);
        }

        document.getElementById('gam-points').textContent = stats.points || 0;
        document.getElementById('gam-level').textContent = stats.level || 1;
        document.getElementById('gam-badges').textContent = (stats.badges || []).length;
        document.getElementById('gam-reputation').textContent = stats.reputation_score || 0;
    }

    createSpendingChart(orders) {
        const ctx = document.getElementById('spending-chart').getContext('2d');

        // Grouper par catégorie (simplifié)
        const spendingByCategory = {};
        orders.forEach(order => {
            const category = order.listing?.category || 'Autre';
            spendingByCategory[category] = (spendingByCategory[category] || 0) + (order.total_price || 0);
        });

        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: Object.keys(spendingByCategory),
                datasets: [{
                    data: Object.values(spendingByCategory),
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF'
                    ]
                }]
            },
            options: {
                responsive: true
            }
        });
    }

    createOrdersChart(orders) {
        const ctx = document.getElementById('orders-chart').getContext('2d');

        // Grouper par mois
        const ordersByMonth = {};
        orders.forEach(order => {
            const date = new Date(order.created_at);
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            ordersByMonth[monthKey] = (ordersByMonth[monthKey] || 0) + 1;
        });

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: Object.keys(ordersByMonth).sort(),
                datasets: [{
                    label: 'Nombre de commandes',
                    data: Object.values(ordersByMonth),
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    async loadMarketplace() {
        console.log('loadMarketplace appelé');
        try {
            const response = await fetch('/api/marketplace/listings', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            console.log('Réponse API marketplace:', response.status, response.statusText);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Données reçues:', data);
                this.currentListings = data.listings || data;
                console.log('Listings stockés:', this.currentListings.length);
                this.displayListings(this.currentListings);
                this.loadRecommendations();
            } else {
                console.error('Erreur API marketplace:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Erreur chargement marketplace:', error);
        }
    }

    async loadRecommendations() {
        try {
            const response = await fetch('/api/recommendations/hybrid?limit=10', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                const recommendations = data.recommendations || [];
                this.displayRecommendations(recommendations);
            }
        } catch (error) {
            console.error('Erreur chargement recommandations:', error);
        }
    }

    displayRecommendations(recommendations) {
        const container = document.getElementById('recommendations-section');
        if (!container) {
            const marketplaceSection = document.getElementById('marketplace');
            const recSection = document.createElement('section');
            recSection.id = 'recommendations-section';
            recSection.className = 'dashboard-section';
            recSection.innerHTML = `
                <h2>🎯 Recommandations pour vous</h2>
                <div id="recommendations-grid" class="items-grid"></div>
            `;
            marketplaceSection.parentNode.insertBefore(recSection, marketplaceSection);
        }

        const grid = document.getElementById('recommendations-grid');
        grid.innerHTML = recommendations.map(rec => this.createListingCard(rec)).join('');
    }

    searchListings() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const category = document.getElementById('category-filter').value;
        const minPrice = parseFloat(document.getElementById('min-price').value) || 0;
        const maxPrice = parseFloat(document.getElementById('max-price').value) || Infinity;

        const filteredListings = this.currentListings.filter(listing => {
            const matchesSearch = listing.title.toLowerCase().includes(searchTerm) ||
                                listing.description.toLowerCase().includes(searchTerm);
            const matchesCategory = !category || listing.category === category;
            const matchesPrice = listing.price_per_unit >= minPrice && listing.price_per_unit <= maxPrice;

            return matchesSearch && matchesCategory && matchesPrice;
        });

        this.displayListings(filteredListings);
    }

    displayListings(listings) {
        console.log('displayListings appelé avec', listings.length, 'listings');
        const container = document.getElementById('marketplace-listings');
        if (!container) {
            console.error('Conteneur marketplace-listings non trouvé');
            return;
        }
        container.innerHTML = '';

        if (!listings || listings.length === 0) {
            container.innerHTML = '<p>Aucun produit disponible dans la marketplace.</p>';
            return;
        }

        listings.forEach(listing => {
            const listingCard = document.createElement('div');
            listingCard.className = 'item-card marketplace-card';
            const mainImage = ImageManager.getMainImage(listing.images);
            
            const description = listing.description || 'Pas de description';
            
            listingCard.innerHTML = `
                <img src="${mainImage}" alt="${listing.title}" class="listing-image" onerror="this.src='${ImageManager.getPlaceholder()}'">
                <div class="listing-info">
                    <h4>${listing.title}</h4>
                    <p class="listing-description">${description.substring(0, 60)}...</p>
                    <div class="listing-price">
                        <span class="price">${listing.price_per_unit.toLocaleString()} XOF</span>
                        <span class="unit">/${listing.unit}</span>
                    </div>
                    <div class="listing-meta">
                        <span>Qté: ${listing.quantity} ${listing.unit}</span>
                    </div>
                    <div class="card-actions">
                        <button class="btn-primary" onclick="clientDashboard.viewListing(${listing.id})">Détails</button>
                        <button class="btn-secondary" onclick="clientDashboard.addToFavorites(${listing.id})">❤️</button>
                    </div>
                </div>
            `;
            container.appendChild(listingCard);
        });
        console.log('Listings affichés:', listings.length);
    }

    async loadOrders() {
        try {
            const response = await fetch('/api/client/orders/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const orders = await response.json();
                this.displayOrders(orders);
            } else {
                this.displayOrders([]);
            }
        } catch (error) {
            console.error('Erreur chargement commandes:', error);
            this.displayOrders([]);
        }
    }

    displayOrders(orders) {
        const container = document.getElementById('orders-list');
        if (!container) return;
        container.innerHTML = '';

        const safeOrders = Array.isArray(orders) ? orders : [];
        if (!safeOrders.length) {
            container.innerHTML = `
                <div class="no-data">
                    <h3>Vous n’avez pas encore de commande.</h3>
                    <p>Explorez la marketplace pour passer votre première commande.</p>
                    <button class="btn-primary" onclick="clientDashboard.showSection('marketplace')">Voir la marketplace</button>
                </div>
            `;
            return;
        }

        safeOrders.forEach(order => {
            const orderCard = document.createElement('div');
            orderCard.className = 'item-card';
            orderCard.innerHTML = `
                <h4>Commande #${order.id}</h4>
                <p><strong>Produit :</strong> ${order.listing?.title || 'Produit non renseigné'}</p>
                <p><strong>Quantité :</strong> ${order.quantity || 0} ${order.listing?.unit || ''}</p>
                <p><strong>Total :</strong> ${Number(order.total_price || 0).toLocaleString()} XOF</p>
                <p><strong>Statut :</strong> <span class="status-${order.status || 'unknown'}">${order.status || 'Inconnu'}</span></p>
                <p><strong>Livraison :</strong> ${order.shipping_address || 'Non définie'}</p>
                <p><strong>Payé via :</strong> ${order.payment_method || 'N/A'}</p>
                <p><strong>Date :</strong> ${new Date(order.created_at).toLocaleDateString('fr-FR')}</p>
                <div class="card-actions">
                    <button class="btn-secondary" onclick="clientDashboard.viewOrderDetails(${order.id})">Voir Détails</button>
                    ${order.status === 'delivered' ? `<button class="btn-primary" onclick="clientDashboard.leaveReview(${order.id})">Laisser un Avis</button>` : ''}
                </div>
            `;
            container.appendChild(orderCard);
        });
    }

    async viewOrderDetails(orderId) {
        try {
            const response = await fetch(`/api/marketplace/orders/${orderId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                alert('Impossible de charger le détail de la commande.');
                return;
            }

            const order = await response.json();
            this.displayOrderDetails(order);
            const modal = document.getElementById('order-detail-modal');
            if (modal) modal.style.display = 'block';
        } catch (error) {
            console.error('Erreur chargement détail commande:', error);
            alert('Erreur lors du chargement du détail de la commande.');
        }
    }

    displayOrderDetails(order) {
        const container = document.getElementById('order-detail-content');
        if (!container) return;

        const payment = order.payment || {};
        const seller = order.seller || {};
        const listing = order.listing || {};
        const transactionDetails = payment.transaction_details || {};

        container.innerHTML = `
            <div class="modal-header">
                <h3>Commande #${order.id} - ${order.status}</h3>
            </div>
            <div class="modal-body">
                <h4>Produit</h4>
                <p><strong>${listing.title || 'N/A'}</strong></p>
                <p>${listing.product_type || ''} • ${listing.quantity_available || ''} ${listing.unit || ''} disponible(s)</p>
                <p>Prix unitaire: ${listing.price_per_unit?.toLocaleString() || 0} ${order.currency || 'XOF'}</p>

                <h4>Détails de la commande</h4>
                <p><strong>Quantité commandée :</strong> ${order.quantity} ${listing.unit || ''}</p>
                <p><strong>Montant total :</strong> ${order.total_price?.toLocaleString() || 0} ${order.currency || 'XOF'}</p>
                <p><strong>Statut commande :</strong> ${order.status}</p>
                <p><strong>Date de commande :</strong> ${new Date(order.created_at).toLocaleDateString('fr-FR')}</p>
                ${order.updated_at ? `<p><strong>Dernière mise à jour :</strong> ${new Date(order.updated_at).toLocaleDateString('fr-FR')}</p>` : ''}

                <h4>Informations de livraison</h4>
                <p><strong>Destinataire :</strong> ${order.recipient_name || 'N/A'}</p>
                <p><strong>Adresse de livraison :</strong> ${order.shipping_address || 'N/A'}</p>
                ${order.order_notes ? `<p><strong>Instructions :</strong> ${order.order_notes}</p>` : ''}

                <h4>Informations de paiement</h4>
                <div class="payment-info">
                    <p><strong>Méthode de paiement :</strong> ${this.formatPaymentMethod(order.payment_method || payment.payment_method)}</p>
                    <p><strong>Statut du paiement :</strong> <span class="payment-status ${payment.status || 'pending'}">${this.formatPaymentStatus(payment.status || (order.status === 'paid' ? 'completed' : 'pending'))}</span></p>
                    ${payment.payment_provider ? `<p><strong>Fournisseur :</strong> ${payment.payment_provider}</p>` : ''}
                    ${payment.transaction_id ? `<p><strong>Référence transaction :</strong> ${payment.transaction_id}</p>` : ''}
                    ${payment.blockchain_tx_hash ? `<p><strong>Hash blockchain :</strong> <code class="tx-hash">${payment.blockchain_tx_hash}</code></p>` : ''}
                    ${payment.processed_at ? `<p><strong>Date de paiement :</strong> ${new Date(payment.processed_at).toLocaleString('fr-FR')}</p>` : ''}
                    ${payment.amount ? `<p><strong>Montant payé :</strong> ${payment.amount.toLocaleString()} ${payment.currency || 'XOF'}</p>` : ''}
                </div>

                ${transactionDetails.hash ? `
                <h4>Détails de transaction</h4>
                <div class="transaction-details">
                    <p><strong>Hash de transaction :</strong> <code>${transactionDetails.hash}</code></p>
                    <p><strong>Fournisseur :</strong> ${transactionDetails.provider || 'N/A'}</p>
                    <p><strong>Méthode :</strong> ${this.formatPaymentMethod(transactionDetails.method)}</p>
                    <p><strong>Référence :</strong> ${transactionDetails.reference || 'N/A'}</p>
                    <p><strong>Statut :</strong> <span class="payment-status ${transactionDetails.status || 'pending'}">${this.formatPaymentStatus(transactionDetails.status)}</span></p>
                    ${transactionDetails.timestamp ? `<p><strong>Timestamp :</strong> ${new Date(transactionDetails.timestamp).toLocaleString('fr-FR')}</p>` : ''}
                </div>
                ` : ''}

                <h4>Vendeur</h4>
                <p><strong>${seller.username || seller.full_name || 'N/A'}</strong></p>
                <p>${seller.email || 'Email non disponible'}</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="clientDashboard.closeModals()">Fermer</button>
                ${order.status === 'shipped' ? `<button type="button" class="btn-primary" onclick="clientDashboard.confirmDelivery(${order.id})">✅ Confirmer la livraison</button>` : ''}
                ${order.status === 'paid' && !order.review_left ? `<button type="button" class="btn-primary" onclick="clientDashboard.leaveReview(${order.id})">Laisser un avis</button>` : ''}
            </div>
        `;
    }

    async loadRequests() {
        try {
            const response = await fetch('/api/client/requests/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.displayRequests(data);
            }
        } catch (error) {
            console.error('Erreur chargement demandes:', error);
        }
    }

    displayRequests(data) {
        const loanContainer = document.getElementById('loan-requests-list');
        const insuranceContainer = document.getElementById('insurance-requests-list');
        loanContainer.innerHTML = '<h3>Demandes de prêt</h3>';
        insuranceContainer.innerHTML = '<h3>Demandes d\'assurance</h3>';

        const loans = data.loan_requests || [];
        const insurances = data.insurance_requests || [];

        if (loans.length === 0) {
            loanContainer.innerHTML += '<p class="no-data">Aucune demande de prêt.</p>';
        } else {
            loans.forEach(loan => {
                const loanCard = document.createElement('div');
                loanCard.className = 'item-card';
                loanCard.innerHTML = `
                    <h4>Prêt #${loan.id}</h4>
                    <p>Montant: ${loan.amount?.toLocaleString() || 0} XOF</p>
                    <p>Durée: ${loan.duration_months || 0} mois</p>
                    <p>Motif: ${loan.purpose || 'N/A'}</p>
                    <p>Statut: ${loan.status}</p>
                    <p>Date: ${new Date(loan.requested_date).toLocaleDateString()}</p>
                `;
                loanContainer.appendChild(loanCard);
            });
        }

        if (insurances.length === 0) {
            insuranceContainer.innerHTML += '<p class="no-data">Aucune demande d\'assurance.</p>';
        } else {
            insurances.forEach(insurance => {
                const insuranceCard = document.createElement('div');
                insuranceCard.className = 'item-card';
                insuranceCard.innerHTML = `
                    <h4>Assurance #${insurance.id}</h4>
                    <p>Type: ${insurance.type}</p>
                    <p>Prime: ${insurance.premium?.toLocaleString() || 0} XOF</p>
                    <p>Couverture: ${insurance.coverage?.toLocaleString() || 0} XOF</p>
                    <p>Durée: ${insurance.duration_months || 0} mois</p>
                    <p>Statut: ${insurance.status}</p>
                    <p>Date: ${new Date(insurance.requested_date).toLocaleDateString()}</p>
                `;
                insuranceContainer.appendChild(insuranceCard);
            });
        }
    }

    loadFavorites() {
        const container = document.getElementById('favorites-list');
        if (!container) return;

        const favorites = this.getFavorites();
        const favoriteIds = new Set(favorites.map(favorite => favorite.id));
        const favoriteListings = this.currentListings.filter(listing => favoriteIds.has(listing.id));

        if (!favoriteListings.length) {
            container.innerHTML = '<p class="no-data">Vous n’avez pas encore ajouté de favoris.</p>';
            document.getElementById('favorites-count').textContent = '0';
            return;
        }

        document.getElementById('favorites-count').textContent = favoriteListings.length;
        container.innerHTML = favoriteListings.map(listing => `
            <div class="item-card marketplace-card">
                <img src="${ImageManager.getMainImage(listing.images)}" alt="${listing.title}" class="listing-image" onerror="this.src='${ImageManager.getPlaceholder()}'">
                <div class="listing-info">
                    <h4>${listing.title}</h4>
                    <p class="listing-description">${(listing.description || 'Aucune description').substring(0, 90)}...</p>
                    <div class="listing-price">
                        <span class="price">${Number(listing.price_per_unit || 0).toLocaleString()} XOF</span>
                        <span class="unit">/${listing.unit || 'unité'}</span>
                    </div>
                    <div class="card-actions">
                        <button class="btn-primary" onclick="clientDashboard.viewListing(${listing.id})">Détails</button>
                        <button class="btn-secondary" onclick="clientDashboard.removeFromFavorites(${listing.id})">Retirer</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async loadReviews() {
        const container = document.getElementById('reviews-list');
        if (!container) return;
        container.innerHTML = '<p>Chargement des avis...</p>';

        try {
            const response = await fetch('/api/marketplace/reviews/user', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                container.innerHTML = '<p>Impossible de charger vos avis pour le moment.</p>';
                return;
            }

            const reviews = await response.json();
            if (!reviews.length) {
                container.innerHTML = '<p>Aucun avis publié pour le moment.</p>';
                return;
            }

            container.innerHTML = reviews.map(review => `
                <div class="review-card">
                    <div class="review-card-header">
                        <div>
                            <strong>${review.listing_title || 'Annonce'}</strong>
                            ${review.seller_name ? `<span class="review-seller">par ${review.seller_name}</span>` : ''}
                        </div>
                        <span class="rating">${'⭐'.repeat(review.rating)}</span>
                    </div>
                    <p>${review.comment || ''}</p>
                    <div class="review-card-meta">
                        <span>${review.is_verified_purchase ? 'Achat vérifié' : 'Avis libre'}</span>
                        <span>${new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Erreur chargement avis:', error);
            container.innerHTML = '<p>Impossible de charger vos avis.</p>';
        }
    }

    viewListing(listingId) {
        const listing = this.currentListings.find(l => l.id === listingId);
        if (!listing) return;

        const modal = document.getElementById('listing-modal');
        const details = document.getElementById('listing-details');
        const actions = document.querySelector('#listing-modal .modal-fixed-actions');

        const images = ImageManager.normalize(listing.images);
        const displayImages = images.length > 0 ? images : [ImageManager.getPlaceholder()];
        const mainImageId = `listing-main-image-${listingId}`;
        const thumbnailsId = `listing-thumbnails-${listingId}`;
        const description = listing.description || 'Aucune description disponible pour ce produit.';
        const category = listing.category || 'Autre';
        const price = Number(listing.price_per_unit || 0).toLocaleString();
        const quantity = listing.quantity || 0;
        const unit = listing.unit || 'unité';

        details.innerHTML = `
            <div class="listing-detail-card">
                <div class="listing-gallery">
                    <div class="gallery-main">
                        <img id="${mainImageId}" class="main-image" src="${displayImages[0]}" alt="${listing.title}" onerror="this.src='${ImageManager.getPlaceholder()}'">
                        <span class="image-count">1/${displayImages.length}</span>
                    </div>
                    ${displayImages.length > 1 ? `
                        <div class="gallery-thumbnails" id="${thumbnailsId}">
                            ${displayImages.map((image, index) => `
                                <img class="thumbnail ${index === 0 ? 'active' : ''}" src="${image}" alt="${listing.title} ${index + 1}" onclick="clientDashboard.switchImage('${mainImageId}', '${thumbnailsId}', '${image}', ${index + 1}, ${displayImages.length})" onerror="this.src='${ImageManager.getPlaceholder()}'">
                            `).join('')}
                        </div>
                    ` : ''}
                </div>

                <div class="listing-detail-info">
                    <h3>${listing.title}</h3>
                    <p class="listing-description-full">${description}</p>
                    <div class="listing-details-grid">
                        <div><strong>Prix :</strong> ${price} XOF/${unit}</div>
                        <div><strong>Quantité disponible :</strong> ${quantity} ${unit}</div>
                        <div><strong>Catégorie :</strong> ${category}</div>
                        <div><strong>Produit :</strong> ${listing.product_type || 'Non précisé'}</div>
                    </div>
                    <div id="listing-reviews-${listingId}" class="listing-reviews"></div>
                </div>
            </div>
        `;

        actions.innerHTML = `
            <button class="btn-primary" onclick="clientDashboard.createOrder(${listingId})">Commander</button>
            <button class="btn-secondary" onclick="clientDashboard.closeModals()">Fermer</button>
        `;

        modal.style.display = 'block';
        this.loadListingReviews(listingId);
    }

    switchImage(mainImageId, thumbnailsId, imageSrc, imageNum, totalImages) {
        // Update main image
        document.getElementById(mainImageId).src = imageSrc;

        // Update image count
        const countSpan = document.querySelector('.image-count');
        if (countSpan) {
            countSpan.textContent = `${imageNum}/${totalImages}`;
        }

        // Update thumbnail active state
        const thumbnailsContainer = document.getElementById(thumbnailsId);
        if (thumbnailsContainer) {
            thumbnailsContainer.querySelectorAll('.thumbnail').forEach((thumb, idx) => {
                thumb.classList.toggle('active', idx === imageNum - 1);
            });
        }
    }

    async loadListingReviews(listingId) {
        try {
            const response = await fetch(`/api/marketplace/listings/${listingId}/reviews`);
            if (response.ok) {
                const reviews = await response.json();
                const reviewsContainer = document.getElementById(`listing-reviews-${listingId}`);
                reviewsContainer.innerHTML = reviews.map(review => `
                    <div class="review">
                        <div class="review-header">
                            <span class="reviewer">${review.reviewer_name || 'Anonyme'}</span>
                            <span class="rating">${'⭐'.repeat(review.rating)}</span>
                        </div>
                        <p class="review-text">${review.comment}</p>
                        <span class="review-date">${new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                `).join('') || '<p>Aucun avis pour le moment.</p>';
            }
        } catch (error) {
            console.error('Erreur chargement avis:', error);
        }
    }

    async createOrder(listingId) {
        if (!this.currentUser) {
            alert('Vous devez être connecté pour commander.');
            window.location.href = '/login';
            return;
        }

        const userRole = this.currentUser.role || this.currentUser.account_type;
        if (userRole !== 'client' && !this.currentUser.is_admin) {
            alert('Votre compte ne peut pas passer de commande ici.');
            if (userRole === 'farmer') {
                window.location.href = '/farmer-dashboard';
            } else if (userRole === 'bank') {
                window.location.href = '/bank-dashboard';
            } else if (userRole === 'insurance') {
                window.location.href = '/insurance-dashboard';
            } else if (userRole === 'admin') {
                window.location.href = '/admin';
            } else {
                window.location.href = '/login';
            }
            return;
        }

        const listing = this.currentListings.find(l => l.id === listingId);
        if (!listing) {
            alert('Annonce introuvable.');
            return;
        }

        this.openOrderModal(listing);
    }

    openOrderModal(listing) {
        const modal = document.getElementById('order-modal');
        const container = document.getElementById('order-form-container');
        if (!modal || !container) return;

        container.innerHTML = `
            <div class="modal-header">
                <h3>Commander : ${listing.title}</h3>
            </div>
            <form id="listing-order-form">
                <div class="modal-body">
                    <p><strong>Prix unitaire :</strong> ${listing.price_per_unit.toLocaleString()} XOF / ${listing.unit}</p>
                    <p><strong>Quantité disponible :</strong> ${listing.quantity} ${listing.unit}</p>
                    <div class="form-group">
                        <label for="order-quantity">Quantité à commander</label>
                        <input id="order-quantity" name="quantity" type="number" min="1" max="${listing.quantity}" value="1" required>
                    </div>
                    <div class="form-group">
                        <label for="order-recipient">Nom du destinataire</label>
                        <input id="order-recipient" name="recipient_name" type="text" value="${this.currentUser.full_name || ''}" required>
                    </div>
                    <div class="form-group">
                        <label for="order-shipping">Adresse de livraison</label>
                        <textarea id="order-shipping" name="shipping_address" rows="3" required>${this.currentUser.region || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="order-payment">Mode de paiement</label>
                        <select id="order-payment" name="payment_method" required>
                            <option value="mobile_money">Mobile Money</option>
                            <option value="cash_on_delivery">Espèces à la livraison</option>
                            <option value="bank_transfer">Virement bancaire</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="order-provider">Fournisseur de paiement</label>
                        <input id="order-provider" name="payment_provider" type="text" placeholder="Orange Money, Wave, Banque..." required>
                    </div>
                    <div class="form-group">
                        <label for="order-transaction">Référence de transaction</label>
                        <input id="order-transaction" name="transaction_id" type="text" placeholder="Ex: TX123456789">
                    </div>
                    <div class="form-group">
                        <label for="order-notes">Instructions / conditions</label>
                        <textarea id="order-notes" name="order_notes" rows="3" placeholder="Ex: préférence de livraison, emballage, contact additionnel..."></textarea>
                    </div>
                    <p><strong>Total estimé :</strong> <span id="order-total">${listing.price_per_unit.toLocaleString()} XOF</span></p>
                    <p class="error-message" id="order-error-message"></p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-secondary" onclick="clientDashboard.closeModals()">Annuler</button>
                    <button type="submit" class="btn-primary">Confirmer la commande</button>
                </div>
            </form>
        `;

        modal.style.display = 'block';

        const orderForm = document.getElementById('listing-order-form');
        const quantityInput = document.getElementById('order-quantity');
        const totalElement = document.getElementById('order-total');

        quantityInput.addEventListener('input', () => {
            const quantity = parseInt(quantityInput.value, 10) || 0;
            const total = Math.max(0, Math.min(quantity, listing.quantity) * listing.price_per_unit);
            totalElement.textContent = `${total.toLocaleString()} XOF`;
        });

        orderForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            await this.submitOrder(listing);
        });
    }

    async submitOrder(listing) {
        const orderForm = document.getElementById('listing-order-form');
        const errorMessage = document.getElementById('order-error-message');
        if (!orderForm) return;

        errorMessage.textContent = '';

        const quantity = parseInt(orderForm.quantity.value, 10);
        const shippingAddress = orderForm.shipping_address.value.trim();
        const recipientName = orderForm.recipient_name.value.trim();
        const paymentMethod = orderForm.payment_method.value;
        const orderNotes = orderForm.order_notes.value.trim();

        if (!quantity || quantity < 1) {
            errorMessage.textContent = 'Veuillez saisir une quantité valide.';
            return;
        }

        if (quantity > listing.quantity) {
            errorMessage.textContent = `Quantité maximale disponible : ${listing.quantity} ${listing.unit}.`;
            return;
        }

        if (!shippingAddress) {
            errorMessage.textContent = 'L\'adresse de livraison est requise.';
            return;
        }

        if (!recipientName) {
            errorMessage.textContent = 'Le nom du destinataire est requis.';
            return;
        }

        const paymentProvider = orderForm.payment_provider.value.trim();
        const transactionIdInput = orderForm.transaction_id.value.trim();

        if (!paymentProvider) {
            errorMessage.textContent = 'Le fournisseur de paiement est requis.';
            return;
        }

        if (paymentMethod !== 'cash_on_delivery' && !transactionIdInput) {
            errorMessage.textContent = 'La référence de transaction est requise pour les paiements en ligne.';
            return;
        }

        try {
            const totalAmount = quantity * listing.price_per_unit;
            
            // Store order data for confirmation
            this.pendingOrder = {
                listing,
                quantity,
                shippingAddress,
                recipientName,
                paymentMethod,
                paymentProvider: orderForm.payment_provider.value.trim(),
                transactionId: orderForm.transaction_id.value.trim(),
                orderNotes,
                totalAmount
            };
            
            // Show confirmation modal
            this.showOrderConfirmationModal();
        } catch (error) {
            console.error('Erreur création commande:', error);
            errorMessage.textContent = 'Erreur lors de la création de la commande.';
        }
    }

    showOrderConfirmationModal() {
        if (!this.pendingOrder) return;
        
        const order = this.pendingOrder;
        const modal = document.getElementById('order-confirmation-modal') || this.createConfirmationModal();
        const content = document.getElementById('order-confirmation-content');
        
        if (!content) return;
        
        const paymentMethodLabel = {
            'mobile_money': 'Mobile Money',
            'cash_on_delivery': 'Espèces à la livraison',
            'bank_transfer': 'Virement bancaire'
        }[order.paymentMethod] || order.paymentMethod;
        
        content.innerHTML = `
            <div class="confirmation-summary">
                <h4>Récapitulatif de votre commande</h4>
                
                <div class="summary-section">
                    <h5>Produit</h5>
                    <p><strong>${order.listing.title}</strong></p>
                    <p>Prix unitaire: ${order.listing.price_per_unit.toLocaleString()} XOF / ${order.listing.unit}</p>
                    <p>Quantité: ${order.quantity} ${order.listing.unit}</p>
                </div>
                
                <div class="summary-section">
                    <h5>Livraison</h5>
                    <p><strong>Destinataire:</strong> ${order.recipientName}</p>
                    <p><strong>Adresse:</strong> ${order.shippingAddress}</p>
                </div>
                
                <div class="summary-section">
                    <h5>Paiement</h5>
                    <p><strong>Mode:</strong> ${paymentMethodLabel}</p>
                    <p><strong>Fournisseur:</strong> ${order.paymentProvider}</p>
                    ${order.transactionId ? `<p><strong>Référence:</strong> ${order.transactionId}</p>` : ''}
                </div>
                
                <div class="summary-section">
                    <h5>Total</h5>
                    <p style="font-size: 1.2em; font-weight: bold; color: #27ae60;">
                        ${order.totalAmount.toLocaleString()} XOF
                    </p>
                </div>
                
                <p style="margin-top: 20px; font-size: 0.9em; color: #666;">
                    ⚠️ Vérifiez tous les détails avant de confirmer votre commande.
                </p>
            </div>
        `;
        
        modal.style.display = 'block';
    }

    createConfirmationModal() {
        const modal = document.createElement('div');
        modal.id = 'order-confirmation-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Confirmation de Commande</h3>
                </div>
                <div class="modal-body" id="order-confirmation-content">
                    <!-- Content will be injected by showOrderConfirmationModal -->
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-secondary" onclick="clientDashboard.cancelOrder()">Annuler</button>
                    <button type="button" class="btn-primary" id="confirm-order-btn" onclick="clientDashboard.confirmAndSubmitOrder()">Confirmer la Commande</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    cancelOrder() {
        this.pendingOrder = null;
        this.closeModals();
    }

    async confirmAndSubmitOrder() {
        if (!this.pendingOrder) return;
        
        const order = this.pendingOrder;
        const listing = order.listing;
        const errorMessage = document.getElementById('order-error-message');
        
        try {
            const orderData = {
                listing_id: listing.id,
                quantity: order.quantity,
                shipping_address: order.shippingAddress,
                payment_method: order.paymentMethod,
                recipient_name: order.recipientName,
                order_notes: order.orderNotes
            };

            const createResponse = await fetch('/api/marketplace/orders/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                },
                body: JSON.stringify(orderData)
            });

            if (!createResponse.ok) {
                let errorText = 'Erreur lors de la création de la commande.';
                try {
                    const error = await createResponse.json();
                    errorText = error.detail || errorText;
                } catch {
                    errorText = await createResponse.text().catch(() => errorText);
                }
                if (errorMessage) errorMessage.textContent = errorText;
                return;
            }

            const createdOrder = await createResponse.json();
            let transactionId = order.transactionId;
            
            if (order.paymentMethod === 'cash_on_delivery' && !transactionId) {
                transactionId = `COD-${Date.now()}`;
            }

            const paymentResponse = await fetch(`/api/marketplace/orders/${createdOrder.id}/pay`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                },
                body: JSON.stringify({
                    payment_method: order.paymentMethod,
                    payment_provider: order.paymentProvider,
                    transaction_id: transactionId,
                    amount: order.totalAmount
                })
            });

            if (!paymentResponse.ok) {
                let paymentErrorText = 'Erreur lors du paiement de la commande.';
                try {
                    const paymentError = await paymentResponse.json();
                    paymentErrorText = paymentError.detail || paymentErrorText;
                } catch {
                    paymentErrorText = await paymentResponse.text().catch(() => paymentErrorText);
                }
                if (errorMessage) errorMessage.textContent = paymentErrorText;
                return;
            }

            let paymentResult = {};
            try {
                paymentResult = await paymentResponse.json();
            } catch {
                paymentResult = { status: 'ok' };
            }
            alert(`✅ Commande créée et paiement enregistré (${paymentResult.status || 'ok'}).`);
            this.pendingOrder = null;
            this.closeModals();
            this.loadOrders();
            if (this.currentListings.length) {
                listing.quantity = Math.max(0, listing.quantity - order.quantity);
                this.displayListings(this.currentListings);
            }
        } catch (error) {
            console.error('Erreur confirmation commande:', error);
            if (errorMessage) errorMessage.textContent = 'Erreur lors de la création de la commande.';
        }
    }

    getFavorites() {
        try {
            return JSON.parse(localStorage.getItem('client-favorites') || '[]');
        } catch {
            return [];
        }
    }

    saveFavorites(favorites) {
        localStorage.setItem('client-favorites', JSON.stringify(favorites));
    }

    addToFavorites(listingId) {
        const listing = this.currentListings.find(item => item.id === listingId);
        if (!listing) return;

        const favorites = this.getFavorites();
        if (favorites.some(item => item.id === listing.id)) {
            alert('Cet article est déjà dans vos favoris.');
            return;
        }

        favorites.push({
            id: listing.id,
            title: listing.title,
            description: listing.description,
            price_per_unit: listing.price_per_unit,
            unit: listing.unit,
            images: listing.images,
            category: listing.category,
            added_at: new Date().toISOString()
        });

        this.saveFavorites(favorites);
        this.loadFavorites();
        alert('✅ Article ajouté à vos favoris.');
    }

    removeFromFavorites(listingId) {
        const favorites = this.getFavorites().filter(item => item.id !== listingId);
        this.saveFavorites(favorites);
        this.loadFavorites();
    }

    async leaveReview(orderId) {
        try {
            const response = await fetch(`/api/marketplace/orders/${orderId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                alert('Impossible de charger la commande pour laisser un avis.');
                return;
            }

            const order = await response.json();
            this.pendingReviewOrder = order;

            const modal = document.getElementById('review-modal') || this.createReviewModal();
            const container = document.getElementById('review-form-container');
            if (!modal || !container) return;

            container.innerHTML = `
                <div class="modal-header">
                    <h3>Laisser un avis sur votre achat</h3>
                </div>
                <form id="review-form" class="review-form">
                    <div class="modal-body">
                        <div class="review-form-group">
                            <p><strong>Produit:</strong> <span>${order.listing?.title || 'N/A'}</span></p>
                            <p><strong>Vendeur:</strong> <span>${order.seller?.full_name || order.seller?.username || 'N/A'}</span></p>
                        </div>
                        
                        <div class="review-form-group">
                            <label>Votre note</label>
                            <div class="rating-input">
                                <div class="star-rating" id="star-rating">
                                    ${[1, 2, 3, 4, 5].map(i => `
                                        <span class="star" data-value="${i}" onclick="clientDashboard.setRating(${i})">★</span>
                                    `).join('')}
                                </div>
                                <span id="rating-text" style="margin-left: 0.5rem; color: #666; font-size: 0.95rem;"></span>
                                <input type="hidden" id="review-rating" name="rating" value="">
                            </div>
                        </div>
                        
                        <div class="review-form-group">
                            <label for="review-comment">Votre commentaire</label>
                            <textarea 
                                id="review-comment" 
                                name="comment" 
                                class="review-textarea"
                                placeholder="Partagez votre expérience avec ce produit. Qu'avez-vous aimé ? Qu'est-ce qui pourrait être amélioré ?" 
                                required>
                            </textarea>
                        </div>
                        
                        <p class="error-message" id="review-error-message"></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn-secondary" onclick="clientDashboard.closeModals()">Annuler</button>
                        <button type="submit" class="btn-primary">Publier l'avis</button>
                    </div>
                </form>
            `;

            modal.style.display = 'block';
            const reviewForm = document.getElementById('review-form');
            reviewForm.addEventListener('submit', async (event) => {
                event.preventDefault();
                await this.submitReview();
            });
        } catch (error) {
            console.error('Erreur ouverture modal d\'avis :', error);
            alert('Impossible d\'ouvrir le formulaire d\'avis.');
        }
    }

    createReviewModal() {
        const modal = document.createElement('div');
        modal.id = 'review-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div id="review-form-container">
                    <!-- Content will be injected by leaveReview -->
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    setRating(value) {
        const ratingInput = document.getElementById('review-rating');
        const ratingText = document.getElementById('rating-text');
        const stars = document.querySelectorAll('.star');
        
        if (ratingInput) ratingInput.value = value;
        
        const ratingLabels = {
            1: '1 - Insuffisant',
            2: '2 - Moyen',
            3: '3 - Bien',
            4: '4 - Très bien',
            5: '5 - Excellent'
        };
        
        if (ratingText) ratingText.textContent = ratingLabels[value] || '';
        
        stars.forEach((star, index) => {
            if (index < value) {
                star.classList.add('active');
            } else {
                star.classList.remove('active');
            }
        });
    }

    async submitReview() {
        const ratingSelect = document.getElementById('review-rating');
        const commentInput = document.getElementById('review-comment');
        const errorMessage = document.getElementById('review-error-message');
        if (!ratingSelect || !commentInput || !errorMessage) return;

        errorMessage.textContent = '';
        const rating = parseInt(ratingSelect.value, 10);
        const comment = commentInput.value.trim();

        if (!rating || rating < 1 || rating > 5) {
            errorMessage.textContent = 'Veuillez choisir une note valide entre 1 et 5.';
            return;
        }

        if (!comment) {
            errorMessage.textContent = 'Veuillez laisser un commentaire pour votre avis.';
            return;
        }

        if (!this.pendingReviewOrder) {
            errorMessage.textContent = 'Impossible de retrouver la commande associée.';
            return;
        }

        try {
            const payload = {
                listing_id: this.pendingReviewOrder.listing?.id,
                order_id: this.pendingReviewOrder.id,
                rating,
                comment,
                review_type: 'product'
            };

            const response = await fetch('/api/marketplace/reviews', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const body = await response.json();
                errorMessage.textContent = body.detail || 'Erreur lors de l\'envoi de votre avis.';
                return;
            }

            await response.json();
            alert('✅ Votre avis a été publié avec succès ! Merci de votre retour.');
            this.pendingReviewOrder = null;
            this.closeModals();
            this.loadReviews();
            if (this.pendingReviewOrder?.listing?.id) {
                this.loadListingReviews(this.pendingReviewOrder.listing.id);
            }
        } catch (error) {
            console.error('Erreur enregistrement avis:', error);
            errorMessage.textContent = 'Erreur lors de l\'enregistrement de l\'avis.';
        }
    }

    formatPaymentMethod(method) {
        const methods = {
            'mobile_money': 'Mobile Money',
            'cash_on_delivery': 'Espèces à la livraison',
            'bank_transfer': 'Virement bancaire',
            'card': 'Carte bancaire'
        };
        return methods[method] || method || 'N/A';
    }

    formatPaymentStatus(status) {
        const statuses = {
            'pending': 'En attente',
            'completed': 'Terminé',
            'failed': 'Échec',
            'refunded': 'Remboursé',
            'cancelled': 'Annulé'
        };
        return statuses[status] || status || 'Inconnu';
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }

    async confirmDelivery(orderId) {
        try {
            const response = await fetch('/api/payment-release/confirm-delivery', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                },
                body: JSON.stringify({ order_id: orderId })
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    alert('✅ Livraison confirmée ! Le paiement a été libéré au vendeur.');
                    this.closeModals();
                    this.loadOrders();
                } else {
                    alert('Erreur: ' + result.error);
                }
            } else {
                const error = await response.json();
                alert('Erreur: ' + (error.detail || 'Impossible de confirmer la livraison'));
            }
        } catch (error) {
            console.error('Erreur confirmation livraison:', error);
            alert('Erreur de connexion. Veuillez réessayer.');
        }
    }

    logout() {
        localStorage.removeItem('accessToken');
        window.location.href = '/login';
    }
}

async function syncOfflineData() {
    try {
        const response = await fetch('/api/offline/sync/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const result = await response.json();
            alert('📩 Résumé envoyé par SMS ! Vérifiez votre téléphone.');
        } else {
            const error = await response.json();
            alert('Erreur: ' + (error.detail || 'Impossible d\'envoyer le SMS'));
        }
    } catch (error) {
        console.error('Erreur sync offline:', error);
        alert('Erreur de connexion. Vérifiez que votre numéro de téléphone est configuré.');
    }
}

function initClientDashboard() {
    if (!window.clientDashboard) {
        window.clientDashboard = new ClientDashboard();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initClientDashboard);
} else {
    initClientDashboard();
}
