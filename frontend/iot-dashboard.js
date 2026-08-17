const iotUserIdKey = 'iotDashboardUserId';

async function loadIoTDashboard() {
  const errorBox = document.getElementById('iot-error');
  errorBox.classList.add('hidden');
  errorBox.textContent = '';

  const token = localStorage.getItem('accessToken');
  if (!token) {
    window.location.href = '/login.html';
    return;
  }

  try {
    let profileResponse;
    try {
      profileResponse = await fetchJson('/api/me', true);
    } catch (err) {
      console.error('fetch /me failed:', err);
      // Try to fetch raw text for better diagnostics (no auth header)
      try {
        const raw = await fetch('/api/me');
        const txt = await raw.text();
        throw new Error(txt || (err.message || 'Erreur lors de récupération de /me'));
      } catch (rawErr) {
        throw err;
      }
    }
    const userId = profileResponse.id;
    localStorage.setItem(iotUserIdKey, userId);

    const dashboard = await fetchJson(`/api/iot/dashboard/${userId}/`, true);
    const readings = await fetchJson(`/api/iot/sensors/${userId}/`, true);

    renderIoTDashboard(dashboard, readings);
  } catch (error) {
    const message = error.message || 'Impossible de charger les informations IoT.';
    if (message.toLowerCase().includes('not authenticated') || message.toLowerCase().includes('unauthorized')) {
      errorBox.textContent = 'Vous devez être connecté pour accéder au dashboard IoT. Veuillez vous connecter.';
    } else {
      errorBox.textContent = message;
    }
    errorBox.classList.remove('hidden');
  }
}

function renderIoTDashboard(dashboard, readings) {
  const statusEl = document.getElementById('iot-status');
  const maintenanceEl = document.getElementById('iot-maintenance');
  const actionEl = document.getElementById('iot-action');
  const resourceEl = document.getElementById('iot-resource');
  const alertEl = document.getElementById('iot-alert');
  const tableBody = document.getElementById('sensor-table-body');

  const isHealthy = dashboard.status === 'ok';
  statusEl.innerHTML = isHealthy
    ? '<span class="status-chip ok"><i class="fas fa-check-circle"></i> Toutes les installations sont stables</span>'
    : '<span class="status-chip alert"><i class="fas fa-exclamation-triangle"></i> Anomalies détectées</span>';

  maintenanceEl.textContent = dashboard.maintenance_due_in_days != null
    ? `Intervention attendue dans ${dashboard.maintenance_due_in_days} jour(s).`
    : 'Aucune maintenance imminente détectée.';
  actionEl.textContent = dashboard.recommended_action || 'Aucune action requise pour l’instant.';
  resourceEl.textContent = Object.entries(dashboard.resource_optimization || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join(' • ') || 'Pas de conseil de ressources disponible.';

  if (dashboard.predicted_alert && dashboard.predicted_alert !== 'Aucune alerte prédictive') {
    alertEl.innerHTML = `<strong>Alerte prédictive</strong><p>${dashboard.predicted_alert}</p>`;
    alertEl.classList.remove('hidden');
  } else {
    alertEl.classList.add('hidden');
  }

  const safeReadings = Array.isArray(readings) ? readings : [];
  if (!safeReadings.length) {
    tableBody.innerHTML = '<tr><td colspan="5" style="color: var(--muted); text-align: center; padding: 24px 0;">Aucune lecture de capteur disponible.</td></tr>';
    document.getElementById('iot-chart-placeholder').classList.remove('hidden');
  } else {
    tableBody.innerHTML = safeReadings.slice(0, 8).map(reading => `
      <tr>
        <td>${reading.sensor_type || 'Capteur'}</td>
        <td>${reading.value ?? '—'}</td>
        <td>${reading.unit || '—'}</td>
        <td>${reading.location || 'N/A'}</td>
        <td>${new Date(reading.timestamp).toLocaleString('fr-FR')}</td>
      </tr>
    `).join('');
    document.getElementById('iot-chart-placeholder').classList.add('hidden');
  }

  renderIoTChart(safeReadings);
}

function renderIoTChart(readings) {
  const ctx = document.getElementById('iot-readings-chart');
  if (!ctx) return;

  const labels = readings.map(reading => new Date(reading.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }));
  const values = readings.map(reading => Number(reading.value) || 0);

  if (window.iotChart) {
    window.iotChart.data.labels = labels;
    window.iotChart.data.datasets[0].data = values;
    window.iotChart.update();
    return;
  }
  if (typeof Chart === 'undefined') {
    try {
      const canvas = ctx;
      const c = canvas.getContext('2d');
      canvas.width = canvas.clientWidth || 700;
      canvas.height = 160;
      c.clearRect(0, 0, canvas.width, canvas.height);
      c.fillStyle = '#0f172a';
      c.fillRect(0, 0, canvas.width, canvas.height);
      c.fillStyle = '#d9faff';
      c.font = '16px Segoe UI';
      c.fillText('Graphique indisponible — Chart.js non chargé', 12, 28);
    } catch (e) {
      console.error(e);
    }
    return;
  }

  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, 'rgba(34, 211, 238, 0.34)');
  gradient.addColorStop(1, 'rgba(124, 58, 237, 0.05)');

  window.iotChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Valeurs capteur',
        data: values,
        backgroundColor: gradient,
        borderColor: '#22d3ee',
        pointBackgroundColor: '#ffffff',
        pointBorderColor: '#7c3aed',
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.35,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
        y: { beginAtZero: false, grid: { color: 'rgba(255,255,255,0.08)' }, ticks: { color: '#94a3b8' } }
      }
    }
  });
}

async function syncOfflineData() {
    try {
        const response = await fetch('/api/offline/sync/me', {
            method: 'POST',
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

window.addEventListener('DOMContentLoaded', () => {
  const refreshButton = document.getElementById('refresh-dashboard');
  refreshButton?.addEventListener('click', loadIoTDashboard);
  loadIoTDashboard();
});
