
        function getAdminToken() {
            // Return stored token from localStorage, or empty string (no ADMIN_SECRET needed in dev)
            return localStorage.getItem('adminToken') || '';
        }

        

        async function triggerImmediateRetrain() {
            if (!confirm('Lancer un réentrainement immédiat ?')) return;
            try {
                const result = await fetchAPI('/admin/auto-retrain', 'POST', null, true);
                if (result.status !== 200 && result.status !== 201) {
                    alert('Erreur: ' + (result.data?.detail || result.status));
                    return;
                }
                const j = result.data || {};
                const log = document.getElementById('schedulerLog');
                log.innerText = 'Réentrainement démarré, job_id: ' + (j.job_id || 'n/a') + '\n' + (log.innerText || '');
                refreshScheduleStatus();
            } catch (e) {
                console.error(e);
                alert('Erreur démarrage réentrainement. Voir console.');
            }
        }

        async function startSchedule() {
            const interval = parseInt(document.getElementById('scheduleInterval').value || '1440', 10);
            try {
                const result = await fetchAPI('/admin/auto-retrain/schedule', 'POST', { interval_minutes: interval }, true);
                const j = result.data || {};
                const log = document.getElementById('schedulerLog');
                log.innerText = 'Schedule response: ' + JSON.stringify(j) + '\n' + (log.innerText || '');
                refreshScheduleStatus();
            } catch (e) { console.error(e); alert('Erreur démarrage planning.'); }
        }

        async function stopSchedule() {
            try {
                const result = await fetchAPI('/admin/auto-retrain/schedule', 'DELETE', null, true);
                const j = result.data || {};
                const log = document.getElementById('schedulerLog');
                log.innerText = 'Stop response: ' + JSON.stringify(j) + '\n' + (log.innerText || '');
                refreshScheduleStatus();
            } catch (e) { console.error(e); alert('Erreur arrêt planning.'); }
        }

        async function refreshScheduleStatus() {
            try {
                const result = await fetchAPI('/admin/auto-retrain/schedule', 'GET', null, true);
                if (result.status !== 200) { document.getElementById('schedulerStatus').innerText = 'Statut: erreur'; return; }
                const j = result.data || {};
                document.getElementById('schedulerStatus').innerText = 'Statut: ' + (j.enabled ? 'activé' : 'désactivé') + ' — interval: ' + (j.interval_minutes || '—') + ' min — last_run: ' + (j.last_run ? new Date(j.last_run*1000).toLocaleString() : '—');
            } catch (e) { console.error(e); document.getElementById('schedulerStatus').innerText = 'Statut: erreur'; }
        }
    