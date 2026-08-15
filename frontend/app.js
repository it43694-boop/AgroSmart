const apiBase = (window.location.origin || '') + '/api';
let accessToken = localStorage.getItem('accessToken') || null;
const OFFLINE_QUEUE_KEY = 'agrosmartOfflineQueue';
const TOKEN_KEY = 'accessToken';
const API_TIMEOUT = 30000; // 30 secondes

async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  if (['127.0.0.1', 'localhost'].includes(window.location.hostname)) {
    try {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map(reg => reg.unregister()));
      console.log('Service worker désenregistré en local pour éviter le cache obsolète.');
    } catch (error) {
      console.warn('Impossible de désenregistrer le service worker en local:', error);
    }
    return;
  }

  try {
    const registration = await navigator.serviceWorker.register('/frontend/service-worker.js');
    console.log('Service worker AgroSmart enregistré à', registration.scope);
  } catch (error) {
    console.warn('Enregistrement du service worker échoué:', error);
  }
}

function getOfflineQueue() {
  try {
    return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveOfflineQueue(queue) {
  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
}

async function queueOfflineRequest(url, data, auth = false) {
  const queue = getOfflineQueue();
  queue.push({ url, data, auth, timestamp: new Date().toISOString() });
  saveOfflineQueue(queue);
  return {
    queued: true,
    offline: true,
    message: 'Requête mise en file d\'attente et envoyée à la reconnexion.'
  };
}

async function flushOfflineQueue() {
  const queue = getOfflineQueue();
  if (!queue.length || !navigator.onLine) {
    return;
  }
  const remaining = [];
  for (const entry of queue) {
    try {
      await postJson(entry.url, entry.data, entry.auth);
    } catch {
      remaining.push(entry);
    }
  }
  saveOfflineQueue(remaining);
}

window.addEventListener('online', () => {
  console.log('Connexion rétablie, synchronisation des requêtes hors ligne.');
  flushOfflineQueue();
  updateNetworkBanner();
  updateQueueIndicator();
});

window.addEventListener('offline', () => {
  console.log('Mode hors ligne activé.');
  updateNetworkBanner();
  updateQueueIndicator();
});

window.addEventListener('load', () => {
  updateNetworkBanner();
  updateQueueIndicator();
  if (navigator.onLine) {
    flushOfflineQueue();
  }
  registerServiceWorker();
});

async function postJson(url, data, auth = false) {
  if (!navigator.onLine) {
    const queued = await queueOfflineRequest(url, data, auth);
    updateQueueIndicator();
    return queued;
  }
  const headers = { 'Content-Type': 'application/json' };
  const token = auth ? accessToken || localStorage.getItem(TOKEN_KEY) : null;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const response = await fetch(apiBase + url, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      accessToken = null;
      window.location.href = '/login';
      throw new Error('Session expirée');
    }

    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Délai de requête dépassé');
    }
    throw error;
  }
}

async function fetchJson(url, auth = false) {
  const headers = {};
  const token = auth ? accessToken || localStorage.getItem(TOKEN_KEY) : null;
  if (auth && token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!navigator.onLine) {
    try {
      const cachedResponse = await caches.match(url);
      if (cachedResponse) {
        const cachedJson = await cachedResponse.json();
        return cachedJson;
      }
      throw new Error('Hors ligne et données non disponibles dans le cache.');
    } catch (error) {
      console.error('Cache Error:', error);
      throw error;
    }
  }

  try {
    const response = await fetch(url, { headers });
    let result = null;
    try {
      result = await response.json();
    } catch (err) {
      const txt = await response.text();
      if (!response.ok) {
        throw new Error(txt || `Erreur ${response.status}: ${response.statusText}`);
      }
      return txt;
    }
    if (!response.ok) {
      throw new Error(result.detail || `Erreur ${response.status}: ${response.statusText}`);
    }
    return result;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

function showResult(elementId, data, isError = false) {
  const element = document.getElementById(elementId);
  if (!element) return;

  if (isError) {
    element.innerHTML = `<div style="color: red; padding: 10px; border: 1px solid red; border-radius: 4px; background: #ffe6e6;">
      <strong>Erreur:</strong><br>${data.message || data.detail || JSON.stringify(data, null, 2)}
    </div>`;
  } else {
    element.innerHTML = `<div style="color: green; padding: 10px; border: 1px solid green; border-radius: 4px; background: #e6ffe6;">
      <strong>Succès:</strong><br><pre>${JSON.stringify(data, null, 2)}</pre>
    </div>`;
  }
}

function getLowBandwidthMode() {
  try {
    const saved = localStorage.getItem('agrosmartLowBandwidthMode');
    if (saved !== null) {
      return saved === 'true';
    }

    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (!connection) {
      return false;
    }

    return connection.saveData === true || ['2g', 'slow-2g'].includes(connection.effectiveType);
  } catch {
    return false;
  }
}

function setLowBandwidthMode(enabled) {
  try {
    localStorage.setItem('agrosmartLowBandwidthMode', enabled ? 'true' : 'false');
    updateNetworkBanner();
  } catch {
    // ignore storage errors
  }
}

function updateNetworkBanner() {
  const banner = document.getElementById('network-status-banner');
  if (!banner) return;

  const online = navigator.onLine;
  const lowBandwidth = getLowBandwidthMode();
  banner.textContent = online
    ? `En ligne${lowBandwidth ? ' - mode basse bande passante activé' : ''}`
    : 'Hors ligne - utilisation en mode PWA activée';
  banner.className = online ? 'network-banner online' : 'network-banner offline';
}

function updateQueueIndicator() {
  const queueElement = document.getElementById('offline-queue-status');
  if (!queueElement) return;
  const queue = getOfflineQueue();
  queueElement.textContent = queue.length > 0 ? `Requêtes hors ligne en attente : ${queue.length}` : 'Aucune requête en attente.';
}

function formatCurrency(value) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value);
}

