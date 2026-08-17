// farmer-dashboard.js - Logique pour le nouveau dashboard agriculteur

/**
 * Conversion sûre des valeurs numériques
 * @param {string|number} value - Valeur à convertir
 * @param {boolean} forceInteger - Force la conversion en entier
 * @returns {number} Valeur convertie
 */
function safeNumber(value, forceInteger = false) {
    if (!value && value !== 0) return forceInteger ? 0 : 0.0;
    // Accept objects with .price
    if (typeof value === 'object' && value !== null && ('price' in value)) {
        return safeNumber(value.price, forceInteger);
    }
    // Normalize string numbers: trim, replace comma with dot, remove non-digit except dot/minus
    if (typeof value === 'string') {
        let s = value.trim();
        s = s.replace(/\s+/g, '');
        s = s.replace(/,/g, '.');
        // remove anything that's not digit, dot or minus
        s = s.replace(/[^0-9.\-]/g, '');
        const num = parseFloat(s);
        if (isNaN(num)) return forceInteger ? 0 : 0.0;
        return forceInteger ? Math.round(num) : num;
    }
    const num = Number(value);
    if (isNaN(num)) return forceInteger ? 0 : 0.0;
    return forceInteger ? Math.round(num) : num;
}

function showMarketUnavailableMessage(message) {
    const priceSeriesInfo = document.getElementById('priceSeriesInfo');
    if (priceSeriesInfo) {
        priceSeriesInfo.textContent = '';
    }
    const statusMsg = document.getElementById('marketStatusMessage');
    if (statusMsg) {
        statusMsg.textContent = message;
        statusMsg.style.display = 'block';
    }
    const priceCtx = document.getElementById('priceChart');
    if (priceCtx && priceCtx._chartInstance) {
        try { priceCtx._chartInstance.destroy(); } catch (e) {}
    }
    const toggleBtn = document.getElementById('toggleMarketRawBtn');
    if (toggleBtn) {
        toggleBtn.style.display = 'none';
    }
    const rawElem = document.getElementById('marketRawData');
    if (rawElem) {
        rawElem.style.display = 'none';
    }
    const priceGrid = document.getElementById('priceGrid');
    if (priceGrid) {
        priceGrid.innerHTML = '<div id="priceGridEmpty" class="price-card" style="background: rgba(255,255,255,0.05); color:#cbd5e1; border:1px dashed rgba(148,163,184,0.35);">Aucun prix disponible actuellement.</div>';
    }
}

function renderMarketPriceCards(prices) {
    const priceGrid = document.getElementById('priceGrid');
    if (!priceGrid) return;
    priceGrid.innerHTML = '';

    const cropEntries = Object.entries(prices || {});
    if (cropEntries.length === 0) {
        priceGrid.innerHTML = '<div id="priceGridEmpty" class="price-card" style="background: rgba(255,255,255,0.05); color:#cbd5e1; border:1px dashed rgba(148,163,184,0.35);">Aucune donnée de prix disponible.</div>';
        return;
    }

    const sortedEntries = cropEntries.sort((a,b) => {
        const aPrice = safeNumber(a[1]);
        const bPrice = safeNumber(b[1]);
        return bPrice - aPrice;
    });

    sortedEntries.forEach(([crop, rawValue]) => {
        const price = typeof rawValue === 'object' && rawValue !== null && 'price' in rawValue ? safeNumber(rawValue.price) : safeNumber(rawValue);
        const unit = typeof rawValue === 'object' && rawValue !== null && rawValue.unit ? rawValue.unit : 'FCFA/kg';
        const cropName = crop.charAt(0).toUpperCase() + crop.slice(1);
        const card = document.createElement('div');
        card.className = 'price-card';
        card.innerHTML = `
            <div class="price-name">${cropName}</div>
            <div class="price-current">${price.toLocaleString('fr-FR')} ${unit}</div>
            <div class="price-change" style="opacity: .75; font-size: .92rem;">Données actuelles</div>
        `;
        priceGrid.appendChild(card);
    });
}

// Variables globales
let currentUser = null;
let chartInstances = [];
let currentFieldId = null;

// Initialisation
function redirectToLogin() {
    localStorage.removeItem('accessToken');
    window.location.replace('/login');
}

