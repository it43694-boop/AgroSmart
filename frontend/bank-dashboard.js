// bank-dashboard.js - Logique pour le dashboard banque

class BankDashboard {
    constructor() {
        this.currentUser = null;
        this.init();
    }

    async init() {
        await this.checkAuth();
        this.setupEventListeners();
        this.loadDashboardData();
        this.loadPendingLoans();
        this.loadApprovedLoans();
    }

    async checkAuth() {
        try {
            const response = await fetch('https://agrosmart-vi8d.onrender.com/api/me', {
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

            // Vérifier que c'est une banque ou admin
            if (this.currentUser.role !== 'bank' && !this.currentUser.is_admin) {
                console.error('Access denied: not a bank. Role:', this.currentUser.role);
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
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.showSection(e.target.getAttribute('href').substring(1));
            });
        });

        document.getElementById('logout-btn').addEventListener('click', () => this.logout());

        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', () => this.closeModals());
        });

        const loanModal = document.getElementById('loan-modal');
        if (loanModal) {
            loanModal.addEventListener('click', (e) => {
                if (e.target === loanModal) {
                    this.closeModals();
                }
            });
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
            case 'loan-requests':
                this.loadPendingLoans();
                break;
            case 'approved-loans':
                this.loadApprovedLoans();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
        }
    }

    async loadDashboardData() {
        try {
            const response = await fetch('https://agrosmart-vi8d.onrender.com/api/bank/loans/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const loans = await response.json();
                this.updateOverview(loans);
            }
        } catch (error) {
            console.error('Erreur chargement dashboard:', error);
        }
    }

    updateOverview(data) {
        // Calculer les statistiques
        const allLoans = data || [];
        const pendingLoans = allLoans.filter(loan => loan.status === 'pending');
        const approvedLoans = allLoans.filter(loan => loan.status === 'approved');

        const totalLoaned = approvedLoans.reduce((sum, loan) => sum + (loan.amount || 0), 0);
        const approvalRate = allLoans.length > 0 ? Math.round((approvedLoans.length / allLoans.length) * 100) : 0;

        document.getElementById('pending-requests').textContent = pendingLoans.length;
        document.getElementById('approved-loans-count').textContent = approvedLoans.length;
        document.getElementById('total-loaned').textContent = `${totalLoaned.toLocaleString()} XOF`;
        document.getElementById('approval-rate').textContent = `${approvalRate}%`;
    }

    async loadPendingLoans() {
        try {
            const response = await fetch('https://agrosmart-vi8d.onrender.com/api/bank/loan-requests/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const loans = await response.json();
                this.displayLoans(loans, 'pending-loans-list', true);
            }
        } catch (error) {
            console.error('Erreur chargement demandes de prêt:', error);
        }
    }

    async loadApprovedLoans() {
        try {
            const response = await fetch('https://agrosmart-vi8d.onrender.com/api/bank/loans/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const loans = await response.json();
                const approvedLoans = loans.filter(loan => loan.status === 'approved');
                this.displayLoans(approvedLoans, 'approved-loans-list', false);
            }
        } catch (error) {
            console.error('Erreur chargement prêts approuvés:', error);
        }
    }

    displayLoans(loans, containerId, showActions = false) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        loans.forEach(loan => {
            const loanCard = document.createElement('div');
            loanCard.className = 'item-card';
            loanCard.innerHTML = `
                <h4>Demande de Prêt #${loan.id}</h4>
                <p><strong>Montant demandé:</strong> ${loan.amount?.toLocaleString() || 0} XOF</p>
                <p><strong>Durée:</strong> ${loan.duration_months || 0} mois</p>
                <p><strong>Motif:</strong> ${loan.purpose || 'N/A'}</p>
                <p><strong>Statut:</strong> <span class="status-${loan.status}">${loan.status}</span></p>
                <p><strong>Date de demande:</strong> ${new Date(loan.requested_date).toLocaleDateString()}</p>
                ${loan.approved_date ? `<p><strong>Date d'approbation:</strong> ${new Date(loan.approved_date).toLocaleDateString()}</p>` : ''}
                ${showActions ? `
                    <div class="card-actions">
                        <button class="btn-primary" onclick="bankDashboard.viewLoanDetails(${loan.id})">Voir Détails</button>
                        <button class="btn-success" onclick="bankDashboard.approveLoan(${loan.id})">Approuver</button>
                        <button class="btn-danger" onclick="bankDashboard.rejectLoan(${loan.id})">Rejeter</button>
                    </div>
                ` : ''}
            `;
            container.appendChild(loanCard);
        });

        if (loans.length === 0) {
            container.innerHTML = '<p class="no-data">Aucun prêt trouvé.</p>';
        }
    }

    loadAnalytics() {
        // Créer des graphiques d'analyse
        this.createLoansChart();
        this.createRegionsChart();
    }

    async createLoansChart() {
        try {
            const response = await fetch('https://agrosmart-vi8d.onrender.com/api/bank/loans/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const loans = await response.json();

                // Grouper par mois
                const loansByMonth = {};
                loans.forEach(loan => {
                    const date = new Date(loan.requested_date || loan.approved_date || Date.now());
                    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                    loansByMonth[monthKey] = (loansByMonth[monthKey] || 0) + 1;
                });

                const ctx = document.getElementById('loans-chart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: Object.keys(loansByMonth).sort(),
                        datasets: [{
                            label: 'Nombre de demandes de prêt',
                            data: Object.values(loansByMonth),
                            borderColor: '#2196F3',
                            backgroundColor: 'rgba(33, 150, 243, 0.1)',
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
        } catch (error) {
            console.error('Erreur création graphique prêts:', error);
        }
    }

    async createRegionsChart() {
        try {
            const response = await fetch('https://agrosmart-vi8d.onrender.com/api/bank/loans/', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const loans = await response.json();

                const loansByStatus = {};
                loans.forEach(loan => {
                    const status = loan.status || 'unknown';
                    loansByStatus[status] = (loansByStatus[status] || 0) + 1;
                });

                const ctx = document.getElementById('regions-chart').getContext('2d');
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(loansByStatus),
                        datasets: [{
                            data: Object.values(loansByStatus),
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
                        responsive: true
                    }
                });
            }
        } catch (error) {
            console.error('Erreur création graphique régions:', error);
        }
    }

    async viewLoanDetails(loanId) {
        try {
            const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/bank/loans/${loanId}/`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (!response.ok) {
                alert('Impossible de charger les détails du prêt.');
                return;
            }

            const loan = await response.json();
            const details = `
                <div class="loan-detail-grid">
                    <p><strong>Montant demandé :</strong> ${loan.amount?.toLocaleString() || 0} XOF</p>
                    <p><strong>Durée :</strong> ${loan.duration_months || 0} mois</p>
                    <p><strong>Motif :</strong> ${loan.purpose || 'N/A'}</p>
                    <p><strong>Statut :</strong> ${loan.status || 'N/A'}</p>
                    <p><strong>Date de demande :</strong> ${new Date(loan.requested_date).toLocaleDateString()}</p>
                    ${loan.approved_date ? `<p><strong>Date d'approbation :</strong> ${new Date(loan.approved_date).toLocaleDateString()}</p>` : ''}
                    <p><strong>Taux d'intérêt :</strong> ${loan.interest_rate ? loan.interest_rate + '%': 'N/A'}</p>
                    <p><strong>Score de risque :</strong> ${loan.risk_score ?? 'N/A'}</p>
                </div>
            `;

            document.getElementById('loan-details').innerHTML = details;
            document.getElementById('loan-modal').style.display = 'flex';
        } catch (error) {
            console.error('Erreur chargement détails prêt:', error);
            alert('Impossible de charger les détails du prêt.');
        }
    }

    async approveLoan(loanId) {
        if (!confirm('Êtes-vous sûr de vouloir approuver ce prêt ?')) return;

        try {
            const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/bank/loans/${loanId}/approve/`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                alert('Prêt approuvé avec succès !');
                this.loadPendingLoans();
                this.loadDashboardData();
            } else {
                alert('Erreur lors de l\'approbation du prêt');
            }
        } catch (error) {
            console.error('Erreur approbation prêt:', error);
            alert('Erreur lors de l\'approbation du prêt');
        }
    }

    async rejectLoan(loanId) {
        if (!confirm('Êtes-vous sûr de vouloir rejeter ce prêt ?')) return;

        try {
            const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/bank/loans/${loanId}/reject/`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                alert('Prêt rejeté');
                this.loadPendingLoans();
                this.loadDashboardData();
            } else {
                alert('Erreur lors du rejet du prêt');
            }
        } catch (error) {
            console.error('Erreur rejet prêt:', error);
            alert('Erreur lors du rejet du prêt');
        }
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }

    logout() {
        localStorage.removeItem('accessToken');
        window.location.href = '/login';
    }
}

async function syncOfflineData() {
    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/offline/sync/me', {
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

function scrollToInsights() {
    const insightGrid = document.querySelector('.insight-grid');
    if (insightGrid) {
        insightGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Initialiser le dashboard quand le DOM est chargé
document.addEventListener('DOMContentLoaded', () => {
    window.bankDashboard = new BankDashboard();
    
    // Attacher l'événement au bouton insights
    const insightsBtn = document.getElementById('insights-btn');
    if (insightsBtn) {
        insightsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const insightSection = document.getElementById('insights-section');
            if (insightSection) {
                insightSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }
});