function renderDashboard(data) {
  const container = document.getElementById('dashboard-container');
  const error = document.getElementById('dashboard-error');
  if (!container || !error) return;

  error.classList.add('hidden');
  container.classList.remove('hidden');

  if (data.detail) {
    container.classList.add('hidden');
    error.textContent = data.detail || 'Erreur lors de la récupération du dashboard.';
    error.classList.remove('hidden');
    return;
  }

  const userCard = `
    <div class="card">
      <h3>Profil agriculteur</h3>
      <p><strong>Nom :</strong> ${data.user.full_name}</p>
      <p><strong>Email :</strong> ${data.user.email}</p>
      <p><strong>Région :</strong> ${data.user.region || 'Non définie'}</p>
      <p><strong>Surface totale :</strong> ${data.user.total_surface} ha</p>
      <p><strong>Validation :</strong> ${data.user.is_validated ? 'Validé' : 'En attente'}</p>
    </div>
  `;

  const financeCard = `
    <div class="card">
      <h3>Finance</h3>
      <p class="metric"><span>Revenu total</span><strong>${formatCurrency(data.total_revenue)}</strong></p>
      <p class="metric"><span>Coût total</span><strong>${formatCurrency(data.total_cost)}</strong></p>
      <p class="metric"><span>Revenu net</span><strong>${formatCurrency(data.net_income)}</strong></p>
      <p><strong>Historique :</strong> ${data.user.finance_records.length} enregistrements</p>
    </div>
  `;

  const weatherCard = `
    <div class="card accent-card">
      <h3>Météo</h3>
      <p><strong>Localisation :</strong> ${data.weather.location}</p>
      <p><strong>Température :</strong> ${data.weather.temperature_celsius} °C</p>
      <p><strong>Prévisions :</strong></p>
      <ul>${data.weather.forecast.map(item => `<li>${item}</li>`).join('')}</ul>
      ${data.weather.alert ? `<p class="alert">${data.weather.alert}</p>` : ''}
    </div>
  `;

  const advisorCard = `
    <div class="card">
      <h3>Conseil agricole</h3>
      <p class="recommendation">${data.advisor.recommendation}</p>
      <ul>${data.advisor.details.map(item => `<li>${item}</li>`).join('')}</ul>
    </div>
  `;

  const creditCard = `
    <div class="card accent-card">
      <h3>Score de crédit</h3>
      <p class="large-value">${data.credit_score.score}</p>
      <p><strong>Evaluation :</strong> ${data.credit_score.rating}</p>
      <ul>${data.credit_score.details.map(item => `<li>${item}</li>`).join('')}</ul>
    </div>
  `;

  const marketCard = `
    <div class="card">
      <h3>Marché</h3>
      <p><strong>Tendance :</strong> ${data.market_info.market_trend}</p>
      <p><strong>Source :</strong> ${data.market_info.source}</p>
      <ul>${Object.entries(data.market_info.crop_prices)
        .map(([crop, price]) => `<li>${crop} : ${formatCurrency(price)}</li>`)
        .join('')}</ul>
    </div>
  `;

  const satelliteCard = `
    <div class="card">
      <h3>Satellite</h3>
      <p>${data.satellite_info.summary}</p>
      <p><strong>Indice végétation :</strong> ${data.satellite_info.vegetation_index}</p>
      <p>${data.satellite_info.advisor_note}</p>
      ${data.satellite_info.image_url ? `
        <picture>
          <source type="image/webp" srcset="${data.satellite_info.image_url.replace(/\.(jpe?g|png|bmp|tiff?)([?#].*)?$/i, '.webp$2')}">
          <img src="${data.satellite_info.image_url}" alt="Satellite" class="satellite-image" />
        </picture>
      ` : ''}
    </div>
  `;

  container.innerHTML = `
    ${userCard}
    ${financeCard}
    ${weatherCard}
    ${advisorCard}
    ${creditCard}
    ${marketCard}
    ${satelliteCard}
  `;
}