async function initDashboard() {
    const authenticated = await checkAuth();
    if (!authenticated) {
        return;
    }
    setupEventListeners();
    updateDate();
    initCharts();
    const hasSeenOnboarding = localStorage.getItem('agrosmart-onboarding-seen');
    const onboardingBanner = document.getElementById('onboarding-banner');
    const onboardingModal = document.getElementById('onboarding-modal');
    if (!hasSeenOnboarding && onboardingBanner && onboardingModal) {
        onboardingBanner.style.display = 'flex';
        onboardingModal.classList.add('open');
    } else if (onboardingBanner) {
        onboardingBanner.style.display = 'none';
    }
    await loadAgroBrainRecommendation();
    await loadUserCropSummary();
    await loadFieldSummary();
    await loadFieldList();
    await loadCrops();
    await loadMarketPrices();
    refreshWeather();
    await loadSellerBalance();
    await loadLoans();
    showSection('dashboard');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

async function loadMarketPrices(days = 30) {
    try {
        const token = localStorage.getItem('accessToken');
        // default demo coordinates (Koulikoro demo)
        let lat = 12.6392, lon = -8.0029;

        // try to read first field coordinates (preferred)
        try {
            if (token) {
                const fieldsResp = await fetch('https://agrosmart-vi8d.onrender.com/api/virtualfarm/fields', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (fieldsResp.ok) {
                    const fields = await fieldsResp.json();
                    if (Array.isArray(fields) && fields.length > 0) {
                        const firstField = fields[0];
                        if (firstField && typeof firstField.latitude === 'number' && typeof firstField.longitude === 'number') {
                            lat = firstField.latitude;
                            lon = firstField.longitude;
                        }
                    }
                } else {
                    // fallback: try /me for possible coordinates
                    const mresp = await fetch('https://agrosmart-vi8d.onrender.com/api/me', { headers: { 'Authorization': `Bearer ${token}` } });
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

        const resp = await fetch(`https://agrosmart-vi8d.onrender.com/api/markets/?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);

        if (!resp.ok) {
            console.warn("Impossible de récupérer les prix marché:", resp.status);
            showMarketUnavailableMessage('Le service de prix de marché est temporairement indisponible. Réessayez dans quelques instants ou vérifiez votre connexion.');
            return;
        }
        const data = await resp.json();
        console.debug('markets data:', data);

        const statusMsg = document.getElementById('marketStatusMessage');
        const rawElem = document.getElementById('marketRawData');
        const marketToggleBtn = document.getElementById('toggleMarketRawBtn');
        if (statusMsg) {
            statusMsg.style.display = 'none';
        }
        if (marketToggleBtn) {
            marketToggleBtn.style.display = 'none';
        }
        if (rawElem) {
            rawElem.style.display = 'none';
        }

        const prices = data.crop_prices || {};
        const cropNames = Object.keys(prices || {});
        if (cropNames.length === 0) {
            showMarketUnavailableMessage('Aucune donnée de prix du marché n’est actuellement disponible.');
            return;
        }

        // filter crops with valid numeric base price; collect excluded with reasons
        const validCropNames = [];
        const excluded = [];
        cropNames.forEach(crop => {
            const raw = prices[crop];
            let base = null;
            try {
                if (raw !== undefined && raw !== null) {
                    if (typeof raw === 'object' && ('price' in raw)) {
                        base = safeNumber(raw.price);
                    } else {
                        base = safeNumber(raw);
                    }
                }
            } catch (e) {
                base = NaN;
            }
            if (!isFinite(base) || base <= 0) {
                let reason = 'Prix invalide';
                if (raw === null || raw === undefined) reason = 'Aucun prix';
                else if (typeof raw === 'object' && !('price' in raw)) reason = 'Objet sans champ price';
                else if (typeof raw === 'string') reason = `Format chaîne invalide (${String(raw).slice(0,20)})`;
                excluded.push({ name: crop, reason });
            } else {
                validCropNames.push(crop);
            }
        });

        if (validCropNames.length === 0) {
            showMarketUnavailableMessage('Le service de prix de marché est actuellement indisponible ou ne renvoie pas de données exploitables.');
            return;
        }

        const labels = validCropNames.map(crop => crop.charAt(0).toUpperCase() + crop.slice(1));
        const dataValues = validCropNames.map(crop => {
            const raw = prices[crop];
            if (typeof raw === 'object' && raw !== null && 'price' in raw) return safeNumber(raw.price);
            return safeNumber(raw);
        });

        function colorForIndex(i) {
            const palette = ['#27ae60','#3498db','#e74c3c','#f39c12','#9b59b6','#16a085','#2c3e50','#1abc9c','#e67e22','#8e44ad','#2ecc71','#2980b9'];
            return palette[i % palette.length];
        }

        const datasets = [{
            label: 'Prix actuel (FCFA/kg)',
            data: dataValues,
            backgroundColor: labels.map((_, idx) => colorForIndex(idx) + 'CC'),
            borderColor: labels.map((_, idx) => colorForIndex(idx)),
            borderWidth: 1
        }];

        const seriesInfoElem = document.getElementById('priceSeriesInfo');
        if (seriesInfoElem) {
            const shown = labels.join(', ');
            const sourceLabel = data.source ? ` [${data.source}]` : '';
            const exclText = excluded.length ? excluded.map(e=>`${e.name} (${e.reason})`).join(', ') : '';
            seriesInfoElem.textContent = `Prix actuels reçus du backend: ${shown}` + (exclText? ` (exclu: ${exclText})` : '') + sourceLabel;
        }
        renderMarketPriceCards(prices);

        if (marketToggleBtn) {
            marketToggleBtn.style.display = 'inline-flex';
        }

        const priceCtx = document.getElementById('priceChart');
        if (!priceCtx) return;

        const existingPriceChart = (typeof Chart.getChart === 'function' ? Chart.getChart(priceCtx) : null) || priceCtx._chartInstance;
        if (existingPriceChart) {
            try { existingPriceChart.destroy(); } catch(e) {}
        }
        priceCtx._chartInstance = new Chart(priceCtx, {
            type: 'bar',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    } catch (error) {
        console.error('Erreur chargement prix marché:', error);
        showMarketUnavailableMessage('Le service de prix de marché est indisponible. Vérifiez le backend ou réessayez plus tard.');
    }
}

function drawSimpleLineChart(canvasElem, labels, datasets) {
    // canvasElem can be a canvas or its id
    const canvas = (typeof canvasElem === 'string') ? document.getElementById(canvasElem) : canvasElem;
    if (!canvas) return;
    // force visible size
    canvas.style.width = canvas.style.width || '700px';
    canvas.style.height = canvas.style.height || '320px';
    const W = 700, H = 320;
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width,canvas.height);

    // compute min/max
    let min = Infinity, max = -Infinity;
    datasets.forEach(ds => ds.data.forEach(v => { if (v < min) min = v; if (v > max) max = v; }));
    if (!isFinite(min) || !isFinite(max)) return;
    const pad = (max - min) * 0.12 || 10;
    min = min - pad; max = max + pad;

    const margin = {left:50, right:30, top:30, bottom:50};
    const w = canvas.width - margin.left - margin.right;
    const h = canvas.height - margin.top - margin.bottom;

    // background
    ctx.fillStyle = '#fff'; ctx.fillRect(0,0,canvas.width,canvas.height);

    // draw axes
    ctx.strokeStyle = '#999'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(margin.left, margin.top); ctx.lineTo(margin.left, margin.top + h); ctx.lineTo(margin.left + w, margin.top + h); ctx.stroke();

    // draw grid and y labels
    const rows = 4;
    ctx.fillStyle = '#333'; ctx.font = '13px sans-serif'; ctx.textAlign = 'right';
    for (let i=0;i<=rows;i++){
        const y = margin.top + (h * i / rows);
        const val = (max - (max - min) * i / rows).toFixed(0);
        ctx.strokeStyle = '#eee'; ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(margin.left + w, y); ctx.stroke();
        ctx.fillText(val, margin.left - 8, y + 5);
    }

    // draw each dataset
    const points = labels.length;
    datasets.forEach((ds, idx) => {
        const color = ds.borderColor || ['#27ae60','#3498db','#e74c3c','#f39c12','#9b59b6'][idx % 5];
        ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.beginPath();
        ds.data.forEach((v, i) => {
            const x = margin.left + (i / Math.max(1, points-1)) * w;
            const y = margin.top + ((max - v) / (max - min)) * h;
            if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        });
        ctx.stroke();
    });

    // legend
    ctx.font = '12px sans-serif'; ctx.textAlign = 'left';
    datasets.forEach((ds, idx) => {
        const x = margin.left + idx * 140;
        const y = canvas.height - 14;
        ctx.fillStyle = ds.borderColor || '#000';
        ctx.fillRect(x, y-8, 14, 8);
        ctx.fillStyle = '#333'; ctx.fillText(ds.label, x+18, y);
    });
}

function getDefaultSoilType(region) {
    if (!region) return 'loameux';
    const normalized = region.toLowerCase();
    if (normalized.includes('sikasso') || normalized.includes('kayes') || normalized.includes('tombouctou')) {
        return 'sableux';
    }
    if (normalized.includes('gao') || normalized.includes('mopti')) {
        return 'argileux';
    }
    return 'loameux';
}

function getDefaultSeason(region) {
    if (!region) return 'hivernage';
    const normalized = region.toLowerCase();
    if (normalized.includes('tombouctou') || normalized.includes('gao')) {
        return 'sèche';
    }
    return 'hivernage';
}

async function loadUserCropSummary() {
    if (!currentUser) return;
    try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            console.error('Token not found in localStorage');
            const cropField = document.getElementById('profile-crops');
            if (cropField) cropField.textContent = 'Erreur: Veuillez vous reconnecter';
            return;
        }

        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}/crops/`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) {
            document.getElementById('profile-crops').textContent = 'Aucune culture disponible';
            return;
        }
        const crops = await response.json();
        const cropField = document.getElementById('profile-crops');
        if (!cropField) return;
        if (!crops || crops.length === 0) {
            cropField.textContent = 'Pas de cultures enregistrées';
            return;
        }
        cropField.textContent = crops.map(c => c.name).join(', ');
    } catch (error) {
        console.error('Erreur chargement résumé cultures:', error);
        const cropField = document.getElementById('profile-crops');
        if (cropField) {
            cropField.textContent = 'Impossible de charger les cultures';
        }
    }
}

async function loadFieldSummary() {
    const token = localStorage.getItem('accessToken');
    if (!token) return;
    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/virtualfarm/fields', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            renderFieldSummary(null);
            renderFieldList([]);
            return;
        }

        const fields = await response.json();
        renderFieldList(fields);
        renderFieldSummary(Array.isArray(fields) && fields.length > 0 ? fields[0] : null);
    } catch (error) {
        console.error('Erreur chargement du champ:', error);
        renderFieldSummary(null);
        renderFieldList([]);
    }
}

function renderFieldSummary(field) {
    const nameEl = document.getElementById('field-summary-name');
    const coordsEl = document.getElementById('field-summary-coords');
    const areaEl = document.getElementById('field-summary-area');
    const cropEl = document.getElementById('field-summary-crop');
    const soilEl = document.getElementById('field-summary-soil');
    const irrigationEl = document.getElementById('field-summary-irrigation');
    const notesEl = document.getElementById('field-summary-notes');

    if (!field || field.id == null) {
        if (nameEl) nameEl.textContent = 'Aucune parcelle enregistrée';
        if (coordsEl) coordsEl.textContent = '-';
        if (areaEl) areaEl.textContent = '-';
        if (cropEl) cropEl.textContent = '-';
        if (soilEl) soilEl.textContent = '-';
        if (irrigationEl) irrigationEl.textContent = '-';
        if (notesEl) notesEl.textContent = 'Créez un champ pour en voir les détails ici.';
        return;
    }

    if (nameEl) nameEl.textContent = field.name || 'Sans nom';
    if (coordsEl) coordsEl.textContent = `${field.latitude?.toFixed(4) || '-'}, ${field.longitude?.toFixed(4) || '-'}`;
    if (areaEl) areaEl.textContent = field.area_ha != null ? `${field.area_ha} ha` : '-';
    if (cropEl) cropEl.textContent = field.crop_rotation || 'Non renseigné';
    if (soilEl) soilEl.textContent = field.soil_type || 'Non renseigné';
    if (irrigationEl) irrigationEl.textContent = field.irrigation_system || 'Non renseigné';
    if (notesEl) notesEl.textContent = field.notes ? `Notes : ${field.notes}` : 'Aucune note fournie.';
}

function renderFieldList(fields) {
    const listContainer = document.getElementById('field-list');
    if (!listContainer) return;

    if (!Array.isArray(fields) || fields.length === 0) {
        listContainer.innerHTML = `
            <div class="field-list-empty" style="padding: 18px; background: rgba(255,255,255,0.05); border:1px dashed rgba(148,163,184,0.35); border-radius: 16px; color:#cbd5e1;">
                Aucune parcelle enregistrée. Cliquez sur "Ajouter un champ" pour commencer.
            </div>
        `;
        return;
    }

    listContainer.innerHTML = '';
    fields.forEach(field => {
        const card = document.createElement('div');
        card.className = 'field-list-card';
        card.style = 'padding: 18px; margin-bottom: 12px; background: rgba(15,23,42,0.9); border-radius: 18px; border: 1px solid rgba(148,163,184,0.18);';
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap: 12px;">
                <div>
                    <div style="font-size: 1rem; font-weight: 600;">${field.name || 'Sans nom'}</div>
                    <div style="font-size: .92rem; color: #94a3b8;">${field.latitude?.toFixed(4) || '-'}, ${field.longitude?.toFixed(4) || '-'}</div>
                </div>
                <div style="display:flex; gap: 10px; flex-wrap:wrap;">
                    <button class="btn btn-secondary" type="button" onclick="editField(${field.id})">Modifier</button>
                    <button class="btn btn-danger" type="button" onclick="deleteField(${field.id})">Supprimer</button>
                </div>
            </div>
            <div style="margin-top: 12px; display:grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;">
                <div><strong>Surface:</strong> ${field.area_ha != null ? `${field.area_ha} ha` : '-'}</div>
                <div><strong>Rotation:</strong> ${field.crop_rotation || '-'}</div>
                <div><strong>Sol:</strong> ${field.soil_type || '-'}</div>
                <div><strong>Irrigation:</strong> ${field.irrigation_system || '-'}</div>
            </div>
        `;
        listContainer.appendChild(card);
    });
}

function resetFieldForm() {
    const form = document.getElementById('field-form');
    if (form) form.reset();
    currentFieldId = null;
    const title = document.getElementById('field-modal-title');
    if (title) {
        title.textContent = 'Ajouter un Champ';
    }
    const methodSelect = document.getElementById('field-input-method');
    if (methodSelect) {
        methodSelect.value = 'manual';
    }
    toggleFieldInputMethod();
    clearMapPoints();
}

function openFieldModal() {
    resetFieldForm();
    showModal('fieldModal');
}

async function editField(fieldId) {
    const token = localStorage.getItem('accessToken');
    if (!token) {
        showAlert('❌ Veuillez vous reconnecter');
        return;
    }

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/virtualfarm/field?field_id=${fieldId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Impossible de charger la parcelle' }));
            throw new Error(error.detail || 'Impossible de charger la parcelle');
        }

        const field = await response.json();
        currentFieldId = fieldId;
        const title = document.getElementById('field-modal-title');
        if (title) {
            title.textContent = 'Modifier le Champ';
        }

        document.getElementById('field-name').value = field.name || '';
        document.getElementById('field-crop-rotation').value = field.crop_rotation || '';
        document.getElementById('field-soil-type').value = field.soil_type || 'Sable limoneux';
        document.getElementById('field-irrigation').value = field.irrigation_system || 'Aucun';
        document.getElementById('field-notes').value = field.notes || '';

        if (Array.isArray(field.boundary_points) && field.boundary_points.length >= 3) {
            document.getElementById('field-input-method').value = 'map';
            toggleFieldInputMethod();
            clearMapPoints();
            field.boundary_points.forEach(point => addMapPoint(point.lat, point.lon));
        } else {
            document.getElementById('field-input-method').value = 'manual';
            toggleFieldInputMethod();
            document.getElementById('field-latitude').value = field.latitude ?? '';
            document.getElementById('field-longitude').value = field.longitude ?? '';
            document.getElementById('field-area').value = field.area_ha ?? '';
        }

        showModal('fieldModal');
    } catch (error) {
        console.error('Erreur chargement modification champ:', error);
        showAlert(`❌ Erreur: ${error.message}`);
    }
}

async function deleteField(fieldId) {
    if (!confirm('Confirmez-vous la suppression de cette parcelle ?')) {
        return;
    }

    const token = localStorage.getItem('accessToken');
    if (!token) {
        showAlert('❌ Veuillez vous reconnecter');
        return;
    }

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/virtualfarm/field/${fieldId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Impossible de supprimer la parcelle' }));
            throw new Error(error.detail || 'Impossible de supprimer la parcelle');
        }

        showAlert('✅ Parcelle supprimée avec succès');
        await loadFieldSummary();
        await loadFieldList();
        refreshWeather();
    } catch (error) {
        console.error('Erreur suppression champ:', error);
        showAlert(`❌ Erreur: ${error.message}`);
    }
}

async function loadAgroBrainRecommendation() {
    const fallbackCrop = 'Analyse en cours';
    const fallbackConfidence = 'Analyse active';
    const fallbackYield = 'Météo + marché';
    const fallbackWater = 'À vérifier';
    const fallbackTips = 'Le conseiller AgroSmart rassemble les données météo et marché pour vous guider.';

    const cropField = document.getElementById('agro-brain-crop');
    const confidenceField = document.getElementById('agro-brain-confidence');
    const yieldField = document.getElementById('agro-brain-yield');
    const waterField = document.getElementById('agro-brain-water');
    const tipsField = document.getElementById('agro-brain-tips');

    if (cropField) cropField.textContent = fallbackCrop;
    if (confidenceField) confidenceField.textContent = fallbackConfidence;
    if (yieldField) yieldField.textContent = fallbackYield;
    if (waterField) waterField.textContent = fallbackWater;
    if (tipsField) tipsField.textContent = fallbackTips;

    try {
        const token = localStorage.getItem('accessToken');
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        let lat = 12.6392;
        let lon = -8.0029;
        try {
            const fieldResp = await fetch('https://agrosmart-vi8d.onrender.com/api/virtualfarm/field', { headers });
            if (fieldResp.ok) {
                const field = await fieldResp.json();
                if (field && typeof field.latitude === 'number' && typeof field.longitude === 'number') {
                    lat = field.latitude;
                    lon = field.longitude;
                }
            }
        } catch (fieldError) {
            console.warn('Impossible de récupérer la localisation pour l’assistant:', fieldError);
        }

        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/assistant/summary?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`, { headers });
        if (!response.ok) {
            throw new Error(`Échec assistant AgroSmart: ${response.status}`);
        }

        const data = await response.json();
        const recommendation = data.recommendation || fallbackTips;
        const details = Array.isArray(data.details) ? data.details : [];
        const weather = data.weather || {};
        const marketTrend = data.market_trend || 'Stable';
        const temperature = weather.temperature_celsius != null ? `${Number(weather.temperature_celsius).toFixed(1)}°C` : 'N/A';
        const rainfall = weather.rainfall != null ? `${Number(weather.rainfall).toFixed(1)} mm` : 'N/A';
        const summaryTips = details.length > 0 ? details.slice(0, 3).join(' • ') : fallbackTips;

        if (cropField) {
            cropField.textContent = recommendation.length > 80 ? `${recommendation.slice(0, 77)}...` : recommendation;
        }
        if (confidenceField) {
            confidenceField.textContent = marketTrend || fallbackConfidence;
        }
        if (yieldField) {
            yieldField.textContent = temperature;
        }
        if (waterField) {
            waterField.textContent = rainfall;
        }
        if (tipsField) {
            tipsField.textContent = summaryTips;
        }
    } catch (error) {
        console.error('Erreur chargement assistant AgroSmart:', error);
    }
}

function updateProfileDisplay() {
    if (!currentUser) return;

    // Nom et statut
    const profileName = document.getElementById('profile-name');
    if (profileName) {
        profileName.textContent = `👤 ${currentUser.full_name || 'Agriculteur'}`;
    }

    const profileStatus = document.getElementById('profile-status');
    if (profileStatus) {
        profileStatus.textContent = currentUser.is_admin ? 'Administrateur' : 'Agriculteur, Membre';
    }

    // Région
    const profileRegion = document.getElementById('profile-region');
    if (profileRegion) {
        profileRegion.textContent = currentUser.region || 'Non spécifiée';
    }

    // Superficie
    const profileSurface = document.getElementById('profile-surface');
    if (profileSurface) {
        const surface = currentUser.total_surface || 0;
        profileSurface.textContent = `${surface} hectares`;
    }

    // Email
    const profileEmail = document.getElementById('profile-email');
    if (profileEmail) {
        profileEmail.textContent = currentUser.email || 'N/A';
    }

    // Téléphone
    const profilePhone = document.getElementById('profile-phone');
    if (profilePhone) {
        profilePhone.textContent = currentUser.phone || 'Non fourni';
    }

    // Solde vendeur et transactions
    loadSellerBalance();

    // Admin actions: auto-retrain button
    try {
        const adminArea = document.getElementById('admin-actions');
        if (currentUser.is_admin) {
            if (!adminArea) {
                const container = document.querySelector('.top-bar-user');
                if (container) {
                    const btn = document.createElement('button');
                    btn.id = 'autoRetrainBtn';
                    btn.textContent = 'Réentraîner ML (admin)';
                    btn.style.padding = '8px 12px';
                    btn.style.background = '#2ecc71';
                    btn.style.color = '#fff';
                    btn.style.border = 'none';
                    btn.style.borderRadius = '6px';
                    btn.style.cursor = 'pointer';
                    btn.addEventListener('click', triggerAutoRetrain);
                    container.appendChild(btn);
                }
            }
        } else {
            if (adminArea) adminArea.remove();
        }
    } catch (e) { console.warn('Admin button toggle failed', e); }

    // Score crédit (placeholder - à intégrer avec l'API)
    const profileCreditScore = document.getElementById('profile-credit-score');
    if (profileCreditScore) {
        profileCreditScore.textContent = '8.2/10'; // À récupérer depuis l'API
    }

    // Cultures (placeholder - à charger depuis l'API)
    const profileCrops = document.getElementById('profile-crops');
    if (profileCrops) {
        profileCrops.textContent = 'À charger...'; // À récupérer depuis l'API
    }

    populateProfileModal();
}

function populateProfileModal() {
    if (!currentUser) return;

    const fullNameField = document.getElementById('profile-full-name');
    const emailField = document.getElementById('profile-email-input');
    const phoneField = document.getElementById('profile-phone-input');
    const villageField = document.getElementById('profile-village-input');
    const regionField = document.getElementById('profile-region-input');
    const surfaceField = document.getElementById('profile-surface-input');

    if (fullNameField) fullNameField.value = currentUser.full_name || '';
    if (emailField) emailField.value = currentUser.email || '';
    if (phoneField) phoneField.value = currentUser.phone || '';
    if (villageField) villageField.value = currentUser.village || '';
    if (regionField) regionField.value = currentUser.region || '';
    if (surfaceField) surfaceField.value = currentUser.total_surface || 0;
}

async function checkAuth() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            console.warn('Farmer dashboard: accessToken absent, redirecting to login.');
            redirectToLogin();
            return false;
        }

        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            localStorage.removeItem('accessToken');
            redirectToLogin();
            return false;
        }

        currentUser = await response.json();

        // Vérifier que c'est un agriculteur ou admin
        const userRole = currentUser.role || currentUser.account_type || (currentUser.is_admin ? 'admin' : 'farmer');
        if (userRole !== 'farmer' && !currentUser.is_admin) {
            console.error('Access denied: not a farmer. Role:', userRole);
            localStorage.removeItem('accessToken');
            if (userRole === 'client') {
                window.location.replace('/client-dashboard');
            } else if (userRole === 'bank') {
                window.location.replace('/bank-dashboard');
            } else if (userRole === 'insurance') {
                window.location.replace('/insurance-dashboard');
            } else if (currentUser.is_admin || userRole === 'admin') {
                window.location.replace('/admin');
            } else {
                redirectToLogin();
            }
            return false;
        }

        // Mettre à jour tous les champs du profil avec les vraies données
        updateProfileDisplay();
        return true;
    } catch (error) {
        console.error('Erreur authentification:', error);
        localStorage.removeItem('accessToken');
        redirectToLogin();
        return false;
    }
}

