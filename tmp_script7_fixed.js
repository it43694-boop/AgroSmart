
        // Navigation
        function showSection(event, sectionId) {
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            document.querySelectorAll('.menu-link').forEach(link => {
                link.classList.remove('active');
            });
            const selected = document.getElementById(sectionId);
            if (selected) {
                selected.classList.add('active');
                // Scroll to the section
                setTimeout(() => {
                    selected.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 50);
            }
            // mark the matching menu-link active (works when called programmatically)
            try {
                const best = Array.from(document.querySelectorAll('.menu-link')).find(l => (l.getAttribute('onclick')||'').includes("'"+sectionId+"'") || (l.innerText||'').toLowerCase().includes((sectionId||'').toLowerCase()));
                if (best) best.classList.add('active');
                if (event && event.currentTarget) {
                    event.currentTarget.classList.add('active');
                }
            } catch (e) { console.warn('showSection: unable to set active link', e); }
        }

        // Modals
        function showModal(modalId) {
            document.getElementById(modalId).classList.add('active');
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('active');
        }

        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.classList.remove('active');
            }
        }

        // Actions
        async function changePassword() {
            try {
                const currentPassword = document.querySelector('#changePasswordModal input[type="password"]:nth-of-type(1)').value;
                const newPassword = document.querySelector('#changePasswordModal input[type="password"]:nth-of-type(2)').value;
                const confirmPassword = document.querySelector('#changePasswordModal input[type="password"]:nth-of-type(3)').value;
                
                if (!currentPassword || !newPassword || !confirmPassword) {
                    showAlert('❌ Veuillez remplir tous les champs', 'warning');
                    return;
                }
                
                if (newPassword !== confirmPassword) {
                    showAlert('❌ Les mots de passe ne correspondent pas', 'warning');
                    return;
                }
                
                if (newPassword.length < 8) {
                    showAlert('❌ Le mot de passe doit contenir au moins 8 caractères', 'warning');
                    return;
                }
                
                const headers = await getAuthHeaders();
                if (!headers) return;
                
                const result = await fetchAPI('/change-password', {
                    method: 'POST',
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword
                    })
                });
                
                if (result.status === 200) {
                    showAlert('✅ Mot de passe changé avec succès!', 'success');
                    closeModal('changePasswordModal');
                    document.querySelectorAll('#changePasswordModal input[type="password"]').forEach(input => input.value = '');
                } else {
                    showAlert('❌ Mot de passe actuel incorrect', 'danger');
                }
            } catch (e) {
                console.error('Erreur changement mot de passe:', e);
                showAlert('❌ Erreur lors du changement de mot de passe', 'danger');
            }
        }

        async function addUser() {
            try {
                const name = document.querySelector('#addUserModal input[type="text"]').value;
                const email = document.querySelector('#addUserModal input[type="email"]').value;
                const role = document.querySelector('#addUserModal select').value;
                
                if (!name || !email || !role) {
                    showAlert('❌ Veuillez remplir tous les champs obligatoires', 'warning');
                    return;
                }
                
                const result = await fetchAPI('/admin/users/', 'POST', { name: name, email: email, role: role }, true);
                
                if (result.status === 201) {
                    showAlert('✅ Utilisateur ajouté avec succès!', 'success');
                    closeModal('addUserModal');
                    document.querySelectorAll('#addUserModal input, #addUserModal select').forEach(input => input.value = '');
                    fetchAdminUsers();
                } else {
                    showAlert('❌ Erreur lors de l\'ajout de l\'utilisateur', 'danger');
                }
            } catch (e) {
                console.error('Erreur ajout utilisateur:', e);
                showAlert('❌ Erreur lors de l\'ajout de l\'utilisateur', 'danger');
            }
        }

        async function addBank() {
            try {
                const name = document.querySelector('#addBankModal input[type="text"]').value;
                const code = document.querySelector('#addBankModal input[type="text"]:nth-of-type(2)').value;
                const contactEmail = document.querySelector('#addBankModal input[type="email"]').value;
                
                if (!name || !code || !contactEmail) {
                    showAlert('❌ Veuillez remplir tous les champs obligatoires', 'warning');
                    return;
                }
                
                const result = await fetchAPI('/admin/banks/', 'POST', { name: name, code: code, contact_email: contactEmail }, true);
                
                if (result.status === 201) {
                    showAlert('✅ Banque partenaire ajoutée avec succès!', 'success');
                    closeModal('addBankModal');
                    document.querySelectorAll('#addBankModal input').forEach(input => input.value = '');
                    fetchBanks();
                } else {
                    showAlert('❌ Erreur lors de l\'ajout de la banque', 'danger');
                }
            } catch (e) {
                console.error('Erreur ajout banque:', e);
                showAlert('❌ Erreur lors de l\'ajout de la banque', 'danger');
            }
        }

        async function addInsurance() {
            try {
                const name = document.querySelector('#addInsuranceModal input[type="text"]').value;
                const code = document.querySelector('#addInsuranceModal input[type="text"]:nth-of-type(2)').value;
                const contactEmail = document.querySelector('#addInsuranceModal input[type="email"]').value;
                
                if (!name || !code || !contactEmail) {
                    showAlert('❌ Veuillez remplir tous les champs obligatoires', 'warning');
                    return;
                }
                
                const result = await fetchAPI('/admin/insurances/', 'POST', { name: name, code: code, contact_email: contactEmail }, true);
                
                if (result.status === 201) {
                    showAlert('✅ Assurance partenaire ajoutée avec succès!', 'success');
                    closeModal('addInsuranceModal');
                    document.querySelectorAll('#addInsuranceModal input').forEach(input => input.value = '');
                    fetchInsurance();
                } else {
                    showAlert('❌ Erreur lors de l\'ajout de l\'assurance', 'danger');
                }
            } catch (e) {
                console.error('Erreur ajout assurance:', e);
                showAlert('❌ Erreur lors de l\'ajout de l\'assurance', 'danger');
            }
        }

        let adminActionContext = { action: null, userId: null, userName: null };

        function showAdminActionConfirm(action, userId, userName) {
            adminActionContext = { action, userId, userName };
            const message = {
                delete: `Voulez-vous vraiment supprimer l'utilisateur ${userName} ?`,
                block: `Voulez-vous bloquer l'utilisateur ${userName} ?`,
                unblock: `Voulez-vous débloquer l'utilisateur ${userName} ?`,
            }[action] || 'Êtes-vous sûr de vouloir effectuer cette action ?';
            document.getElementById('actionConfirmMessage').textContent = message;
            const confirmButton = document.getElementById('actionConfirmButton');
            confirmButton.textContent = action === 'delete' ? 'Supprimer' : action === 'block' ? 'Bloquer' : 'Débloquer';
            confirmButton.className = action === 'delete' ? 'btn btn-danger' : 'btn btn-warning';
            showModal('actionConfirmModal');
        }

        async function performAdminAction() {
            const { action, userId } = adminActionContext;
            if (!action || !userId) {
                closeModal('actionConfirmModal');
                return;
            }
            const headers = await getAuthHeaders();
            if (!headers) return;

            let method = 'PUT';
            let url = `/admin/users/${userId}/block/`;

            if (action === 'delete') {
                method = 'DELETE';
                url = `/admin/users/${userId}/`;
            } else if (action === 'unblock') {
                method = 'PUT';
                url = `/admin/users/${userId}/unblock/`;
            }

            const result = await fetchAPI(url, method, null, true);
            closeModal('actionConfirmModal');
            if (result.status === 200) {
                const successMessages = {
                    delete: 'Utilisateur supprimé avec succès.',
                    block: 'Utilisateur bloqué avec succès.',
                    unblock: 'Utilisateur débloqué avec succès.',
                };
                showAlert(successMessages[action] || 'Action effectuée.', action === 'delete' ? 'danger' : 'success');
                await fetchAdminUsers();
            } else {
                showAlert(result.data?.detail || 'Échec de l’action.', 'danger');
            }
        }

        function viewProfile(userId) {
            showAlert(`📋 Affichage du profil de l'utilisateur ${userId}.`, 'info');
        }

        function logout() {
            if (confirm('Êtes-vous sûr de vouloir vous déconnecter?')) {
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
                window.location.href = '/login';
            }
        }

        // Charger les données météo
        // Charger la météo
        async function loadWeather() {
            try {
                // Utiliser les coordonnées centrales du Mali
                const result = await fetchAPI('/weather/?lat=17.5707&lon=-3.9962');
                const weatherDiv = document.getElementById('weather');
                if (result.status === 200) {
                    const weather = result.data;
                    weatherDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-cloud-sun"></i> Météo Mali</div>
                        <div class="info-grid">
                            <div class="info-card">
                                <div class="info-label">Température</div>
                                <div class="info-value">${weather.temperature_celsius != null ? weather.temperature_celsius.toFixed(1) + '°C' : 'N/A'}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Résumé</div>
                                <div class="info-value">${weather.summary || 'N/A'}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Alerte</div>
                                <div class="info-value">${weather.alert || 'Aucune'}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Source</div>
                                <div class="info-value">${weather.source || 'N/A'}</div>
                            </div>
                        </div>
                        <div class="weather-forecast">
                            <strong>Prévisions 7 jours:</strong>
                            ${Array.isArray(weather.forecast) && weather.forecast.length ? `
                                <ul>
                                    ${weather.forecast.slice(0, 7).map((f, i) => `
                                        <li>${f}</li>
                                    `).join('')}
                                </ul>
                            ` : 'Aucune prévision disponible'}
                        </div>
                    `;
                } else {
                    weatherDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-cloud-sun"></i> Météo Mali</div>
                        <div class="info-box">Les données météo ne sont pas disponibles pour le moment. La section reste prête à recevoir les données dès que l'API répond.</div>
                    `;
                }
            } catch (e) {
                console.error('Erreur météo:', e);
                document.getElementById('weather').innerHTML = `
                    <div class="section-title"><i class="fas fa-cloud-sun"></i> Météo Mali</div>
                    <div class="info-box">Chargement météo interrompu. Vérifiez la connexion au service.</div>
                `;
            }
        }

        // Charger les cultures
        async function loadCrops() {
            try {
                const result = await fetchAPI('/admin/crops/', 'GET', null, true);
                const cropsDiv = document.getElementById('crops');
                if (result.status === 200) {
                    const cropsData = result.data;
                    const cropsRows = cropsData.data?.map(crop => `
                        <tr>
                            <td>${crop.name}</td>
                            <td>${crop.count}</td>
                            <td>${crop.surface_ha?.toFixed(2)} ha</td>
                        </tr>
                    `).join('') || '';
                    
                    cropsDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-leaf"></i> Cultures Admin</div>
                        <div class="info-grid">
                            <div class="info-card">
                                <div class="info-label">Total Cultures</div>
                                <div class="info-value">${cropsData.total_crops || 0}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Types Différents</div>
                                <div class="info-value">${cropsData.crop_types || 0}</div>
                            </div>
                        </div>
                        <table class="table" style="margin-top: 15px;">
                            <thead>
                                <tr>
                                    <th>Culture</th>
                                    <th>Nombre</th>
                                    <th>Surface Totale</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${cropsRows || '<tr><td colspan="3">Aucune culture</td></tr>'}
                            </tbody>
                        </table>
                    `;
                } else {
                    cropsDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-leaf"></i> Cultures Admin</div>
                        <div class="info-box">Aucune donnée de culture n’est disponible pour le moment. Les informations seront ajoutées dès que l’API répondra.</div>
                    `;
                }
            } catch (e) {
                console.error('Erreur cultures:', e);
                document.getElementById('crops').innerHTML = `
                    <div class="section-title"><i class="fas fa-leaf"></i> Cultures Admin</div>
                    <div class="info-box">Chargement des cultures interrompu.</div>
                `;
            }
        }

        // Charger les données financières
        async function loadFinance() {
            try {
                const result = await fetchAPI('/admin/finance/', 'GET', null, true);
                const financeDiv = document.getElementById('finance');
                if (result.status === 200) {
                    const financeData = result.data;
                    financeDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-money-bill"></i> Finance Admin</div>
                        <div class="info-grid">
                            <div class="info-card">
                                <div class="info-label">Revenu Total</div>
                                <div class="info-value" style="color: #27ae60;">${formatCurrency(financeData.total_revenue)}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Coût Total</div>
                                <div class="info-value" style="color: #e74c3c;">${formatCurrency(financeData.total_cost)}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Gain Net</div>
                                <div class="info-value" style="color: ${financeData.net_gain >= 0 ? '#27ae60' : '#e74c3c'};">${formatCurrency(financeData.net_gain)}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Records</div>
                                <div class="info-value">${financeData.total_records}</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 16px; color: #cbd5e1;">
                            <strong>Moyennes par enregistrement:</strong><br>
                            • Revenu: ${formatCurrency(financeData.average_revenue_per_record)}<br>
                            • Coût: ${formatCurrency(financeData.average_cost_per_record)}
                        </div>
                    `;
                } else {
                    financeDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-money-bill"></i> Finance Admin</div>
                        <div class="info-box">Les données financières sont actuellement indisponibles. La section reste en place pour l’affichage dès que les données seront disponibles.</div>
                    `;
                }
            } catch (e) {
                console.error('Erreur finances:', e);
                document.getElementById('finance').innerHTML = `
                    <div class="section-title"><i class="fas fa-money-bill"></i> Finance Admin</div>
                    <div class="info-box">Chargement financier interrompu.</div>
                `;
            }
        }

        // Charger l'analyse
        async function loadAnalytics() {
            try {
                const result = await fetchAPI('/admin/dashboard/', 'GET', null, true);
                const analyticsDiv = document.getElementById('analytics');
                if (result.status === 200) {
                    const dashboardData = result.data;
                    
                    analyticsDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-chart-bar"></i> Analyse & Dashboard</div>
                        <div class="info-grid">
                            <div class="info-card">
                                <div class="info-label">Utilisateurs Total</div>
                                <div class="info-value">${dashboardData.stats.total_users}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Validés</div>
                                <div class="info-value">${dashboardData.stats.validated_users}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Actifs</div>
                                <div class="info-value">${dashboardData.stats.active_users}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Prêts Approuvés</div>
                                <div class="info-value">${dashboardData.stats.approved_loans}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Assurances Approuvées</div>
                                <div class="info-value">${dashboardData.stats.approved_insurances}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Revenu Total</div>
                                <div class="info-value">${formatCurrency(dashboardData.stats.total_revenue)}</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px;">
                            <canvas id="analyticsChart" width="400" height="200"></canvas>
                        </div>
                    `;
                    
                    setTimeout(() => {
                        const chartCanvas = document.getElementById('analyticsChart');
                        if (chartCanvas) {
                            new Chart(chartCanvas, {
                                type: 'bar',
                                data: {
                                    labels: ['Utilisateurs', 'Validés', 'Actifs', 'Prêts', 'Assurances'],
                                    datasets: [{
                                        label: 'Statistiques Admin',
                                        data: [
                                            dashboardData.stats.total_users,
                                            dashboardData.stats.validated_users,
                                            dashboardData.stats.active_users,
                                            dashboardData.stats.approved_loans,
                                            dashboardData.stats.approved_insurances
                                        ],
                                        backgroundColor: [
                                            'rgba(54, 162, 235, 0.6)',
                                            'rgba(75, 192, 192, 0.6)',
                                            'rgba(255, 206, 86, 0.6)',
                                            'rgba(153, 102, 255, 0.6)',
                                            'rgba(255, 99, 132, 0.6)'
                                        ],
                                        borderColor: [
                                            'rgba(54, 162, 235, 1)',
                                            'rgba(75, 192, 192, 1)',
                                            'rgba(255, 206, 86, 1)',
                                            'rgba(153, 102, 255, 1)',
                                            'rgba(255, 99, 132, 1)'
                                        ],
                                        borderWidth: 1
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
                    }, 100);
                    
                } else {
                    analyticsDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-chart-bar"></i> Analyse & Dashboard</div>
                        <div class="info-box">Les analyses ne sont pas encore disponibles. La section s’affiche sans données pour éviter un écran vide.</div>
                    `;
                }
            } catch (e) {
                console.error('Erreur analyse:', e);
                document.getElementById('analytics').innerHTML = `
                    <div class="section-title"><i class="fas fa-chart-bar"></i> Analyse & Dashboard</div>
                    <div class="info-box">Chargement de l’analyse interrompu.</div>
                `;
            }
        }

        // Charger les alertes
        async function loadAlerts() {
            try {
                const result = await fetchAPI('/admin/alerts/', 'GET', null, true);
                const alertsDiv = document.getElementById('alerts');
                if (result.status === 200) {
                    const alerts = result.data;
                    const alertRows = alerts.slice(0, 10).map(alert => `
                        <tr>
                            <td><strong>${alert.title}</strong></td>
                            <td>${alert.message}</td>
                            <td><span class="status ${alert.severity?.toLowerCase() || 'info'}">${alert.severity || 'INFO'}</span></td>
                            <td>${new Date(alert.created_at).toLocaleDateString('fr-FR')}</td>
                        </tr>
                    `).join('');
                    
                    alertsDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-bell"></i> Alertes Système</div>
                        <div class="info-grid">
                            <div class="info-card">
                                <div class="info-label">Total Alertes</div>
                                <div class="info-value">${alerts.length}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Critiques</div>
                                <div class="info-value" style="color: #e74c3c;">${alerts.filter(a => a.severity === 'CRITICAL').length}</div>
                            </div>
                        </div>
                        <table class="table" style="margin-top: 15px;">
                            <thead>
                                <tr>
                                    <th>Titre</th>
                                    <th>Message</th>
                                    <th>Sévérité</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${alertRows || '<tr><td colspan="4">Aucune alerte</td></tr>'}
                            </tbody>
                        </table>
                    `;
                } else {
                    alertsDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-bell"></i> Alertes Système</div>
                        <div class="info-box">Aucune alerte n’a été reçue pour le moment.</div>
                    `;
                }
            } catch (e) {
                console.error('Erreur alertes:', e);
                document.getElementById('alerts').innerHTML = `
                    <div class="section-title"><i class="fas fa-bell"></i> Alertes Système</div>
                    <div class="info-box">Chargement des alertes interrompu.</div>
                `;
            }
        }

        // Charger le support
        async function loadSupport() {
            try {
                const result = await fetchAPI('/admin/support/', 'GET', null, true);
                const supportDiv = document.getElementById('support');
                if (result.status === 200) {
                    const messages = result.data;
                    const supportRows = messages.slice(0, 10).map(msg => `
                        <tr>
                            <td>${msg.subject}</td>
                            <td>${msg.message?.substring(0, 50) || 'N/A'}...</td>
                            <td><span class="status ${msg.status?.toLowerCase() || 'pending'}">${msg.status || 'PENDING'}</span></td>
                            <td>${new Date(msg.created_at).toLocaleDateString('fr-FR')}</td>
                            <td>
                                <button class="btn btn-sm btn-primary" onclick="viewSupportMessage(${msg.id})">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                    
                    supportDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-headset"></i> Support Client</div>
                        <div class="info-grid">
                            <div class="info-card">
                                <div class="info-label">Total Messages</div>
                                <div class="info-value">${messages.length}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">En Attente</div>
                                <div class="info-value" style="color: #f39c12;">${messages.filter(m => m.status === 'PENDING').length}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Répondus</div>
                                <div class="info-value" style="color: #27ae60;">${messages.filter(m => m.status === 'RESPONDED').length}</div>
                            </div>
                        </div>
                        <table class="table" style="margin-top: 15px;">
                            <thead>
                                <tr>
                                    <th>Sujet</th>
                                    <th>Message</th>
                                    <th>Status</th>
                                    <th>Date</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${supportRows || '<tr><td colspan="5">Aucun message support</td></tr>'}
                            </tbody>
                        </table>
                    `;
                } else {
                    supportDiv.innerHTML = `
                        <div class="section-title"><i class="fas fa-headset"></i> Support Client</div>
                        <div class="info-box">Aucun message de support n’est disponible pour le moment.</div>
                    `;
                }
            } catch (e) {
                console.error('Erreur support:', e);
                document.getElementById('support').innerHTML = `
                    <div class="section-title"><i class="fas fa-headset"></i> Support Client</div>
                    <div class="info-box">Chargement du support interrompu.</div>
                `;
            }
        }

        // Voir le détail d'un message support
        async function viewSupportMessage(messageId) {
            try {
                const result = await fetchAPI(`/admin/support/${messageId}/`, 'GET', null, true);
                if (result.status === 200) {
                    const message = result.data;
                    
                    // Créer une modal pour afficher le message
                    const modal = document.createElement('div');
                    modal.className = 'modal';
                    modal.innerHTML = `
                        <div class="modal-content modal-large">
                            <div class="modal-header">
                                <h3>Message Support #${message.id}</h3>
                                <span class="close" onclick="this.closest('.modal').remove()">&times;</span>
                            </div>
                            <div class="modal-body">
                                <div style="margin-bottom: 15px;">
                                    <strong>Sujet:</strong> ${message.subject}<br>
                                    <strong>De:</strong> ${message.user_email}<br>
                                    <strong>Date:</strong> ${new Date(message.created_at).toLocaleString('fr-FR')}<br>
                                    <strong>Status:</strong> <span class="status ${message.status?.toLowerCase()}">${message.status}</span>
                                </div>
                                <div style="margin-bottom: 15px;">
                                    <strong>Message:</strong><br>
                                    <div style="background: rgba(255,255,255,0.05); padding: 14px; border-radius: 16px; margin-top: 10px; color: #e2e8f0;">
                                        ${message.message}
                                    </div>
                                </div>
                                ${message.response ? `
                                    <div class="info-box-alt">
                                        <strong>Réponse:</strong><br>
                                        <div class="info-box" style="background: rgba(34,197,94,0.12); color: #e2e8f0; margin-top: 10px;">
                                            ${message.response}
                                        </div>
                                    </div>
                                ` : ''}
                                ${message.status === 'PENDING' ? `
                                    <div style="margin-top: 20px;">
                                        <label for="responseText"><strong>Répondre:</strong></label>
                                        <textarea id="responseText" rows="4" style="width: 100%; margin-top: 5px; padding: 12px 14px; border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; background: rgba(15,23,42,0.92); color: #f8fafc;"></textarea>
                                        <button class="btn btn-primary" style="margin-top: 10px;" onclick="respondToSupport(${message.id})">
                                            <i class="fas fa-reply"></i> Envoyer Réponse
                                        </button>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                    
                    document.body.appendChild(modal);
                    modal.style.display = 'block';
                }
            } catch (e) {
                console.error('Erreur chargement message:', e);
                showAlert('Erreur chargement message: ' + e.message, 'danger');
            }
        }

        // Répondre à un message support
        async function respondToSupport(messageId) {
            const responseText = document.getElementById('responseText').value.trim();
            if (!responseText) {
                showAlert('Veuillez saisir une réponse', 'warning');
                return;
            }
            
            try {
                const result = await fetchAPI(`/admin/support/${messageId}/respond/`, 'PUT', { response: responseText }, true);
                
                if (result.status === 200) {
                    showAlert('Réponse envoyée avec succès', 'success');
                    document.querySelector('.modal').remove();
                    loadSupport(); // Recharger la liste
                } else {
                    showAlert('Erreur lors de l\'envoi de la réponse', 'danger');
                }
            } catch (e) {
                console.error('Erreur réponse:', e);
                showAlert('Erreur réponse: ' + e.message, 'danger');
            }
        }

        // API functions
        const apiBase = (window.location.origin || '') + '/api';
        const accessTokenKey = 'accessToken';
        let accessToken = null;

        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        async function fetchAPI(endpoint, method = 'GET', body = null, auth = true) {
            const headers = {};
            const options = { method: method, headers: headers };

            if (auth) {
                accessToken = localStorage.getItem(accessTokenKey) || getCookie(accessTokenKey);
                if (!accessToken) {
                    // Don't force redirect here; surface a warning so the UI can decide
                    console.warn('fetchAPI: accessToken missing');
                    return { status: 401, data: { detail: 'Token manquant' } };
                }
                headers['Authorization'] = 'Bearer ' + accessToken;
            }

            if (body) {
                headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(body);
            }

            try {
                const response = await fetch(apiBase + endpoint, options);
                // try to parse JSON safely
                let data = null;
                const ct = response.headers.get('content-type') || '';
                if (ct.includes('application/json')) {
                    try { data = await response.json(); } catch (e) { data = null; }
                } else {
                    data = await response.text().catch(()=>null);
                }
                return { status: response.status, data: data };
            } catch (error) {
                console.error('fetchAPI error', endpoint, error);
                return { status: 0, data: { detail: error.message } };
            }
        }

        function formatDate(dateString) {
            if (!dateString) return '-';
            return new Date(dateString).toLocaleDateString('fr-FR');
        }

        function renderAdminUserRow(user) {
            const createdAt = formatDate(user.created_at);
            const statusLabel = user.is_validated ? 'Validé' : 'En attente';
            const statusClass = user.is_validated ? 'validated' : 'pending';
            return `
                <tr>
                    <td>${user.email}</td>
                    <td>${user.full_name}</td>
                    <td>${user.role || '-'}</td>
                    <td>${user.region || '-'}</td>
                    <td>${createdAt}</td>
                    <td><span class="status ${statusClass}">${statusLabel}</span></td>
                    <td>
                        <button class="btn-action" onclick="viewProfile(${user.id})"><i class="fas fa-eye"></i></button>
                        ${user.is_active ? `<button class="btn-action" onclick='showAdminActionConfirm("block", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-ban"></i></button>` : `<button class="btn-action" onclick='showAdminActionConfirm("unblock", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-lock-open"></i></button>`}
                        <button class="btn-action danger" onclick='showAdminActionConfirm("delete", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `;
        }

        async function fetchAdminUsers() {
            const result = await fetchAPI('/admin/users/', 'GET', null, true);
            console.log('DEBUG fetchAdminUsers result:', result && result.status, result && result.data && Array.isArray(result.data) ? result.data.length : result.data);
            if (result.status === 200) {
                const users = result.data;
                const tbody = document.getElementById('usersTableBody');
                tbody.innerHTML = users.map(renderAdminUserRow).join('');
            } else {
                showAlert('Impossible de charger la liste des utilisateurs.', 'danger');
            }
        }

        async function fetchRoleUsers(role) {
            const result = await fetchAPI(`/admin/users/?role=${encodeURIComponent(role)}`, 'GET', null, true);
            if (result.status === 200) {
                return result.data;
            }
            showAlert(`Impossible de charger les ${role}s.`, 'danger');
            return [];
        }

        async function fetchFarmers() {
            const users = await fetchRoleUsers('farmer');
            const tbody = document.getElementById('farmersTableBody');
            if (users.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" class="table-empty-state">
                            Aucune donnée d'agriculteur disponible pour le moment.
                        </td>
                    </tr>
                `;
                return;
            }
            tbody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.full_name}</td>
                    <td>${user.email}</td>
                    <td>${user.region || '-'}</td>
                    <td>${user.total_surface || 0} ha</td>
                    <td>${user.role || '-'}</td>
                    <td>${formatDate(user.created_at)}</td>
                    <td><span class="status ${user.is_validated ? 'validated' : 'pending'}">${user.is_validated ? 'Validé' : 'En attente'}</span></td>
                    <td>
                        <button class="btn-action" onclick="viewProfile(${user.id})"><i class="fas fa-eye"></i></button>
                        ${user.is_active ? `<button class="btn-action" onclick='showAdminActionConfirm("block", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-ban"></i></button>` : `<button class="btn-action" onclick='showAdminActionConfirm("unblock", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-lock-open"></i></button>`}
                        <button class="btn-action danger" onclick='showAdminActionConfirm("delete", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }

        async function fetchBanks() {
            const users = await fetchRoleUsers('bank');
            const tbody = document.getElementById('banksTableBody');
            if (users.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="table-empty-state">
                            Aucune banque partenaire disponible pour le moment.
                        </td>
                    </tr>
                `;
                return;
            }
            tbody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.full_name}</td>
                    <td>${user.email}</td>
                    <td>${user.region || '-'}</td>
                    <td>${user.role || '-'}</td>
                    <td><span class="status ${user.is_validated ? 'validated' : 'pending'}">${user.is_validated ? 'Validé' : 'En attente'}</span></td>
                    <td>
                        <button class="btn-action" onclick="viewProfile(${user.id})"><i class="fas fa-eye"></i></button>
                        ${user.is_active ? `<button class="btn-action" onclick='showAdminActionConfirm("block", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-ban"></i></button>` : `<button class="btn-action" onclick='showAdminActionConfirm("unblock", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-lock-open"></i></button>`}
                        <button class="btn-action danger" onclick='showAdminActionConfirm("delete", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }

        async function fetchInsurance() {
            const users = await fetchRoleUsers('insurance');
            const tbody = document.getElementById('insuranceTableBody');
            if (users.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="table-empty-state">
                            Aucune assurance partenaire disponible pour le moment.
                        </td>
                    </tr>
                `;
                return;
            }
            tbody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.full_name}</td>
                    <td>${user.email}</td>
                    <td>${user.region || '-'}</td>
                    <td>${user.role || '-'}</td>
                    <td><span class="status ${user.is_validated ? 'validated' : 'pending'}">${user.is_validated ? 'Validé' : 'En attente'}</span></td>
                    <td>
                        <button class="btn-action" onclick="viewProfile(${user.id})"><i class="fas fa-eye"></i></button>
                        ${user.is_active ? `<button class="btn-action" onclick='showAdminActionConfirm("block", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-ban"></i></button>` : `<button class="btn-action" onclick='showAdminActionConfirm("unblock", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-lock-open"></i></button>`}
                        <button class="btn-action danger" onclick='showAdminActionConfirm("delete", ${user.id}, ${JSON.stringify(user.full_name)})'><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');

            document.getElementById('insuranceCount').textContent = users.length;
            document.getElementById('insurancePendingCount').textContent = users.filter(u => !u.is_validated).length;
            document.getElementById('insuranceActiveCount').textContent = users.filter(u => u.is_validated).length;
            document.getElementById('insuranceCoverageCount').textContent = users.length;
        }

        function formatCurrency(value) {
            return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF' }).format(value || 0);
        }

        async function loadAdminStats() {
            const result = await fetchAPI('/admin/stats/', 'GET', null, true);
            if (result.status === 200) {
                const stats = result.data;
                document.getElementById('totalUsers').textContent = stats.total_users;
                document.getElementById('activeAgriculturists').textContent = stats.active_users;
                document.getElementById('total-revenue').textContent = formatCurrency(stats.total_revenue);
                document.getElementById('total-cost').textContent = formatCurrency(stats.total_cost);
                document.getElementById('net-profit').textContent = formatCurrency(stats.total_revenue - stats.total_cost);
            } else {
                document.getElementById('totalUsers').textContent = '—';
                document.getElementById('activeAgriculturists').textContent = '—';
                document.getElementById('total-revenue').textContent = formatCurrency(0);
                document.getElementById('total-cost').textContent = formatCurrency(0);
                document.getElementById('net-profit').textContent = formatCurrency(0);
            }
        }

        async function deleteUser(userId) {
            if (!confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ?')) {
                return;
            }
            const result = await fetchAPI(`/admin/users/${userId}/`, 'DELETE', null, true);
            if (result.status === 200) {
                showAlert('Utilisateur supprimé avec succès.', 'success');
                await fetchAdminUsers();
            } else {
                showAlert(result.data?.detail || 'Échec de la suppression.', 'danger');
            }
        }

        async function blockUser(userId) {
            if (!confirm('Bloquer cet utilisateur ?')) {
                return;
            }
            const result = await fetchAPI(`/admin/users/${userId}/block/`, 'PUT', null, true);
            if (result.status === 200) {
                showAlert('Utilisateur bloqué avec succès.', 'warning');
                await fetchAdminUsers();
            } else {
                showAlert(result.data?.detail || 'Échec du blocage.', 'danger');
            }
        }

        // Initialize
        async function initAdminDashboard() {
            await initCharts();

            const ok = await fetchCurrentAdmin();
            if (!ok) {
                console.warn('Admin validation failed — continuing with fallback section content');
            }

            // Load core lists
            await loadAdminStats();
            await fetchAdminUsers();
            await fetchFarmers();
            await fetchBanks();
            await fetchInsurance();

            // Charger tous les modules du dashboard (load in background, but failures are handled)
            loadWeather().catch(() => {});
            loadCrops().catch(() => {});
            loadFinance().catch(() => {});
            loadAnalytics().catch(() => {});
            loadAlerts().catch(() => {});
            loadSupport().catch(() => {});
        }

        if (document.readyState === 'loading') {
            window.addEventListener('DOMContentLoaded', initAdminDashboard);
        } else {
            initAdminDashboard();
        }

        // Alert Message
        function showAlert(message, type = 'info') {
            const alertEl = document.getElementById('successAlert');
            const msgEl = document.getElementById('alertMessage');
            msgEl.innerHTML = message;
            alertEl.className = `alert alert-${type} active`;
            setTimeout(() => {
                alertEl.classList.remove('active');
            }, 4000);
        }

        // Search Filter
        function filterTable(tableId, searchInputId) {
            const input = document.getElementById(searchInputId);
            const filter = input.value.toUpperCase();
            const table = document.getElementById(tableId);
            const tr = table.getElementsByTagName('tr');

            for (let i = 1; i < tr.length; i++) {
                const td = tr[i].getElementsByTagName('td')[0];
                if (td) {
                    const txtValue = td.textContent || td.innerText;
                    tr[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
                }
            }
        }

        async function getAuthHeaders() {
            const token = localStorage.getItem('accessToken');
            if (!token) {
                showAlert('Connexion requise. Veuillez vous reconnecter.', 'warning');
                return null;
            }
            return {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            };
        }

        async function fetchCurrentAdmin() {
            const result = await fetchAPI('/me', 'GET', null, true);
            if (result.status === 200 && result.data) {
                const user = result.data;
                if (!user.is_admin) {
                    console.warn('Accès refusé: compte non administrateur');
                    return false;
                }
                document.querySelector('.user-name').textContent = user.full_name || 'Administrateur';
                document.querySelector('.user-role').textContent = 'Administrateur';
                return true;
            }
            console.warn('Admin validation unavailable — continuing with fallback content');
            return false;
        }

        async function validatePendingUser(userId) {
            const result = await fetchAPI(`/admin/users/${userId}/validate/`, 'PUT', null, true);
            if (result.status === 200) {
                showAlert('Utilisateur validé avec succès.', 'success');
                await fetchAdminUsers();
            } else {
                showAlert(result.data?.detail || 'Échec de la validation.', 'danger');
            }
        }

        // Initialize Charts
        function initCharts() {
            const monthlyCtx = document.getElementById('monthlyChart');
            if (monthlyCtx) {
                new Chart(monthlyCtx, {
                    type: 'line',
                    data: {
                        labels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun'],
                        datasets: [{
                            label: 'Nouveaux Utilisateurs',
                            data: [12, 19, 15, 25, 22, 30],
                            borderColor: '#27ae60',
                            backgroundColor: 'rgba(39, 174, 96, 0.18)',
                            pointBackgroundColor: '#22c55e',
                            pointBorderColor: '#ffffff',
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            borderWidth: 3,
                            tension: 0.35,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#cbd5e1'
                                }
                            }
                        },
                        scales: {
                            x: {
                                ticks: {
                                    color: '#94a3b8'
                                },
                                grid: {
                                    color: 'rgba(255,255,255,0.05)',
                                    borderColor: 'rgba(255,255,255,0.12)'
                                }
                            },
                            y: {
                                ticks: {
                                    color: '#94a3b8'
                                },
                                grid: {
                                    color: 'rgba(255,255,255,0.05)',
                                    borderColor: 'rgba(255,255,255,0.12)'
                                }
                            }
                        }
                    }
                });
            }

            const geoCtx = document.getElementById('geoChart');
            if (geoCtx) {
                new Chart(geoCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Bamako', 'Sikasso', 'Ségou', 'Mopti'],
                        datasets: [{
                            data: [38, 22, 25, 15],
                            backgroundColor: [
                                '#27ae60',
                                '#3498db',
                                '#f39c12',
                                '#e74c3c'
                            ],
                            borderColor: '#0f172a',
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#cbd5e1'
                                }
                            }
                        }
                    }
                });
            }
        }
        