// ==========================================
// ÉCOUTEURS D'ÉVÉNEMENTS AVEC VÉRIFICATIONS DE SÉCURITÉ
// ==========================================

// Vérifier que les éléments existent avant d'ajouter les event listeners
if (document.getElementById('login-form')) {
  document.getElementById('login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('username', document.getElementById('login-email').value);
      formData.append('password', document.getElementById('login-password').value);
      const response = await fetch(`${apiBase}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      const data = await response.json();
      if (data.access_token) {
        accessToken = data.access_token;
        localStorage.setItem('accessToken', data.access_token);
        showResult('login-result', { message: 'Connexion réussie ! Token obtenu.', token: data.access_token.substring(0, 20) + '...' });
      } else {
        showResult('login-result', data, true);
      }
    } catch (error) {
      showResult('login-result', { message: error.message }, true);
    }
  });
}

if (document.getElementById('create-user-form')) {
  document.getElementById('create-user-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const fullName = document.getElementById('user-name').value.trim();
      const user = {
        full_name: fullName || 'Test User',
        email: document.getElementById('user-email').value,
        password: document.getElementById('user-password').value,
        phone: '+22501020304', // Numéro par défaut pour les tests
        region: document.getElementById('user-region').value || 'Test Region',
        total_surface: 1.0, // Surface minimale requise
        account_type: 'farmer',
      };
      const data = await postJson(`${apiBase}/users/`, user);
      showResult('user-result', data);
    } catch (error) {
      showResult('user-result', { message: error.message }, true);
    }
  });
}

if (document.getElementById('create-crop-form')) {
  document.getElementById('create-crop-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const userId = document.getElementById('crop-user-id').value;
      const crop = {
        name: document.getElementById('crop-name').value,
        surface: parseFloat(document.getElementById('crop-surface').value),
      };
      const data = await postJson(`${apiBase}/users/${userId}/crops/`, crop, true);
      showResult('crop-result', data);
    } catch (error) {
      showResult('crop-result', { message: error.message }, true);
    }
  });
}

if (document.getElementById('create-finance-form')) {
  document.getElementById('create-finance-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const userId = document.getElementById('finance-user-id').value;
      const record = {
        revenue: parseFloat(document.getElementById('finance-revenue').value),
        cost: parseFloat(document.getElementById('finance-cost').value),
      };
      const data = await postJson(`${apiBase}/users/${userId}/finance/`, record, true);
      showResult('finance-result', data);
    } catch (error) {
      showResult('finance-result', { message: error.message }, true);
    }
  });
}

if (document.getElementById('dashboard-form')) {
  document.getElementById('dashboard-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const userId = document.getElementById('dashboard-user-id').value;
      // default demo coordinates (Koulikoro demo)
      let lat = 12.6392, lon = -8.0029;

      // try to read first field coordinates (preferred)
      try {
        const token = localStorage.getItem('accessToken');
        if (token) {
          const fresp = await fetch(`${apiBase}/virtualfarm/field`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (fresp.ok) {
            const field = await fresp.json();
            if (field && typeof field.latitude === 'number' && typeof field.longitude === 'number') {
              lat = field.latitude;
              lon = field.longitude;
            }
          } else {
            // fallback: try /me for possible coordinates
            const mresp = await fetch(`${apiBase}/me`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (mresp.ok) {
              const me = await mresp.json().catch(()=>null);
              if (me && typeof me.latitude === 'number' && typeof me.longitude === 'number') {
                lat = me.latitude; lon = me.longitude;
              }
            }
          }
        }
      } catch (e) {
        console.warn('Impossible de récupérer la localisation utilisateur:', e);
      }

      const data = await fetchJson(`${apiBase}/dashboard/${userId}?lat=${lat}&lon=${lon}`, true);
      renderDashboard(data);
    } catch (error) {
      const errorDiv = document.getElementById('dashboard-error');
      if (errorDiv) {
        errorDiv.textContent = `Erreur: ${error.message}`;
        errorDiv.classList.remove('hidden');
      }
      const container = document.getElementById('dashboard-container');
      if (container) {
        container.classList.add('hidden');
      }
    }
  });
}