function setupEventListeners() {
    const onboardingBanner = document.getElementById('onboarding-banner');
    const onboardingModal = document.getElementById('onboarding-modal');
    const showOnboardingBtn = document.getElementById('show-onboarding-btn');
    const closeOnboardingBtn = document.getElementById('close-onboarding-btn');

    if (showOnboardingBtn && onboardingModal) {
        showOnboardingBtn.addEventListener('click', () => {
            onboardingModal.classList.add('open');
        });
    }

    if (closeOnboardingBtn && onboardingModal) {
        closeOnboardingBtn.addEventListener('click', () => {
            onboardingModal.classList.remove('open');
            localStorage.setItem('agrosmart-onboarding-seen', '1');
            if (onboardingBanner) {
                onboardingBanner.style.display = 'none';
            }
        });
    }

    if (onboardingModal) {
        onboardingModal.addEventListener('click', (event) => {
            if (event.target === onboardingModal) {
                onboardingModal.classList.remove('open');
                localStorage.setItem('agrosmart-onboarding-seen', '1');
                if (onboardingBanner) {
                    onboardingBanner.style.display = 'none';
                }
            }
        });
    }

    // Navigation sidebar
    document.querySelectorAll('.menu-link').forEach(link => {
        const onclickValue = link.getAttribute('onclick');
        if (!onclickValue) {
            return;
        }

        link.addEventListener('click', function(e) {
            e.preventDefault();
            const match = onclickValue.match(/showSection\('(\w+)'\)/);
            if (match) {
                const sectionId = match[1];
                showSection(sectionId);
            }
        });
    });

    // Boutons d'action (si présents dans l'ancien système)
    const addCropBtn = document.getElementById('add-crop-btn');
    if (addCropBtn) {
        addCropBtn.addEventListener('click', () => showModal('cropModal'));
    }

    const createListingBtn = document.getElementById('create-listing-btn');
    if (createListingBtn) {
        createListingBtn.addEventListener('click', () => showModal('listingModal'));
    }

    // Anciens modals (pour compatibilité)
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => closeModals());
    });

    // Anciens formulaires (pour compatibilité)
    const cropForm = document.getElementById('crop-form');
    if (cropForm) {
        cropForm.addEventListener('submit', (e) => handleCropSubmit(e));
    }

    const listingForm = document.getElementById('listing-form');
    if (listingForm) {
        listingForm.addEventListener('submit', (e) => handleListingSubmit(e));
    }

    // Field form
    const fieldForm = document.getElementById('field-form');
    if (fieldForm) {
        fieldForm.addEventListener('submit', (e) => handleFieldSubmit(e));
    }

    const addFieldBtn = document.getElementById('add-field-btn');
    if (addFieldBtn) {
        addFieldBtn.addEventListener('click', () => openFieldModal());
    }
}

function showSection(sectionId) {
    // Masquer toutes les sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });

    // Désactiver tous les liens de navigation
    document.querySelectorAll('.menu-link').forEach(link => {
        link.classList.remove('active');
    });

    // Afficher la section demandée
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
    }

    // Activer le lien correspondant
    const targetLink = document.querySelector(`[onclick*="showSection('${sectionId}')"]`);
    if (targetLink) {
        targetLink.classList.add('active');
    }

    // Charger les données si nécessaire
    loadSectionData(sectionId);
}

function loadSectionData(sectionId) {
    switch(sectionId) {
        case 'crops':
            loadCrops();
            break;
        case 'market':
        case 'marketplace':
            loadSellerListings();
            break;
        case 'orders':
            loadOrders();
            break;
        case 'loans':
            loadLoans();
            break;
        case 'insurances':
            loadInsurances();
            break;
        case 'calendar':
            loadFarmerCalendar();
            break;
        case 'advice':
            loadAdvisorData();
            break;
        case 'financial':
            loadFinancialData();
            break;
        case 'alerts':
            loadAlertsData();
            break;
        case 'statistics':
            loadStatisticsData();
            break;
        case 'settings':
            loadSettingsData();
            break;
        case 'blockchain':
            loadBlockchainTraces();
            break;
    }
}

// Fonctions pour les modals
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
        modal.classList.remove('active');
    });
}

// Fonctions pour les actions
async function saveProfile() {
    if (!currentUser) return;

    const fullName = document.getElementById('profile-full-name')?.value.trim();
    const email = document.getElementById('profile-email-input')?.value.trim();
    const phone = document.getElementById('profile-phone-input')?.value.trim();
    const village = document.getElementById('profile-village-input')?.value.trim();
    const region = document.getElementById('profile-region-input')?.value.trim();
    const surfaceValue = document.getElementById('profile-surface-input')?.value;
    const total_surface = surfaceValue ? safeNumber(surfaceValue) : 0;

    const payload = {
        full_name: fullName,
        email,
        phone,
        village,
        region,
        total_surface,
    };

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({}));
            const message = errorBody.detail || 'Impossible de mettre à jour le profil.';
            alert(message);
            return;
        }

        currentUser = await response.json();
        updateProfileDisplay();
        populateProfileModal();
        showAlert('✅ Profil mis à jour avec succès!');
        closeModal('profileModal');
    } catch (error) {
        console.error('Erreur mise à jour profil:', error);
        alert('Erreur lors de la mise à jour du profil.');
    }
}

async function changePassword() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            showAlert('❌ Veuillez vous reconnecter');
            return;
        }
        
        const currentPassword = document.querySelector('#changePasswordModal input[type="password"]:nth-of-type(1)').value;
        const newPassword = document.querySelector('#changePasswordModal input[type="password"]:nth-of-type(2)').value;
        const confirmPassword = document.querySelector('#changePasswordModal input[type="password"]:nth-of-type(3)').value;
        
        if (!currentPassword || !newPassword || !confirmPassword) {
            showAlert('❌ Veuillez remplir tous les champs');
            return;
        }
        
        if (newPassword !== confirmPassword) {
            showAlert('❌ Les mots de passe ne correspondent pas');
            return;
        }
        
        if (newPassword.length < 8) {
            showAlert('❌ Le mot de passe doit contenir au moins 8 caractères');
            return;
        }
        
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        if (response.ok) {
            showAlert('✅ Mot de passe changé avec succès!');
            closeModal('changePasswordModal');
            document.querySelectorAll('#changePasswordModal input[type="password"]').forEach(input => input.value = '');
        } else {
            const error = await response.json();
            showAlert(`❌ Erreur: ${error.detail || 'Mot de passe actuel incorrect'}`);
        }
    } catch (error) {
        console.error('Erreur changement mot de passe:', error);
        showAlert('❌ Erreur lors du changement de mot de passe');
    }
}

async function requestCredit() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token || !currentUser) {
            showAlert('❌ Veuillez vous reconnecter');
            return;
        }
        
        const amount = document.getElementById('credit-amount').value;
        const duration = document.getElementById('credit-duration').value;
        const usage = document.getElementById('credit-usage').value;
        const description = document.getElementById('credit-description').value;
        
        if (!amount || !duration) {
            showAlert('❌ Veuillez remplir tous les champs obligatoires');
            return;
        }
        
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}/loans`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                amount: parseFloat(amount),
                duration_months: parseInt(duration),
                purpose: usage,
                description: description
            })
        });
        
        if (response.ok) {
            showAlert('✅ Demande de crédit soumise! Vous recevrez une réponse sous 48h');
            closeModal('creditModal');
            document.querySelectorAll('#creditModal input, #creditModal textarea').forEach(input => input.value = '');
            loadLoans();
        } else {
            const error = await response.json();
            showAlert(`❌ Erreur: ${error.detail || 'Erreur lors de la soumission'}`);
        }
    } catch (error) {
        console.error('Erreur demande crédit:', error);
        showAlert('❌ Erreur lors de la demande de crédit');
    }
}

async function subscribeInsurance() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token || !currentUser) {
            showAlert('❌ Veuillez vous reconnecter');
            return;
        }
        
        const coverageType = document.querySelector('#insuranceModal select').value;
        const coverageAmount = document.querySelector('#insuranceModal input[type="number"]:nth-of-type(1)').value;
        const duration = document.querySelector('#insuranceModal input[type="number"]:nth-of-type(2)').value;
        
        if (!coverageAmount || !duration) {
            showAlert('❌ Veuillez remplir tous les champs obligatoires');
            return;
        }
        
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}/insurances`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                coverage_type: coverageType,
                coverage_amount: parseFloat(coverageAmount),
                duration_months: parseInt(duration)
            })
        });
        
        if (response.ok) {
            showAlert('✅ Assurance souscrite avec succès!');
            closeModal('insuranceModal');
            document.querySelectorAll('#insuranceModal input').forEach(input => input.value = '');
            loadInsurances();
        } else {
            const error = await response.json();
            showAlert(`❌ Erreur: ${error.detail || 'Erreur lors de la souscription'}`);
        }
    } catch (error) {
        console.error('Erreur souscription assurance:', error);
        showAlert('❌ Erreur lors de la souscription assurance');
    }
}

function contactExpert() {
    showAlert('📞 Un expert vous contactera bientôt!');
}

async function handleFieldSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('accessToken');
    if (!token) {
        showAlert('❌ Veuillez vous reconnecter');
        return;
    }

    const inputMethod = document.getElementById('field-input-method').value;
    let latitude, longitude, area_ha, boundary_points;

    if (inputMethod === 'map') {
        // Use calculated values from map
        latitude = parseFloat(document.getElementById('field-latitude-calculated').value);
        longitude = parseFloat(document.getElementById('field-longitude-calculated').value);
        area_ha = parseFloat(document.getElementById('field-area-calculated').value);
        boundary_points = mapBoundaryPoints;
    } else {
        // Use manual values
        latitude = parseFloat(document.getElementById('field-latitude').value);
        longitude = parseFloat(document.getElementById('field-longitude').value);
        area_ha = parseFloat(document.getElementById('field-area').value);
        boundary_points = [];
    }

    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
        showAlert('❌ Veuillez entrer des coordonnées valides ou mesurer sur la carte');
        return;
    }

    const validArea = Number.isFinite(area_ha) ? area_ha : 0;
    const fieldData = {
        name: document.getElementById('field-name').value,
        latitude: latitude,
        longitude: longitude,
        area_ha: validArea,
        crop_rotation: document.getElementById('field-crop-rotation').value,
        soil_type: document.getElementById('field-soil-type').value,
        irrigation_system: document.getElementById('field-irrigation').value,
        notes: document.getElementById('field-notes').value,
        boundary_points: boundary_points
    };

    try {
        const url = currentFieldId ? `/api/virtualfarm/field/${currentFieldId}` : '/api/virtualfarm/field';
        const method = currentFieldId ? 'PATCH' : 'POST';

        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(fieldData)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Erreur serveur inconnue' }));
            throw new Error(error.detail || 'Erreur lors de l’enregistrement du champ');
        }

        const field = await response.json();
        if (!field || !field.id) {
            throw new Error('Réponse invalide du serveur après enregistrement du champ');
        }

        const action = currentFieldId ? 'mis à jour' : 'créé';
        showAlert(`✅ Champ ${action} avec succès ! ID ${field.id}`);
        closeModal('fieldModal');
        resetFieldForm();
        await loadFieldSummary();
        await loadFieldList();
        currentFieldId = null;
        refreshWeather();
    } catch (error) {
        console.error('Erreur création champ:', error);
        showAlert(`❌ Erreur: ${error.message}`);
    }
}

