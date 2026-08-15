// insurance-dashboard.js - Logique pour le dashboard assurance

class InsuranceDashboard {
    constructor() {
        this.currentUser = null;
        this.init();
    }

    async init() {
        await this.checkAuth();
        this.setupEventListeners();
        this.loadDashboardData();
        this.loadCharts();
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

            // Vérifier que c'est une assurance ou admin
            if (this.currentUser.role !== 'insurance' && !this.currentUser.is_admin) {
                console.error('Access denied: not an insurance. Role:', this.currentUser.role);
                localStorage.removeItem('accessToken');
                window.location.href = this.currentUser.dashboard || '/login';
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

        const contractsBtn = document.getElementById('contracts-btn');
        if (contractsBtn) {
            contractsBtn.addEventListener('click', () => this.viewKeyContracts());
        }

        // Déconnexion
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }
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
            case 'insurance-requests':
                this.loadPendingInsurances();
                break;
            case 'approved-insurances':
                this.loadApprovedInsurances();
                break;
            case 'claims':
                this.loadClaims();
                break;
        }
    }

    async viewKeyContracts() {
        try {
            const response = await fetch('/api/insurance/policies/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                alert('Impossible de charger les contrats clés.');
                return;
            }

            const contracts = await response.json();
            const activeContracts = (contracts || []).slice(0, 3);
            if (!activeContracts.length) {
                alert('Aucun contrat disponible pour le moment.');
                return;
            }

            const summary = activeContracts.map(contract => {
                return `#${contract.id} • ${contract.type || 'Assurance'} • ${Number(contract.coverage || 0).toLocaleString()} XOF`; 
            }).join('\n');

            alert('Contrats actifs:\n' + summary);
        } catch (error) {
            console.error('Erreur chargement contrats clés:', error);
            alert('Impossible d’afficher les contrats clés.');
        }
    }

    async loadDashboardData() {
        try {
            const response = await fetch('/api/insurance/policies/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const insurances = await response.json();
                this.updateOverview(insurances);
            }
        } catch (error) {
            console.error('Erreur chargement dashboard:', error);
        }
    }

    updateOverview(insurances) {
        const allInsurances = insurances || [];
        const pendingInsurances = allInsurances.filter(insurance => insurance.status === 'pending');
        const approvedInsurances = allInsurances.filter(insurance => insurance.status === 'approved');

        const totalPremium = approvedInsurances.reduce((sum, insurance) => sum + (insurance.premium || 0), 0);
        const totalCoverage = approvedInsurances.reduce((sum, insurance) => sum + (insurance.coverage || 0), 0);

        document.getElementById('pending-requests').textContent = pendingInsurances.length;
        document.getElementById('approved-insurances-count').textContent = approvedInsurances.length;
        document.getElementById('total-premium').textContent = `${totalPremium.toLocaleString()} XOF`;
        document.getElementById('total-coverage').textContent = `${totalCoverage.toLocaleString()} XOF`;
    }

    async loadPendingInsurances() {
        try {
            const response = await fetch('/api/insurance/policy-requests/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const insurances = await response.json();
                this.displayInsurances(insurances, 'pending-insurances-list', true);
            }
        } catch (error) {
            console.error('Erreur chargement demandes d\'assurance:', error);
        }
    }

    async loadApprovedInsurances() {
        try {
            const response = await fetch('/api/insurance/policies/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const insurances = await response.json();
                const approvedInsurances = insurances.filter(insurance => insurance.status === 'approved');
                this.displayInsurances(approvedInsurances, 'approved-insurances-list', false);
            }
        } catch (error) {
            console.error('Erreur chargement assurances approuvées:', error);
        }
    }

    displayInsurances(insurances, containerId, showActions = false) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        insurances.forEach(insurance => {
            const insuranceCard = document.createElement('div');
            insuranceCard.className = 'item-card';
            insuranceCard.innerHTML = `
                <h4>Demande d'Assurance #${insurance.id}</h4>
                <p><strong>Type:</strong> ${insurance.type || 'N/A'}</p>
                <p><strong>Prime:</strong> ${insurance.premium?.toLocaleString() || 0} XOF</p>
                <p><strong>Couverture:</strong> ${insurance.coverage?.toLocaleString() || 0} XOF</p>
                <p><strong>Durée:</strong> ${insurance.duration_months || 0} mois</p>
                <p><strong>Statut:</strong> <span class="status-${insurance.status}">${insurance.status}</span></p>
                <p><strong>Date de demande:</strong> ${new Date(insurance.requested_date).toLocaleDateString()}</p>
                ${insurance.approved_date ? `<p><strong>Date d'approbation:</strong> ${new Date(insurance.approved_date).toLocaleDateString()}</p>` : ''}
                ${showActions ? `
                    <div class="card-actions">
                        <button class="btn-primary" onclick="insuranceDashboard.viewInsuranceDetails(${insurance.id})">Voir Détails</button>
                        <button class="btn-success" onclick="insuranceDashboard.approveInsurance(${insurance.id})">Approuver</button>
                        <button class="btn-danger" onclick="insuranceDashboard.rejectInsurance(${insurance.id})">Rejeter</button>
                    </div>
                ` : ''}
            `;
            container.appendChild(insuranceCard);
        });

        if (insurances.length === 0) {
            container.innerHTML = '<p class="no-data">Aucune assurance trouvée.</p>';
        }
    }

    async loadClaims() {
        const container = document.getElementById('claims-list');
        if (!container) return;
        container.innerHTML = '<p class="no-data">Chargement des sinistres...</p>';

        try {
            const response = await fetch('/api/insurance/claims/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                throw new Error('Impossible de charger les sinistres');
            }

            const claims = await response.json();
            if (!claims.length) {
                container.innerHTML = '<p class="no-data">Aucun sinistre à traiter pour le moment.</p>';
                return;
            }

            container.innerHTML = claims.map(claim => `
                <div class="item-card">
                    <h4>Sinistre #${claim.id}</h4>
                    <p><strong>Assurance:</strong> #${claim.insurance_id}</p>
                    <p><strong>Type:</strong> ${claim.type}</p>
                    <p><strong>Région:</strong> ${claim.region}</p>
                    <p><strong>Montant:</strong> ${Number(claim.amount || 0).toLocaleString()} XOF</p>
                    <p><strong>Statut:</strong> <span class="status-${claim.status}">${claim.status}</span></p>
                    <p>${claim.description}</p>
                </div>
            `).join('');
        } catch (error) {
            console.error('Erreur chargement sinistres:', error);
            container.innerHTML = '<p class="no-data">Impossible de charger les sinistres.</p>';
        }
    }

    async viewInsuranceDetails(insuranceId) {
        try {
            const response = await fetch('/api/insurance/policies/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                throw new Error('Impossible de charger les détails');
            }

            const insurances = await response.json();
            const insurance = insurances.find(item => item.id === insuranceId);
            if (!insurance) {
                alert('Assurance introuvable.');
                return;
            }

            const details = `
                <div class="item-card">
                    <h4>Détails de l'assurance #${insurance.id}</h4>
                    <p><strong>Type:</strong> ${insurance.type || 'N/A'}</p>
                    <p><strong>Prime:</strong> ${Number(insurance.premium || 0).toLocaleString()} XOF</p>
                    <p><strong>Couverture:</strong> ${Number(insurance.coverage || 0).toLocaleString()} XOF</p>
                    <p><strong>Statut:</strong> ${insurance.status}</p>
                    <p><strong>Date de demande:</strong> ${new Date(insurance.requested_date).toLocaleDateString()}</p>
                    ${insurance.approved_date ? `<p><strong>Date d'approbation:</strong> ${new Date(insurance.approved_date).toLocaleDateString()}</p>` : ''}
                </div>
            `;
            alert(details.replace(/<[^>]*>/g, ''));
        } catch (error) {
            console.error('Erreur détails assurance:', error);
            alert('Impossible d’afficher les détails de l’assurance.');
        }
    }

    async approveInsurance(insuranceId) {
        if (!confirm('Êtes-vous sûr de vouloir approuver cette assurance ?')) return;

        try {
            const response = await fetch(`/api/insurance/${insuranceId}/approve/`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                alert('Assurance approuvée avec succès !');
                this.loadPendingInsurances();
                this.loadDashboardData();
            } else {
                alert('Erreur lors de l\'approbation de l\'assurance');
            }
        } catch (error) {
            console.error('Erreur approbation assurance:', error);
            alert('Erreur lors de l\'approbation de l\'assurance');
        }
    }

    async rejectInsurance(insuranceId) {
        if (!confirm('Êtes-vous sûr de vouloir rejeter cette assurance ?')) return;

        try {
            const response = await fetch(`/api/insurance/${insuranceId}/reject/`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                alert('Assurance rejetée');
                this.loadPendingInsurances();
                this.loadDashboardData();
            } else {
                alert('Erreur lors du rejet de l\'assurance');
            }
        } catch (error) {
            console.error('Erreur rejet assurance:', error);
            alert('Erreur lors du rejet de l\'assurance');
        }
    }

    logout() {
        localStorage.removeItem('accessToken');
        window.location.href = '/login';
    }

    async loadCharts() {
        try {
            const response = await fetch('/api/insurance/policies/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const insurances = await response.json();
                this.createPremiumChart(insurances);
                this.createClaimsChart(insurances);
            }
        } catch (error) {
            console.error('Erreur chargement graphiques:', error);
        }
    }

    createPremiumChart(insurances) {
        const ctx = document.getElementById('premium-chart');
        if (!ctx || typeof Chart === 'undefined') return;

        const premiumsByMonth = {};
        insurances.forEach(insurance => {
            const date = new Date(insurance.requested_date || insurance.approved_date || Date.now());
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            premiumsByMonth[monthKey] = (premiumsByMonth[monthKey] || 0) + (insurance.premium || 0);
        });

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: Object.keys(premiumsByMonth).sort(),
                datasets: [{
                    label: 'Primes (XOF)',
                    data: Object.values(premiumsByMonth),
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + ' XOF';
                            }
                        }
                    }
                }
            }
        });
    }

    createClaimsChart(insurances) {
        const ctx = document.getElementById('claims-chart');
        if (!ctx || typeof Chart === 'undefined') return;

        const claimsByRegion = {};
        insurances.forEach(insurance => {
            const region = insurance.region || 'Autre';
            claimsByRegion[region] = (claimsByRegion[region] || 0) + 1;
        });

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(claimsByRegion),
                datasets: [{
                    label: 'Nombre de sinistres',
                    data: Object.values(claimsByRegion),
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF',
                        '#FF9F40'
                    ]
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

// Initialiser le dashboard quand le DOM est chargé
document.addEventListener('DOMContentLoaded', () => {
    window.insuranceDashboard = new InsuranceDashboard();
});