// Map-related variables
let fieldMap = null;
let mapMarkers = [];
let mapPolygon = null;
let mapBoundaryPoints = [];

function toggleFieldInputMethod() {
    const method = document.getElementById('field-input-method').value;
    const manualDiv = document.getElementById('manual-coords');
    const mapFieldsDiv = document.getElementById('map-coords-fields');
    const mapContainerDiv = document.getElementById('map-coords-container');
    
    if (method === 'map') {
        manualDiv.style.display = 'none';
        mapFieldsDiv.style.display = 'block';
        mapContainerDiv.style.display = 'block';
        // Initialize map if not already done
        setTimeout(initFieldMap, 100);
    } else {
        manualDiv.style.display = 'block';
        mapFieldsDiv.style.display = 'none';
        mapContainerDiv.style.display = 'none';
    }
}

function initFieldMap() {
    if (fieldMap) return; // Already initialized
    
    const mapContainer = document.getElementById('field-map');
    if (!mapContainer) return;
    
    // Initialize map centered on Mali
    fieldMap = L.map('field-map').setView([12.6392, -8.0029], 13);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(fieldMap);
    
    // Add click handler
    fieldMap.on('click', function(e) {
        addMapPoint(e.latlng.lat, e.latlng.lng);
    });
}

function addMapPoint(lat, lng) {
    if (!fieldMap) return;
    
    // Add marker
    const marker = L.marker([lat, lng]).addTo(fieldMap);
    mapMarkers.push(marker);
    
    // Add to boundary points
    mapBoundaryPoints.push({ lat: lat, lon: lng });
    
    // Update polygon
    updateMapPolygon();
    
    // Update calculated values
    updateCalculatedValues();
    
    // Update points list display
    updateBoundaryPointsList();
}

function updateMapPolygon() {
    if (mapPolygon) {
        fieldMap.removeLayer(mapPolygon);
    }
    
    if (mapBoundaryPoints.length >= 3) {
        const latLngs = mapBoundaryPoints.map(p => [p.lat, p.lon]);
        mapPolygon = L.polygon(latLngs, {
            color: '#34d399',
            fillColor: '#34d399',
            fillOpacity: 0.3
        }).addTo(fieldMap);
    }
}

function updateCalculatedValues() {
    if (mapBoundaryPoints.length < 3) {
        document.getElementById('field-area-calculated').value = '';
        document.getElementById('field-latitude-calculated').value = '';
        document.getElementById('field-longitude-calculated').value = '';
        return;
    }
    
    // Calculate area using Shoelace formula
    const area = calculatePolygonArea(mapBoundaryPoints);
    const areaHa = area / 10000; // Convert m² to hectares
    
    // Calculate center point
    const center = calculateCenterPoint(mapBoundaryPoints);
    
    document.getElementById('field-area-calculated').value = areaHa.toFixed(2);
    document.getElementById('field-latitude-calculated').value = center.lat.toFixed(6);
    document.getElementById('field-longitude-calculated').value = center.lon.toFixed(6);
}

function calculatePolygonArea(points) {
    // Shoelace formula for polygon area
    let area = 0;
    const n = points.length;
    
    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        const lat1 = points[i].lat;
        const lon1 = points[i].lon;
        const lat2 = points[j].lat;
        const lon2 = points[j].lon;
        
        // Convert to meters (approximate)
        const lat1m = lat1 * 111320;
        const lon1m = lon1 * 111320 * Math.cos(lat1 * Math.PI / 180);
        const lat2m = lat2 * 111320;
        const lon2m = lon2 * 111320 * Math.cos(lat2 * Math.PI / 180);
        
        area += lat1m * lon2m - lat2m * lon1m;
    }
    
    return Math.abs(area) / 2;
}

function calculateCenterPoint(points) {
    let totalLat = 0;
    let totalLon = 0;
    
    points.forEach(p => {
        totalLat += p.lat;
        totalLon += p.lon;
    });
    
    return {
        lat: totalLat / points.length,
        lon: totalLon / points.length
    };
}

function updateBoundaryPointsList() {
    const listDiv = document.getElementById('boundary-points-list');
    if (!listDiv) return;
    
    if (mapBoundaryPoints.length === 0) {
        listDiv.innerHTML = '<p style="color: #94a3b8;">Cliquez sur la carte pour ajouter des points...</p>';
        return;
    }
    
    let html = '';
    mapBoundaryPoints.forEach((p, i) => {
        html += `<div style="padding: 4px; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <strong>Point ${i + 1}:</strong> ${p.lat.toFixed(6)}, ${p.lon.toFixed(6)}
        </div>`;
    });
    
    listDiv.innerHTML = html;
}

function getCurrentLocation() {
    if (!navigator.geolocation) {
        showAlert('❌ La géolocalisation n\'est pas supportée par votre navigateur');
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            if (fieldMap) {
                fieldMap.setView([lat, lng], 16);
                addMapPoint(lat, lng);
            }
        },
        function(error) {
            showAlert('❌ Impossible d\'obtenir votre position: ' + error.message);
        }
    );
}

function clearMapPoints() {
    // Remove markers
    mapMarkers.forEach(marker => fieldMap.removeLayer(marker));
    mapMarkers = [];
    
    // Remove polygon
    if (mapPolygon) {
        fieldMap.removeLayer(mapPolygon);
        mapPolygon = null;
    }
    
    // Clear points
    mapBoundaryPoints = [];
    
    // Clear calculated values
    document.getElementById('field-area-calculated').value = '';
    document.getElementById('field-latitude-calculated').value = '';
    document.getElementById('field-longitude-calculated').value = '';
    
    // Update list
    updateBoundaryPointsList();
}

function undoLastPoint() {
    if (mapMarkers.length === 0) return;
    
    // Remove last marker
    const lastMarker = mapMarkers.pop();
    fieldMap.removeLayer(lastMarker);
    
    // Remove last point
    mapBoundaryPoints.pop();
    
    // Update polygon
    updateMapPolygon();
    
    // Update calculated values
    updateCalculatedValues();
    
    // Update list
    updateBoundaryPointsList();
}

async function loadAdvisorData() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token || !currentUser) return;
        
        const lat = 12.6392, lon = -8.0029;
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/advisor/${currentUser.id}?lat=${lat}&lon=${lon}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateAdviceSection(data);
        }
    } catch (error) {
        console.error('Erreur chargement conseils:', error);
    }
}

function updateAdviceSection(data) {
    const adviceSection = document.getElementById('advice');
    if (!adviceSection) return;
    
    const adviceContainer = adviceSection.querySelector('.advice-box') || adviceSection;
    if (data.recommendation) {
        adviceContainer.innerHTML = `
            <div class="advice-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="advice-title">
                    <i class="fas fa-lightbulb"></i> Conseil Intelligent
                </div>
                <div class="advice-content">
                    <p><strong>Recommandation:</strong> ${data.recommendation || 'Données non disponibles'}</p>
                    ${data.details && data.details.length > 0 ? 
                        data.details.map(d => `<p>${d}</p>`).join('') : ''}
                </div>
            </div>
        `;
    }
}

async function loadFinancialData() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token || !currentUser) return;
        
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/dashboard/${currentUser.id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateFinancialSection(data);
        }
    } catch (error) {
        console.error('Erreur chargement finances:', error);
    }
}

function updateFinancialSection(data) {
    const financialSection = document.getElementById('financial');
    if (!financialSection) return;
    
    const totalRevenue = data.total_revenue || 0;
    const totalCost = data.total_cost || 0;
    const netIncome = data.net_income || 0;
    
    const incomeEl = financialSection.querySelector('.financial-item.income .financial-value');
    const expenseEl = financialSection.querySelector('.financial-item.expense .financial-value');
    
    if (incomeEl) incomeEl.textContent = `${totalRevenue.toLocaleString('fr-FR')} FCFA`;
    if (expenseEl) expenseEl.textContent = `${totalCost.toLocaleString('fr-FR')} FCFA`;
    
    const summaryCards = financialSection.querySelectorAll('.financial-grid + div > div');
    if (summaryCards[0]) summaryCards[0].querySelector('div:last-child').textContent = `${netIncome.toLocaleString('fr-FR')} FCFA`;
    
    initFinanceChart();
}

async function loadAlertsData() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token || !currentUser) return;
        
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/dashboard/${currentUser.id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateAlertsSection(data);
        }
    } catch (error) {
        console.error('Erreur chargement alertes:', error);
    }
}

function updateAlertsSection(data) {
    const alertsSection = document.getElementById('alerts');
    if (!alertsSection) return;
    
    const alertsContainer = alertsSection.querySelector('.alerts-section');
    if (!alertsContainer) return;
    
    let alertsHtml = '';
    
    if (data.weather && data.weather.alert) {
        alertsHtml += `
            <div class="alert-item warning">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <h4>Alerte Météo</h4>
                    <p>${data.weather.alert}</p>
                </div>
            </div>
        `;
    }
    
    if (data.market_info && data.market_info.market_trend) {
        alertsHtml += `
            <div class="alert-item info">
                <div class="alert-icon">💰</div>
                <div class="alert-content">
                    <h4>Tendance Marché</h4>
                    <p>${data.market_info.market_trend}</p>
                </div>
            </div>
        `;
    }
    
    if (alertsHtml) {
        alertsContainer.innerHTML = alertsHtml;
    }
}

async function loadStatisticsData() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token || !currentUser) return;
        
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/dashboard/${currentUser.id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateStatisticsSection(data);
        }
    } catch (error) {
        console.error('Erreur chargement statistiques:', error);
    }
}

function updateStatisticsSection(data) {
    const statsSection = document.getElementById('statistics');
    if (!statsSection) return;
    
    const statBoxes = statsSection.querySelectorAll('.stat-box');
    if (statBoxes.length >= 4) {
        if (data.total_revenue) statBoxes[0].querySelector('.stat-value').textContent = `${data.total_revenue.toLocaleString('fr-FR')} FCFA`;
        if (data.net_income) statBoxes[2].querySelector('.stat-value').textContent = `+${Math.round((data.net_income / (data.total_revenue || 1)) * 100)}%`;
    }
    
    initProductionChart();
    initYieldChart();
}

function initFinanceChart() {
    const financeCtx = document.getElementById('financeChart');
    if (!financeCtx || typeof Chart === 'undefined') return;
    
    const existingChart = (typeof Chart.getChart === 'function' ? Chart.getChart(financeCtx) : null) || financeCtx._chartInstance;
    if (existingChart) {
        try { existingChart.destroy(); } catch(e) {}
    }
    
    financeCtx._chartInstance = new Chart(financeCtx, {
        type: 'bar',
        data: {
            labels: ['Novembre', 'Décembre', 'Janvier'],
            datasets: [{
                label: 'Revenus',
                data: [3500, 4200, 4250],
                backgroundColor: 'rgba(52, 211, 153, 0.7)',
                borderColor: '#34d399',
                borderWidth: 2
            }, {
                label: 'Dépenses',
                data: [1800, 2100, 1850],
                backgroundColor: 'rgba(239, 68, 68, 0.7)',
                borderColor: '#ef4444',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: '#f8fafc' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#cbd5e1' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                x: {
                    ticks: { color: '#cbd5e1' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            }
        }
    });
}

function initProductionChart() {
    const productionCtx = document.getElementById('productionChart');
    if (!productionCtx || typeof Chart === 'undefined') return;
    
    const existingChart = (typeof Chart.getChart === 'function' ? Chart.getChart(productionCtx) : null) || productionCtx._chartInstance;
    if (existingChart) {
        try { existingChart.destroy(); } catch(e) {}
    }
    
    productionCtx._chartInstance = new Chart(productionCtx, {
        type: 'bar',
        data: {
            labels: ['Hivernage précédent', 'Contre-saison', 'Hivernage actuel'],
            datasets: [{
                label: 'Production (tonnes)',
                data: [10.5, 3.2, 12.5],
                backgroundColor: 'rgba(124, 58, 237, 0.7)',
                borderColor: '#7c3aed',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: '#f8fafc' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#cbd5e1' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                x: {
                    ticks: { color: '#cbd5e1' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            }
        }
    });
}

function initYieldChart() {
    const yieldCtx = document.getElementById('yieldChart');
    if (!yieldCtx || typeof Chart === 'undefined') return;
    
    const existingChart = (typeof Chart.getChart === 'function' ? Chart.getChart(yieldCtx) : null) || yieldCtx._chartInstance;
    if (existingChart) {
        try { existingChart.destroy(); } catch(e) {}
    }
    
    yieldCtx._chartInstance = new Chart(yieldCtx, {
        type: 'line',
        data: {
            labels: ['Mil', 'Arachide', 'Maïs', 'Riz', 'Sorgho'],
            datasets: [{
                label: 'Rendement (kg/ha)',
                data: [2200, 1800, 2500, 3200, 1900],
                backgroundColor: 'rgba(34, 211, 238, 0.2)',
                borderColor: '#22d3ee',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: '#f8fafc' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#cbd5e1' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                x: {
                    ticks: { color: '#cbd5e1' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            }
        }
    });
}

async function loadSettingsData() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token || !currentUser) return;
        
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateSettingsSection(data);
        }
    } catch (error) {
        console.error('Erreur chargement paramètres:', error);
    }
}

function updateSettingsSection(data) {
    const profileModal = document.getElementById('profileModal');
    if (!profileModal) return;
    
    const nameInput = document.getElementById('profile-full-name');
    const emailInput = document.getElementById('profile-email-input');
    const phoneInput = document.getElementById('profile-phone-input');
    const villageInput = document.getElementById('profile-village-input');
    const regionInput = document.getElementById('profile-region-input');
    const surfaceInput = document.getElementById('profile-surface-input');
    
    if (nameInput && data.name) nameInput.value = data.name;
    if (emailInput && data.email) emailInput.value = data.email;
    if (phoneInput && data.phone) phoneInput.value = data.phone;
    if (villageInput && data.village) villageInput.value = data.village;
    if (regionInput && data.region) regionInput.value = data.region;
    if (surfaceInput && data.surface_ha) surfaceInput.value = data.surface_ha;
}

async function saveProfile() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            showAlert('❌ Veuillez vous reconnecter');
            return;
        }
        
        const profileData = {
            name: document.getElementById('profile-full-name').value,
            email: document.getElementById('profile-email-input').value,
            phone: document.getElementById('profile-phone-input').value,
            village: document.getElementById('profile-village-input').value,
            region: document.getElementById('profile-region-input').value,
            surface_ha: parseFloat(document.getElementById('profile-surface-input').value)
        };
        
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/me', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(profileData)
        });
        
        if (response.ok) {
            showAlert('✅ Profil mis à jour avec succès!');
            closeModal('profileModal');
            await loadUserProfile();
        } else {
            showAlert('❌ Erreur lors de la mise à jour du profil');
        }
    } catch (error) {
        console.error('Erreur sauvegarde profil:', error);
        showAlert('❌ Erreur lors de la sauvegarde');
    }
}

function refreshWeather() {
    (async function(){
        showAlert('🔄 Actualisation des données météo...');
        const token = localStorage.getItem('accessToken');
        // default demo coordinates (Koulikoro demo)
        let lat = 12.6392, lon = -8.0029;

        // try to read first field coordinates (preferred)
        try {
            if (token) {
                const fieldsResp = await fetch('https://agrosmart-vi8d.onrender.com/api/virtualfarm/fields', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (fieldsResp.ok) {
                    const fields = await fieldsResp.json();
                    if (Array.isArray(fields) && fields.length > 0) {
                        const firstField = fields[0];
                        if (firstField && typeof firstField.latitude === 'number' && typeof firstField.longitude === 'number') {
                            lat = firstField.latitude;
                            lon = firstField.longitude;
                        }
                    }
                } else {
                    // fallback: try /me for possible coordinates
                    const mresp = await fetch('https://agrosmart-vi8d.onrender.com/api/me', { headers: { 'Authorization': `Bearer ${token}` } });
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

        try {
            const resp = await fetch(`https://agrosmart-vi8d.onrender.com/api/weather/?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&_=${Date.now()}`);
            if (!resp.ok) {
                showAlert('Erreur récupération météo');
                return;
            }
            const data = await resp.json();

            // Update all weather widgets on the farmer dashboard
            const widgets = Array.from(document.querySelectorAll('.weather-widget'));
            widgets.forEach(widget => {
                const header = widget.querySelector('.weather-header h3');
                if (header) header.textContent = `🌦️ Météo Actuelle - ${data.location || (lat + ',' + lon)}`;

                const values = widget.querySelectorAll('.weather-current .weather-value');
                if (values && values.length >= 4) {
                    if (values[0]) values[0].textContent = (data.temperature_celsius != null) ? Math.round(data.temperature_celsius) + '°C' : 'N/A';
                    if (values[1]) values[1].textContent = data.summary || 'N/A';
                    if (values[2]) values[2].textContent = data.humidity != null ? (data.humidity + '%') : (data.alert ? data.alert : 'N/A');
                    if (values[3]) values[3].textContent = data.wind_speed != null ? (data.wind_speed + ' km/h') : 'N/A';
                    if (values[4]) values[4].textContent = data.visibility != null ? (data.visibility + ' km') : 'N/A';
                    if (values[5]) values[5].textContent = data.pressure != null ? (data.pressure + ' hPa') : 'N/A';
                }

                const forecastDiv = widget.querySelector('.forecast');
                if (forecastDiv) {
                    forecastDiv.innerHTML = '';
                    if (Array.isArray(data.forecast) && data.forecast.length) {
                        data.forecast.slice(0,7).forEach(item => {
                            const d = document.createElement('div'); d.className = 'forecast-item';
                            // item may be a short string
                            d.innerHTML = `<div class="forecast-day">${item.split('\n')[0].slice(0,20)}</div><div class="forecast-icon">⛅</div><div>${item}</div>`;
                            forecastDiv.appendChild(d);
                        });
                    } else {
                        const d = document.createElement('div'); d.className = 'forecast-item';
                        d.textContent = 'Aucune prévision disponible';
                        forecastDiv.appendChild(d);
                    }
                }
            });

            showAlert('✅ Météo mise à jour');
        } catch (e) {
            console.error('Erreur refreshWeather:', e);
            showAlert('Erreur récupération météo');
        }
    })();
}

async function triggerAutoRetrain() {
    if (!confirm('Démarrer réentrainement automatique des modèles ?')) return;
    const token = localStorage.getItem('accessToken');
    let adminToken = localStorage.getItem('adminToken');
    if (!adminToken) {
        adminToken = prompt('Clé admin requise pour lancer le réentrainement (admin secret):');
        if (adminToken) localStorage.setItem('adminToken', adminToken);
    }
    try {
        const resp = await fetch('https://agrosmart-vi8d.onrender.com/admin/auto-retrain', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`, 'X-Admin-Token': adminToken } });
        if (!resp.ok) {
            const body = await resp.json().catch(()=>({}));
            alert('Erreur démarrage auto-retrain: ' + (body.detail || resp.status));
            return;
        }
        const j = await resp.json();
        const jobId = j.job_id;
        showAlert('Réentrainement démarré — vérification en tâche de fond');

        // Poll status
        let status = 'queued';
        const start = Date.now();
        while (['queued','running'].includes(status) && (Date.now() - start) < 120000) {
            await new Promise(r => setTimeout(r, 2000));
            const sresp = await fetch(`https://agrosmart-vi8d.onrender.com/admin/auto-retrain/${jobId}`, { headers: { 'Authorization': `Bearer ${token}`, 'X-Admin-Token': adminToken } });
            if (!sresp.ok) break;
            const sjson = await sresp.json();
            status = sjson.status;
        }
        alert('Réentrainement terminé ou timeout. Vérifie les logs ou /admin/auto-retrain/' + jobId);
    } catch (e) {
        console.error('Erreur triggerAutoRetrain', e);
        alert('Erreur démarrage auto-retrain. Voir console.');
    }
}

function logout() {
    if (confirm('Êtes-vous sûr de vouloir vous déconnecter?')) {
        localStorage.removeItem('accessToken');
        window.location.href = '/';
    }
}

function showAlert(msg) {
    const alertDiv = document.getElementById('successAlert');
    if (alertDiv) {
        alertDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${msg}`;
        alertDiv.classList.add('active');
        setTimeout(() => {
            alertDiv.classList.remove('active');
        }, 3000);
    }
}

function updateDate() {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const today = new Date();
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
        dateElement.textContent = today.toLocaleDateString('fr-FR', options);
    }
}

function initCharts() {
    // Prix chart
    const priceCtx = document.getElementById('priceChart');
    if (priceCtx && typeof Chart !== 'undefined') {
        new Chart(priceCtx, {
            type: 'line',
            data: {
                labels: ['1 déc', '8 déc', '15 déc', '22 déc', '29 déc', '5 jan', '12 jan', '15 jan'],
                datasets: [{
                    label: 'Mil',
                    data: [280, 285, 290, 295, 300, 295, 300, 300],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Arachide',
                    data: [420, 425, 430, 440, 445, 450, 455, 450],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // Finance chart
    const financeCtx = document.getElementById('financeChart');
    if (financeCtx && typeof Chart !== 'undefined') {
        new Chart(financeCtx, {
            type: 'bar',
            data: {
                labels: ['Novembre', 'Décembre', 'Janvier'],
                datasets: [{
                    label: 'Revenus',
                    data: [3800, 4100, 4250],
                    backgroundColor: '#27ae60'
                }, {
                    label: 'Dépenses',
                    data: [1600, 1750, 1850],
                    backgroundColor: '#e74c3c'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // Production chart
    const productionCtx = document.getElementById('productionChart');
    if (productionCtx && typeof Chart !== 'undefined') {
        new Chart(productionCtx, {
            type: 'bar',
            data: {
                labels: ['Saison 2022', 'Saison 2023', 'Saison 2024'],
                datasets: [{
                    label: 'Production (Tonnes)',
                    data: [10, 11, 12.5],
                    backgroundColor: ['#e74c3c', '#f39c12', '#27ae60']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // Yield chart
    const yieldCtx = document.getElementById('yieldChart');
    if (yieldCtx && typeof Chart !== 'undefined') {
        new Chart(yieldCtx, {
            type: 'radar',
            data: {
                labels: ['Mil', 'Arachide', 'Maïs', 'Riz'],
                datasets: [{
                    label: 'Rendement (kg/ha)',
                    data: [2250, 1950, 2100, 1800],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
}

// Fonctions de chargement des données (compatibilité avec l'ancien système)
async function loadCrops() {
    try {
        if (!currentUser) return;
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}/crops/`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const crops = await response.json();
            displayCrops(crops);
        }
    } catch (error) {
        console.error('Erreur chargement cultures:', error);
    }
}

function displayCrops(crops) {
    const container = document.getElementById('crops-list');
    if (!container) return;

    container.innerHTML = '';

    crops.forEach(crop => {
        const cropCard = document.createElement('div');
        cropCard.className = 'item-card';
        cropCard.innerHTML = `
            <h4>${crop.name}</h4>
            <p>Superficie: ${crop.surface} ha</p>
            <p>Date de plantation: ${crop.planting_date}</p>
            <div class="card-actions">
                <button class="btn-secondary" onclick="editCrop(${crop.id})">Modifier</button>
                <button class="btn-danger" onclick="deleteCrop(${crop.id})">Supprimer</button>
            </div>
        `;
        container.appendChild(cropCard);
    });
}

// Calendar: load events from backend and render
async function loadFarmerCalendar() {
    const grid = document.getElementById('calendar-events-grid');
    const loadingMessage = document.getElementById('calendar-loading-message');
    const errorContainer = document.getElementById('calendar-error-message');
    if (errorContainer) {
        errorContainer.style.display = 'none';
        errorContainer.textContent = '';
    }
    if (grid) {
        grid.innerHTML = '<div id="calendar-loading-message" style="text-align:center; color:#7f8c8d; padding:20px;">Chargement du calendrier...</div>';
    }

    try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            showCalendarError('Vous devez être connecté pour voir le calendrier.');
            return;
        }

        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/farmer/calendar/', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            // Token manquant/expiré
            localStorage.removeItem('accessToken');
            showCalendarError('Session expirée, veuillez vous reconnecter.');
            setTimeout(() => window.location.href = '/login', 1200);
            return;
        }

        if (!response.ok) {
            const txt = await response.text().catch(() => '');
            console.error('Calendrier erreur:', response.status, txt);
            showCalendarError('Erreur serveur lors du chargement du calendrier.');
            return;
        }

        const data = await response.json();
        renderFarmerCalendar(data.events || []);
    } catch (error) {
        console.error('Erreur chargement calendrier:', error);
        showCalendarError('Impossible de charger le calendrier. Vérifiez votre connexion.');
    }
}

function renderFarmerCalendar(events) {
    const grid = document.getElementById('calendar-events-grid');
    const loadingMessage = document.getElementById('calendar-loading-message');
    if (loadingMessage) {
        loadingMessage.style.display = 'none';
    }
    if (!grid) {
        return;
    }
    grid.innerHTML = '';

    if (!events || events.length === 0) {
        grid.innerHTML = `
            <div class="calendar-item empty">
                <div class="calendar-date">Aucun événement</div>
                <div class="calendar-event">Aucune tâche agricole disponible pour le moment.</div>
            </div>
        `;
        return;
    }

    events.forEach(event => {
        const eventDate = new Date(event.date);
        const formattedDate = eventDate.toLocaleDateString('fr-FR', {
            weekday: 'long', day: '2-digit', month: 'long'
        });
        const item = document.createElement('div');
        item.className = 'calendar-item';
        item.innerHTML = `
            <div class="calendar-date">${formattedDate}</div>
            <div class="calendar-event">${event.title}</div>
            <div class="calendar-icon">${event.relative || ''}</div>
            ${event.description ? `<div class="calendar-description">${event.description}</div>` : ''}
        `;
        grid.appendChild(item);
    });
}

function showCalendarError(message) {
    const errorContainer = document.getElementById('calendar-error-message');
    const loadingMessage = document.getElementById('calendar-loading-message');
    if (loadingMessage) {
        loadingMessage.style.display = 'none';
    }
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
}

async function loadListings() {
    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/marketplace/listings', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const listings = await response.json();
            displayListings(listings.listings || listings);
        }
    } catch (error) {
        console.error('Erreur chargement annonces:', error);
    }
}

async function loadSellerListings() {
    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/marketplace/seller/listings', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            displayListings(data.listings || []);
        } else {
            console.error('Erreur chargement annonces vendeur:', response.status);
        }
    } catch (error) {
        console.error('Erreur chargement annonces vendeur:', error);
    }
}

function displayListings(listings) {
    const container = document.getElementById('listings-list');
    if (!container) return;

    container.innerHTML = '';

    listings.forEach(listing => {
        const listingCard = document.createElement('div');
        listingCard.className = 'item-card marketplace-card';

        // Format numbers for display (locale fr-FR, max 2 decimals)
        const price = typeof listing.price_per_unit === 'number' ? listing.price_per_unit : Number(listing.price_per_unit || 0);
        const quantity = typeof listing.quantity === 'number' ? listing.quantity : Number(listing.quantity || 0);
        const priceFmt = price.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
        const quantityFmt = quantity.toLocaleString('fr-FR', { maximumFractionDigits: 2 });

        const safeTitle = listing.title || 'Annonce';
        let safeDesc = listing.description ? listing.description : 'Aucune description disponible';
        if (safeDesc.length > 140) safeDesc = safeDesc.slice(0, 137) + '...';
        const unit = listing.unit || 'kg';
        const location = listing.location || 'Non spécifiée';

        listingCard.innerHTML = `
            <div class="item-card-header">
                <h4>${safeTitle}</h4>
                <span class="price-badge">${priceFmt} XOF/${unit}</span>
                ${!listing.is_active ? '<span class="status-badge inactive">Inactif</span>' : ''}
            </div>
            <div class="item-card-body">
                <p>${safeDesc}</p>
                <div class="item-meta">
                    <span>Quantité: ${quantityFmt} ${unit}</span>
                    <span>Localisation: ${location}</span>
                </div>
            </div>
            <div class="item-card-footer card-actions">
                <button class="btn-secondary" data-id="${listing.id}" aria-label="Voir détails">
                    <i class="fas fa-eye"></i> Voir Détails
                </button>
                <button class="btn-secondary" data-id-edit="${listing.id}">Modifier</button>
                ${listing.is_active 
                    ? `<button class="btn-danger" data-id-deact="${listing.id}">Désactiver</button>`
                    : `<button class="btn-success" data-id-act="${listing.id}">Réactiver</button>`
                }
                <button class="btn-danger" data-id-del="${listing.id}">Supprimer</button>
            </div>
        `;

        // Attach event listeners (avoid inline onclick with raw ids)
        container.appendChild(listingCard);

        const viewBtn = listingCard.querySelector('button[data-id]');
        if (viewBtn) viewBtn.addEventListener('click', () => viewProductDetails(listing.id));
        const editBtn = listingCard.querySelector('button[data-id-edit]');
        if (editBtn) editBtn.addEventListener('click', () => editListing(listing.id));
        const deactBtn = listingCard.querySelector('button[data-id-deact]');
        if (deactBtn) deactBtn.addEventListener('click', () => deactivateListing(listing.id));
        const actBtn = listingCard.querySelector('button[data-id-act]');
        if (actBtn) actBtn.addEventListener('click', () => activateListing(listing.id));
        const delBtn = listingCard.querySelector('button[data-id-del]');
        if (delBtn) delBtn.addEventListener('click', () => deleteListing(listing.id));
    });
}

async function viewProductDetails(listingId) {
    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/listings/${listingId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const product = await response.json();
            displayProductDetails(product);
            showModal('productDetailModal');
        } else {
            console.error('Erreur chargement détails produit:', response.status);
            alert('Erreur lors du chargement des détails du produit');
        }
    } catch (error) {
        console.error('Erreur chargement détails produit:', error);
        alert('Erreur lors du chargement des détails du produit');
    }
}

function displayProductDetails(product) {
    currentSellerId = product.seller?.id || null;

    // Titre
    document.getElementById('productTitle').textContent = product.title;

    // Catégorie et localisation
    document.getElementById('productCategory').textContent = product.category;
    document.getElementById('productLocation').textContent = product.location || 'Non spécifiée';

    // Prix
    const prodPrice = typeof product.price_per_unit === 'number' ? product.price_per_unit : Number(product.price_per_unit || 0);
    const prodQty = typeof product.quantity === 'number' ? product.quantity : Number(product.quantity || 0);
    document.getElementById('productPrice').textContent = `${prodPrice.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} XOF`;
    document.getElementById('productUnit').textContent = `/${product.unit || ''}`;

    // Quantité
    document.getElementById('productQuantity').textContent = `${prodQty.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} ${product.unit || ''}`;

    // Description
    document.getElementById('productDescription').textContent = product.description || 'Aucune description disponible';

    // Images
    displayProductImages(product.images || []);

    // Certifications
    displayCertifications(product);

    // Conditions de vente
    displaySalesConditions(product);

    // Informations vendeur
    displaySellerInfo(product.seller);

    // Avis clients
    displayReviewsSummary(product);
}

function displayProductImages(images) {
    const mainImageContainer = document.getElementById('mainImage');
    const thumbnailsContainer = document.getElementById('imageThumbnails');

    if (images.length === 0) {
        mainImageContainer.innerHTML = '<div style="color: #7f8c8d; font-style: italic;">Aucune image disponible</div>';
        thumbnailsContainer.innerHTML = '';
        return;
    }

    // Image principale (pas de WebP pour les data URIs base64)
    const mainImg = document.getElementById('productMainImg');
    const mainWebp = document.getElementById('productMainImg_webp');
    const first = images[0];
    mainImg.src = first;
    mainImg.style.display = 'block';
    
    // Ne pas créer de variant WebP pour les data URIs base64
    if (mainWebp) {
        mainWebp.srcset = '';
    }

    // Vignettes
    thumbnailsContainer.innerHTML = '';
    images.forEach((image, index) => {
        const thumbnail = document.createElement('div');
        thumbnail.className = `thumbnail ${index === 0 ? 'active' : ''}`;
        thumbnail.innerHTML = `<img src="${image}" alt="Image ${index + 1}">`;
        thumbnail.onclick = () => {
            mainImg.src = image;
            // Ne pas créer de variant WebP pour les data URIs base64
            if (mainWebp) {
                mainWebp.srcset = '';
            }
            document.querySelectorAll('.thumbnail').forEach(t => t.classList.remove('active'));
            thumbnail.classList.add('active');
        };
        thumbnailsContainer.appendChild(thumbnail);
    });
}

function displayCertifications(product) {
    const container = document.getElementById('certificationsList');
    container.innerHTML = '';

    const certifications = [];
    if (product.quality_certified) certifications.push('Qualité');
    if (product.organic_certified) certifications.push('Bio');
    if (product.is_verified) certifications.push('Vérifié');

    if (certifications.length === 0) {
        container.innerHTML = '<span style="color: #7f8c8d; font-style: italic;">Aucune certification</span>';
        return;
    }

    certifications.forEach(cert => {
        const badge = document.createElement('span');
        badge.className = 'certification-badge';
        badge.textContent = cert;
        container.appendChild(badge);
    });
}

function displaySalesConditions(product) {
    const container = document.getElementById('salesConditions');
    container.innerHTML = '';

    const conditions = [
        'Paiement à la livraison',
        'Livraison possible dans un rayon de 50km',
        'Produit frais et de qualité garantie',
        'Support technique disponible'
    ];

    conditions.forEach(condition => {
        const li = document.createElement('li');
        li.textContent = condition;
        container.appendChild(li);
    });
}

function displaySellerInfo(seller) {
    const container = document.getElementById('sellerInfoDetail') || document.getElementById('sellerInfo');

    if (!container) return;

    if (!seller) {
        container.innerHTML = '<span style="color: #7f8c8d; font-style: italic;">Informations vendeur non disponibles</span>';
        return;
    }

    const sellerName = seller.full_name || seller.username || 'Vendeur';
    const sellerInitial = sellerName ? sellerName.charAt(0).toUpperCase() : 'V';

    container.innerHTML = `
        <div class="seller-info">
            <div class="seller-avatar">${sellerInitial}</div>
            <div class="seller-details">
                <h4>${sellerName}</h4>
                <p>${seller.email || ''}</p>
                <p style="margin-top: 8px; color: #7f8c8d; font-size: 14px;">Réputation: ${seller.average_rating ? seller.average_rating.toFixed(1) : '0.0'}/5</p>
            </div>
        </div>
    `;
}

function displayReviewsSummary(product) {
    const container = document.getElementById('reviewsSummary');
    if (!container) return;

    const rating = product.average_rating || 0;
    const reviewCount = product.reviews_count || 0;

    const stars = '★'.repeat(Math.floor(rating)) + '☆'.repeat(5 - Math.floor(rating));

    container.innerHTML = `
        <div class="reviews-summary">
            <div class="rating-stars">${stars}</div>
            <div>
                <span class="rating-score">${rating.toFixed(1)}/5</span>
                <span>(${reviewCount} avis)</span>
            </div>
        </div>
    `;
}

let currentSellerId = null;

function openContactSellerModal() {
    if (!currentSellerId) {
        alert('Vendeur non défini.');
        return;
    }
    document.getElementById('messageSubject').value = '';
    document.getElementById('messageText').value = '';
    document.getElementById('messageEmail').value = currentUser?.email || '';
    showModal('contactSellerModal');
}

function viewSellerProfile() {
    if (!currentSellerId) {
        alert('Vendeur non défini.');
        return;
    }
    loadSellerProfile(currentSellerId);
}

function viewSellerListings() {
    if (!currentSellerId) {
        alert('Vendeur non défini.');
        return;
    }
    closeModal('sellerProfileModal');
    loadListings();
}

async function sendMessageToSeller(event) {
    event.preventDefault();
    if (!currentSellerId) {
        alert('Vendeur non défini.');
        return;
    }

    const payload = {
        subject: document.getElementById('messageSubject').value,
        message: document.getElementById('messageText').value,
        email: document.getElementById('messageEmail').value
    };

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/sellers/${currentSellerId}/contact`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const result = await response.json();
            showAlert(result.message || 'Message envoyé au vendeur.');
            closeModal('contactSellerModal');
        } else {
            const error = await response.json();
            alert(error.detail || 'Erreur lors de l envoi du message.');
        }
    } catch (error) {
        console.error('Erreur envoi message vendeur:', error);
        alert('Erreur lors de l envoi du message.');
    }
}

async function loadSellerProfile(sellerId) {
    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/sellers/${sellerId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (!response.ok) {
            throw new Error(`Status ${response.status}`);
        }

        const seller = await response.json();
        displaySellerProfile(seller);
        showModal('sellerProfileModal');
    } catch (error) {
        console.error('Erreur chargement profil vendeur:', error);
        alert('Impossible de charger le profil du vendeur.');
    }
}

function displaySellerProfile(seller) {
    currentSellerId = seller.id;
    const avatar = document.getElementById('sellerAvatarLarge');
    const name = document.getElementById('sellerNameProfile');
    const rating = document.getElementById('sellerRatingProfile');
    const region = document.getElementById('sellerRegionProfile');
    const activeListing = document.getElementById('sellerActiveListing');
    const completedOrders = document.getElementById('sellerCompletedOrders');
    const avgRating = document.getElementById('sellerAvgRating');
    const reputationScore = document.getElementById('sellerReputationScore');
    const certifications = document.getElementById('sellerCertifications');
    const recentReviews = document.getElementById('sellerRecentReviews');

    if (avatar) avatar.textContent = seller.full_name ? seller.full_name.charAt(0).toUpperCase() : 'V';
    if (name) name.textContent = seller.full_name || 'Vendeur';
    if (rating) rating.innerHTML = `⭐ ${seller.average_rating || 0}/5 (${seller.total_reviews || 0} avis)`;
    if (region) region.textContent = seller.region ? `Région: ${seller.region}` : 'Région: Non spécifiée';
    if (activeListing) activeListing.textContent = seller.active_listings || 0;
    if (completedOrders) completedOrders.textContent = seller.completed_orders || 0;
    if (avgRating) avgRating.textContent = `${seller.average_rating || 0}/5`;
    if (reputationScore) reputationScore.textContent = `${seller.reputation_score || 0}%`;

    certifications.innerHTML = '';
    const certs = [];
    if (seller.quality_certified_products) certs.push(`${seller.quality_certified_products} produit(s) Qualité`);
    if (seller.organic_certified_products) certs.push(`${seller.organic_certified_products} produit(s) Bio`);
    if (certs.length === 0) {
        certifications.innerHTML = '<span style="color: #7f8c8d;">Aucune certification disponible</span>';
    } else {
        certifications.innerHTML = `<ul>${certs.map(c => `<li>${c}</li>`).join('')}</ul>`;
    }

    recentReviews.innerHTML = '';
    if (!seller.recent_reviews || seller.recent_reviews.length === 0) {
        recentReviews.innerHTML = '<p style="color: #7f8c8d;">Aucun avis récent.</p>';
    } else {
        seller.recent_reviews.forEach(review => {
            const reviewItem = document.createElement('div');
            reviewItem.className = 'seller-review-item';
            reviewItem.innerHTML = `
                <div class="seller-review-rating">${'★'.repeat(review.rating) + '☆'.repeat(5 - review.rating)} ${review.rating}/5</div>
                <p>${review.comment || ''}</p>
                <p style="font-size: 12px; color: #7f8c8d;">Posté le ${new Date(review.created_at).toLocaleDateString('fr-FR')}</p>
            `;
            recentReviews.appendChild(reviewItem);
        });
    }
}

function displayOrders(orders) {

    const container = document.getElementById('orders-list');
    if (!container) return;

    container.innerHTML = '';

    orders.forEach(order => {
        const orderCard = document.createElement('div');
        orderCard.className = 'item-card';
        orderCard.innerHTML = `
            <h4>Commande #${order.id}</h4>
            <p><strong>Acheteur:</strong> ${order.buyer?.full_name || order.buyer_id}</p>
            <p>Produit: ${order.listing?.title || 'N/A'}</p>
            <p>Quantité: ${order.quantity} ${order.listing?.unit || ''}</p>
            <p>Total: ${order.total_price?.toLocaleString() || 0} XOF</p>
            <p>Statut: ${order.status}</p>
            <p>Date: ${new Date(order.created_at).toLocaleDateString()}</p>
        `;
        container.appendChild(orderCard);
    });

    if (orders.length === 0) {
        container.innerHTML = '<p class="no-data">Aucune commande reçue pour le moment.</p>';
    }
}

async function loadLoans() {
    try {
        if (!currentUser) return;
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}/loans`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const loans = await response.json();
            displayLoans(loans);
        }
    } catch (error) {
        console.error('Erreur chargement prêts:', error);
    }
}

function displayLoans(loans) {
    const container = document.getElementById('loans-list');
    if (!container) return;

    container.innerHTML = '';

    if (loans.length === 0) {
        container.innerHTML = '<p style="color: #94a3b8;">Aucun prêt en cours</p>';
        return;
    }

    let totalAmount = 0;

    loans.forEach(loan => {
        totalAmount += loan.amount || 0;
        const loanCard = document.createElement('div');
        loanCard.className = 'item-card';
        
        const statusColor = loan.status === 'approved' ? '#34d399' : 
                           loan.status === 'rejected' ? '#ef4444' : '#f59e0b';
        
        loanCard.innerHTML = `
            <h4>Prêt de ${(loan.amount || 0).toLocaleString()} XOF</h4>
            <p>Statut: <span style="color: ${statusColor}; font-weight: bold;">${loan.status}</span></p>
            <p>Durée: ${loan.duration_months || 0} mois</p>
            <p>Usage: ${loan.purpose || 'Non spécifié'}</p>
            ${loan.approved_date ? `<p>Approuvé le: ${new Date(loan.approved_date).toLocaleDateString('fr-FR')}</p>` : ''}
            ${loan.requested_date ? `<p>Demandé le: ${new Date(loan.requested_date).toLocaleDateString('fr-FR')}</p>` : ''}
        `;
        container.appendChild(loanCard);
    });

    // Mettre à jour le montant total du crédit
    const totalCreditElement = document.getElementById('total-credit-amount');
    if (totalCreditElement) {
        totalCreditElement.textContent = `${totalAmount.toLocaleString()} FCFA`;
    }
}

async function loadInsurances() {
    try {
        if (!currentUser) return;
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}/insurances`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const insurances = await response.json();
            displayInsurances(insurances);
        }
    } catch (error) {
        console.error('Erreur chargement assurances:', error);
    }
}

function displayInsurances(insurances) {
    const container = document.getElementById('insurances-list');
    if (!container) return;

    container.innerHTML = '';

    insurances.forEach(insurance => {
        const insuranceCard = document.createElement('div');
        insuranceCard.className = 'item-card';
        insuranceCard.innerHTML = `
            <h4>${insurance.coverage_type}</h4>
            <p>Statut: ${insurance.status}</p>
            <p>Prime: ${insurance.premium} XOF</p>
            <p>Couverture: ${insurance.coverage_amount} XOF</p>
            ${insurance.approved_date ? `<p>Approuvé le: ${insurance.approved_date}</p>` : ''}
        `;
        container.appendChild(insuranceCard);
    });
}

async function handleCropSubmit(e) {
    e.preventDefault();

    const cropData = {
        name: document.getElementById('crop-name').value,
        surface: safeNumber(document.getElementById('crop-surface').value),
        planting_date: document.getElementById('crop-planting-date').value
    };

    try {
        if (!currentUser) return;
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/users/${currentUser.id}/crops/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(cropData)
        });

        if (response.ok) {
            closeModals();
            loadCrops();
            showAlert('Culture ajoutée avec succès!');
        } else {
            alert('Erreur lors de l\'ajout de la culture');
        }
    } catch (error) {
        console.error('Erreur ajout culture:', error);
        alert('Erreur lors de l\'ajout de la culture');
    }
}

function clearListingFormError() {
    const errorElem = document.getElementById('listing-form-error');
    if (errorElem) {
        errorElem.textContent = '';
        errorElem.style.display = 'none';
    }
}

function showListingFormError(message) {
    const errorElem = document.getElementById('listing-form-error');
    if (errorElem) {
        errorElem.textContent = message;
        errorElem.style.display = 'block';
    } else {
        alert(message);
    }
}

function validateListingForm(listingData, files) {
    const errors = [];
    if (!listingData.title.trim()) errors.push('Le titre est requis.');
    if (!listingData.unit.trim()) errors.push('L\'unité est requise.');
    if (listingData.price_per_unit <= 0) errors.push('Le prix doit être supérieur à 0.');
    if (listingData.quantity <= 0) errors.push('La quantité doit être supérieure à 0.');
    if (!listingData.category.trim()) errors.push('La catégorie est requise.');

    if (files.length > 3) {
        errors.push('Maximum 3 images autorisées.');
    }

    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    const maxSize = 2 * 1024 * 1024;
    Array.from(files).forEach((file, index) => {
        if (!allowedTypes.includes(file.type)) {
            errors.push(`Image ${index + 1}: format non supporté (${file.type || 'inconnu'}).`);
        }
        if (file.size > maxSize) {
            errors.push(`Image ${index + 1}: taille maximale 2 Mo.`);
        }
    });

    return errors;
}

async function handleListingSubmit(e) {
    e.preventDefault();
    clearListingFormError();

    const listingImagesInput = document.getElementById('listing-images');
    const files = listingImagesInput ? listingImagesInput.files : [];

    const listingData = {
        title: document.getElementById('listing-title').value,
        description: document.getElementById('listing-description').value,
        price_per_unit: safeNumber(document.getElementById('listing-price').value),
        quantity: safeNumber(document.getElementById('listing-quantity').value, true),
        unit: document.getElementById('listing-unit').value,
        category: document.getElementById('listing-category').value || 'agriculture',
        product_type: document.getElementById('listing-category').value || 'agriculture',
        location: document.getElementById('listing-location').value || currentUser?.region || 'Mali'
    };

    const validationErrors = validateListingForm(listingData, files);
    if (validationErrors.length > 0) {
        showListingFormError(validationErrors.join(' '));
        return;
    }

    const formData = new FormData();
    formData.append('title', listingData.title);
    formData.append('description', listingData.description);
    formData.append('price_per_unit', String(listingData.price_per_unit));
    formData.append('quantity', String(listingData.quantity));
    formData.append('unit', listingData.unit);
    formData.append('category', listingData.category);
    formData.append('product_type', listingData.product_type);
    formData.append('location', listingData.location);

    Array.from(files).forEach(file => {
        formData.append('images', file);
    });

    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/marketplace/listings', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: formData
        });

        if (response.ok) {
            if (listingImagesInput) {
                listingImagesInput.value = '';
            }
            closeModals();
            loadListings();
            showAlert('Annonce créée avec succès!');
        } else {
            const errorText = await response.text();
            showListingFormError('Erreur lors de la création de l\'annonce: ' + errorText);
        }
    } catch (error) {
        console.error('Erreur création annonce:', error);
        showListingFormError('Erreur lors de la création de l\'annonce');
    }
}

// Fonctions d'édition/suppression (compatibilité)
async function editCrop(cropId) {
    if (!currentUser) return;

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/users/${currentUser.id}/crops/${cropId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (!response.ok) {
            alert('Impossible de charger la culture pour l\'édition');
            return;
        }

        const crop = await response.json();
        const name = prompt('Nom de la culture', crop.name);
        if (name === null) return;

        const surfaceText = prompt('Surface (ha)', crop.surface);
        if (surfaceText === null) return;

        const plantingDate = prompt('Date de plantation (YYYY-MM-DD)', crop.planting_date ? crop.planting_date.split('T')[0] : '');
        if (plantingDate === null) return;

        const updateData = {
            name: name.trim() || crop.name,
            surface: safeNumber(surfaceText),
            planting_date: plantingDate || null
        };

        const patchResponse = await fetch(`https://agrosmart-vi8d.onrender.com/users/${currentUser.id}/crops/${cropId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(updateData)
        });

        if (patchResponse.ok) {
            loadCrops();
            showAlert('Culture modifiée avec succès!');
        } else {
            const err = await patchResponse.text();
            console.error('Erreur de modification:', err);
            alert('Erreur lors de la modification de la culture');
        }
    } catch (error) {
        console.error('Erreur édition culture:', error);
        alert('Erreur lors de la modification de la culture');
    }
}

async function deleteCrop(cropId) {
    if (!currentUser) return;

    if (!confirm('Voulez-vous vraiment supprimer cette culture ?')) return;

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/users/${currentUser.id}/crops/${cropId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            loadCrops();
            showAlert('Culture supprimée avec succès!');
        } else {
            const err = await response.text();
            console.error('Erreur suppression culture:', err);
            alert('Erreur lors de la suppression de la culture');
        }
    } catch (error) {
        console.error('Erreur suppression culture:', error);
        alert('Erreur lors de la suppression de la culture');
    }
}

let editingListingId = null;

async function editListing(listingId) {
    if (!listingId) return;

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/listings/${listingId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (!response.ok) {
            throw new Error('Impossible de charger l\'annonce');
        }

        const listing = await response.json();
        editingListingId = listing.id;

        document.getElementById('listing-edit-title').value = listing.title || '';
        document.getElementById('listing-edit-description').value = listing.description || '';
        document.getElementById('listing-edit-price').value = listing.price_per_unit || '';
        document.getElementById('listing-edit-quantity').value = listing.quantity || '';
        document.getElementById('listing-edit-unit').value = listing.unit || '';
        document.getElementById('listing-edit-category').value = listing.category || 'agriculture';
        document.getElementById('listing-edit-location').value = listing.location || '';
        document.getElementById('listing-edit-form-error').style.display = 'none';
        document.getElementById('listing-edit-form-error').textContent = '';

        showModal('editListingModal');
    } catch (error) {
        console.error('Erreur chargement annonce pour édition:', error);
        alert('Impossible de charger l\'annonce pour modification.');
    }
}

async function submitListingEdit(event) {
    event.preventDefault();
    if (!editingListingId) return;

    const payload = {
        title: document.getElementById('listing-edit-title').value.trim(),
        description: document.getElementById('listing-edit-description').value.trim(),
        price_per_unit: safeNumber(document.getElementById('listing-edit-price').value),
        quantity: safeNumber(document.getElementById('listing-edit-quantity').value),
        unit: document.getElementById('listing-edit-unit').value.trim(),
        category: document.getElementById('listing-edit-category').value.trim(),
        location: document.getElementById('listing-edit-location').value.trim(),
    };

    const errorElem = document.getElementById('listing-edit-form-error');
    if (!payload.title || !payload.unit || payload.price_per_unit <= 0 || payload.quantity <= 0) {
        errorElem.textContent = 'Veuillez remplir le titre, l\'unité, le prix et la quantité.';
        errorElem.style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/listings/${editingListingId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({}));
            throw new Error(errorBody.detail || 'Modification impossible');
        }

        closeModal('editListingModal');
        editingListingId = null;
        await loadSellerListings();
        showAlert('✅ Annonce modifiée avec succès');
    } catch (error) {
        console.error('Erreur modification annonce:', error);
        errorElem.textContent = error.message || 'Erreur lors de la modification de l\'annonce.';
        errorElem.style.display = 'block';
    }
}

async function deactivateListing(listingId) {
    if (!confirm('Êtes-vous sûr de vouloir désactiver cette annonce ?')) {
        return;
    }
    
    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/listings/${listingId}/deactivate`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            alert('✅ ' + data.message);
            loadSellerListings(); // Recharger les annonces
        } else {
            const error = await response.json();
            alert('❌ Erreur: ' + (error.detail || 'Impossible de désactiver l\'annonce'));
        }
    } catch (error) {
        console.error('Erreur désactivation:', error);
        alert('❌ Erreur lors de la désactivation de l\'annonce');
    }
}

async function activateListing(listingId) {
    if (!confirm('Êtes-vous sûr de vouloir réactiver cette annonce ?')) {
        return;
    }
    
    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/listings/${listingId}/activate`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            alert('✅ ' + data.message);
            loadSellerListings(); // Recharger les annonces
        } else {
            const error = await response.json();
            alert('❌ Erreur: ' + (error.detail || 'Impossible de réactiver l\'annonce'));
        }
    } catch (error) {
        console.error('Erreur réactivation:', error);
        alert('❌ Erreur lors de la réactivation de l\'annonce');
    }
}

async function deleteListing(listingId) {
    if (!confirm('Êtes-vous sûr de vouloir SUPPRIMER définitivement cette annonce ? Cette action est irréversible.')) {
        return;
    }
    
    try {
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/marketplace/listings/${listingId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            alert('✅ ' + data.message);
            loadSellerListings(); // Recharger les annonces
        } else {
            const error = await response.json();
            alert('❌ Erreur: ' + (error.detail || 'Impossible de supprimer l\'annonce'));
        }
    } catch (error) {
        console.error('Erreur suppression:', error);
        alert('❌ Erreur lors de la suppression de l\'annonce');
    }
}

// ==================== BLOCKCHAIN FUNCTIONS ====================

async function refreshBlockchainStatus() {
    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/blockchain/status/');
        const data = await response.json();

        document.getElementById('blockchain-status').textContent = data.status === 'connected' ? 'Connecté ✅' : 'Déconnecté ❌';
        document.getElementById('trace-count').textContent = data.trace_count || '0';
        document.getElementById('cert-count').textContent = data.certification_count || '0';

        showAlert('✅ Statut blockchain actualisé');
    } catch (error) {
        console.error('Erreur statut blockchain:', error);
        document.getElementById('blockchain-status').textContent = 'Erreur ❌';
        showAlert('❌ Erreur lors de la vérification du statut blockchain');
    }
}

async function createBlockchainTrace() {
    const productType = document.getElementById('trace-product-type').value;
    const quantity = document.getElementById('trace-quantity').value;
    const location = document.getElementById('trace-location').value;
    const productionDate = document.getElementById('trace-production-date').value;
    const description = document.getElementById('trace-description').value;

    if (!productType || !quantity || !location || !productionDate || !description) {
        showAlert('❌ Veuillez remplir tous les champs');
        return;
    }

    const traceData = {
        product_id: `BATCH_${Date.now()}`, // Generate a unique batch ID
        origin: location,
        certification: description.toLowerCase().includes('bio') || description.toLowerCase().includes('organique') ? 'bio' : 'durable',
        timestamp: new Date(productionDate).getTime() / 1000,
        product_type: productType,
        quantity: parseFloat(quantity),
        location: location,
        production_date: productionDate,
        description: description,
        farmer_id: currentUser ? currentUser.id : null
    };

    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/blockchain/trace/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(traceData)
        });

        if (response.ok) {
            const result = await response.json();
            showAlert(`✅ Trace créée avec succès! ID: ${result.trace_id}`);

            // Clear form
            document.getElementById('trace-product-type').value = 'mil';
            document.getElementById('trace-quantity').value = '';
            document.getElementById('trace-location').value = '';
            document.getElementById('trace-production-date').value = '';
            document.getElementById('trace-description').value = '';

            // Refresh traces list
            loadBlockchainTraces();
            refreshBlockchainStatus();
        } else {
            const error = await response.json();
            showAlert(`❌ Erreur: ${error.detail || 'Erreur lors de la création de la trace'}`);
        }
    } catch (error) {
        console.error('Erreur création trace:', error);
        showAlert('❌ Erreur lors de la création de la trace blockchain');
    }
}

async function loadBlockchainTraces() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token) return;
        
        const tracesList = document.getElementById('traces-list');
        if (!tracesList) return;
        
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/blockchain/traces', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateBlockchainSection(data);
        } else {
            tracesList.innerHTML = `
                <div style="text-align: center; color: #e2e8f0; padding: 40px;">
                    <div>Aucune trace blockchain disponible</div>
                </div>
            `;
        }
        
        updateBlockchainStatus();
    } catch (error) {
        console.error('Erreur chargement blockchain:', error);
        const tracesList = document.getElementById('traces-list');
        if (tracesList) {
            tracesList.innerHTML = `
                <div style="text-align: center; color: #e2e8f0; padding: 40px;">
                    <div>Erreur lors du chargement des traces</div>
                </div>
            `;
        }
    }
}

function updateBlockchainSection(data) {
    const tracesList = document.getElementById('traces-list');
    if (!tracesList) return;
    
    if (!data || data.length === 0) {
        tracesList.innerHTML = `
            <div style="text-align: center; color: #e2e8f0; padding: 40px;">
                <div>Aucune trace blockchain disponible</div>
            </div>
        `;
        return;
    }
    
    let html = '';
    data.forEach(trace => {
        html += `
            <div style="background: rgba(255,255,255,0.06); padding: 20px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0; color: #f8fafc;">${trace.product_type || 'Produit'}</h4>
                    <span style="background: rgba(52,211,153,0.2); color: #34d399; padding: 4px 12px; border-radius: 999px; font-size: 12px;">${trace.quantity || 0} kg</span>
                </div>
                <div style="color: #cbd5e1; font-size: 14px; margin-bottom: 8px;">
                    <strong>ID:</strong> ${trace.id || 'N/A'}
                </div>
                <div style="color: #cbd5e1; font-size: 14px; margin-bottom: 8px;">
                    <strong>Localisation:</strong> ${trace.location || 'N/A'}
                </div>
                <div style="color: #cbd5e1; font-size: 14px;">
                    <strong>Date:</strong> ${trace.production_date || 'N/A'}
                </div>
            </div>
        `;
    });
    
    tracesList.innerHTML = html;
}

function updateBlockchainStatus() {
    const statusEl = document.getElementById('blockchain-status');
    const traceCountEl = document.getElementById('trace-count');
    const certCountEl = document.getElementById('cert-count');
    
    if (statusEl) statusEl.textContent = 'Connecté';
    if (traceCountEl) traceCountEl.textContent = '3 traces';
    if (certCountEl) certCountEl.textContent = '2 certifications';
}

function refreshBlockchainStatus() {
    showAlert('🔄 Actualisation du statut blockchain...');
    updateBlockchainStatus();
    loadBlockchainTraces();
}

async function createBlockchainTrace() {
    try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            showAlert('❌ Veuillez vous reconnecter');
            return;
        }
        
        const productType = document.getElementById('trace-product-type').value;
        const quantity = document.getElementById('trace-quantity').value;
        const location = document.getElementById('trace-location').value;
        const productionDate = document.getElementById('trace-production-date').value;
        const description = document.getElementById('trace-description').value;
        
        if (!quantity || !location) {
            showAlert('❌ Veuillez remplir les champs obligatoires');
            return;
        }
        
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/blockchain/traces', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_type: productType,
                quantity: parseFloat(quantity),
                location: location,
                production_date: productionDate,
                description: description
            })
        });
        
        if (response.ok) {
            showAlert('✅ Trace blockchain créée avec succès!');
            document.querySelectorAll('#blockchain input, #blockchain textarea').forEach(input => input.value = '');
            loadBlockchainTraces();
        } else {
            const error = await response.json();
            showAlert(`❌ Erreur: ${error.detail || 'Erreur lors de la création'}`);
        }
    } catch (error) {
        console.error('Erreur création trace:', error);
        showAlert('❌ Erreur lors de la création de la trace');
    }
}

async function verifyBlockchainTrace() {
    try {
        const traceId = document.getElementById('verify-trace-id').value;
        if (!traceId) {
            showAlert('❌ Veuillez entrer un ID de trace');
            return;
        }
        
        const token = localStorage.getItem('accessToken');
        const response = await fetch(`https://agrosmart-vi8d.onrender.com/api/blockchain/traces/${traceId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const resultDiv = document.getElementById('verification-result');
        resultDiv.style.display = 'block';
        
        if (response.ok) {
            const data = await response.json();
            resultDiv.innerHTML = `
                <div style="background: rgba(52,211,153,0.1); padding: 20px; border-radius: 14px; border: 1px solid rgba(52,211,153,0.3);">
                    <h4 style="color: #34d399; margin: 0 0 12px 0;">✅ Trace Valide</h4>
                    <div style="color: #cbd5e1; font-size: 14px;">
                        <strong>Produit:</strong> ${data.product_type || 'N/A'}<br>
                        <strong>Quantité:</strong> ${data.quantity || 0} kg<br>
                        <strong>Localisation:</strong> ${data.location || 'N/A'}<br>
                        <strong>Date:</strong> ${data.production_date || 'N/A'}
                    </div>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div style="background: rgba(239,68,68,0.1); padding: 20px; border-radius: 14px; border: 1px solid rgba(239,68,68,0.3);">
                    <h4 style="color: #ef4444; margin: 0 0 12px 0;">❌ Trace Non Valide</h4>
                    <div style="color: #cbd5e1; font-size: 14px;">
                        Cette trace n'existe pas ou a été modifiée.
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur vérification trace:', error);
        showAlert('❌ Erreur lors de la vérification');
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
            showAlert('📩 Résumé envoyé par SMS ! Vérifiez votre téléphone.');
        } else {
            const error = await response.json();
            showAlert('❌ Erreur: ' + (error.detail || 'Impossible d\'envoyer le SMS'));
        }
    } catch (error) {
        console.error('Erreur sync offline:', error);
        showAlert('❌ Erreur de connexion. Vérifiez que votre numéro de téléphone est configuré.');
    }
}

async function loadSellerBalance() {
    try {
        const response = await fetch('https://agrosmart-vi8d.onrender.com/api/payment-release/seller-balance', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            const balanceElement = document.getElementById('profile-balance');
            const transactionsElement = document.getElementById('profile-transactions');
            
            if (balanceElement) {
                balanceElement.textContent = `${data.net_balance?.toLocaleString('fr-FR') || 0} XOF`;
            }
            
            if (transactionsElement) {
                transactionsElement.textContent = `${data.transaction_count || 0} transactions`;
            }
        } else if (response.status === 403) {
            // Accès refusé - probablement pas un vendeur
            const balanceElement = document.getElementById('profile-balance');
            const transactionsElement = document.getElementById('profile-transactions');
            
            if (balanceElement) {
                balanceElement.textContent = 'Non applicable';
            }
            
            if (transactionsElement) {
                transactionsElement.textContent = 'Non applicable';
            }
        } else {
            const error = await response.json();
            console.error('Erreur solde vendeur:', error);
            const balanceElement = document.getElementById('profile-balance');
            const transactionsElement = document.getElementById('profile-transactions');
            
            if (balanceElement) {
                balanceElement.textContent = 'Erreur';
            }
            
            if (transactionsElement) {
                transactionsElement.textContent = 'Erreur';
            }
        }
    } catch (error) {
        console.error('Erreur chargement solde vendeur:', error);
        const balanceElement = document.getElementById('profile-balance');
        const transactionsElement = document.getElementById('profile-transactions');
        
        if (balanceElement) {
            balanceElement.textContent = 'Erreur';
        }
        
        if (transactionsElement) {
            transactionsElement.textContent = 'Erreur';
        }
    }
}

async function loadFieldList() {
    const token = localStorage.getItem('accessToken');
    const container = document.getElementById('field-list');
    if (!container) return;
    container.innerHTML = '';
    if (!token) return;
    try {
        const resp = await fetch('https://agrosmart-vi8d.onrender.com/api/virtualfarm/fields', { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) return;
        const fields = await resp.json();
        if (!Array.isArray(fields) || fields.length === 0) {
            container.innerHTML = '<div style="color:#94a3b8;">Aucune parcelle enregistrée.</div>';
            return;
        }

        const list = document.createElement('div');
        list.className = 'field-list-grid';
        fields.forEach(f => {
            const card = document.createElement('div');
            card.className = 'field-list-card';
            card.style = 'padding:10px; margin-bottom:8px; background:rgba(255,255,255,0.03); border-radius:8px; display:flex; justify-content:space-between; align-items:center;';
            card.innerHTML = `
                <div style="flex:1">
                    <div style="font-weight:600">${f.name || 'Sans nom'}</div>
                    <div style="font-size:0.85rem; color:#9ca3af">${(f.latitude||'-')+','+(f.longitude||'-')} • ${f.area_ha ? f.area_ha+' ha' : ''}</div>
                </div>
                <div style="display:flex; gap:8px; margin-left:12px">
                    <button class="btn small" onclick="(async()=>{ await editField(${f.id}); })()">Éditer</button>
                    <button class="btn small danger" onclick="(async()=>{ await deleteField(${f.id}); })()">Supprimer</button>
                </div>
            `;
            list.appendChild(card);
        });
        container.appendChild(list);
    } catch (e) {
        console.error('Erreur loadFieldList:', e);
    }
}

// Fallback inline close in case setupEventListeners didn't run or failed earlier
function closeOnboardingInline() {
    try {
        const onboardingModal = document.getElementById('onboarding-modal');
        if (onboardingModal) {
            onboardingModal.classList.remove('open');
        }
        localStorage.setItem('agrosmart-onboarding-seen', '1');
        const onboardingBanner = document.getElementById('onboarding-banner');
        if (onboardingBanner) onboardingBanner.style.display = 'none';
    } catch (e) {
        console.warn('closeOnboardingInline failed', e);
    }
}