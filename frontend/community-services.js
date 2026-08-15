const apiBase = window.location.origin || '';
const accessTokenKey = 'accessToken';

function getToken() {
    const token = localStorage.getItem(accessTokenKey);
    if (!token) {
        window.location.href = '/login';
        return null;
    }
    return token;
}

function formatDetail(data) {
    if (!data) return 'Erreur inconnue';
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map((d) => d.msg || String(d)).join(' | ');
    return 'Erreur serveur';
}

async function api(endpoint, method = 'GET', body = null) {
    const token = getToken();
    if (!token) return null;
    const headers = { Authorization: `Bearer ${token}` };
    const options = { method, headers };
    if (body) {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }
    const res = await fetch(`${apiBase}${endpoint}`, options);
    let data = null;
    try {
        data = await res.json();
    } catch {
        data = { detail: 'Réponse invalide' };
    }
    if (res.status === 401) {
        localStorage.removeItem(accessTokenKey);
        window.location.href = '/login';
    }
    return { ok: res.ok, status: res.status, data };
}

function showMsg(elId, text, isError = false) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    el.className = isError ? 'msg error' : 'msg success';
    el.style.display = 'block';
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.toggle('active', b.dataset.tab === tabId));
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.toggle('active', p.id === `panel-${tabId}`));
}

async function loadFeed() {
    const expOnly = document.getElementById('filter-experience').checked;
    const q = expOnly ? '?experience_share=true' : '';
    const res = await api(`/api/community/posts/${q}`);
    const list = document.getElementById('posts-list');
    if (!res?.ok) {
        list.innerHTML = '<p class="empty">Impossible de charger le fil.</p>';
        return;
    }
    const posts = res.data || [];
    if (!posts.length) {
        list.innerHTML = '<p class="empty">Aucune publication pour le moment.</p>';
        return;
    }
    list.innerHTML = posts
        .map(
            (p) => `
        <article class="card post" data-id="${p.id}">
            <div class="post-head">
                <strong>${escapeHtml(p.title)}</strong>
                ${p.experience_share ? '<span class="badge">Expérience</span>' : ''}
            </div>
            <p>${escapeHtml(p.content)}</p>
            <div class="post-meta">
                <span><i class="fas fa-heart"></i> ${p.likes || 0}</span>
                <button type="button" class="btn-sm" data-like="${p.id}">J'aime</button>
                <button type="button" class="btn-sm" data-comments="${p.id}">Commentaires</button>
            </div>
            <div class="comments" id="comments-${p.id}" hidden></div>
        </article>`
        )
        .join('');
    list.querySelectorAll('[data-like]').forEach((btn) => {
        btn.addEventListener('click', () => likePost(btn.dataset.like));
    });
    list.querySelectorAll('[data-comments]').forEach((btn) => {
        btn.addEventListener('click', () => toggleComments(btn.dataset.comments));
    });
}

function escapeHtml(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

async function likePost(postId) {
    const res = await api(`/api/community/posts/${postId}/like/`, 'POST');
    if (res?.ok) loadFeed();
}

async function toggleComments(postId) {
    const box = document.getElementById(`comments-${postId}`);
    if (!box) return;
    if (!box.hidden) {
        box.hidden = true;
        return;
    }
    const res = await api(`/api/community/posts/${postId}/comments/`);
    const comments = res?.ok ? res.data : [];
    box.innerHTML = `
        <div class="comment-list">${(comments || [])
            .map((c) => `<p><b>#${c.author_id}</b>: ${escapeHtml(c.content)}</p>`)
            .join('')}</div>
        <div class="comment-form">
            <input type="text" id="comment-input-${postId}" placeholder="Votre commentaire..." />
            <button type="button" class="btn-sm" data-submit-comment="${postId}">Envoyer</button>
        </div>`;
    box.hidden = false;
    box.querySelector('[data-submit-comment]').addEventListener('click', () => submitComment(postId));
}

async function submitComment(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    const content = input?.value?.trim();
    if (!content) return;
    const res = await api(`/api/community/posts/${postId}/comments/`, 'POST', { content });
    if (res?.ok) {
        input.value = '';
        toggleComments(postId);
        toggleComments(postId);
    }
}

async function loadGroups() {
    const res = await api('/api/community/groups/');
    const list = document.getElementById('groups-list');
    if (!res?.ok) {
        list.innerHTML = '<p class="empty">Erreur chargement groupes.</p>';
        return;
    }
    const groups = res.data || [];
    list.innerHTML = groups.length
        ? groups
              .map(
                  (g) => `
            <div class="card">
                <strong>${escapeHtml(g.name)}</strong>
                <p>${escapeHtml(g.description || '')}</p>
                <button type="button" class="btn-sm" data-join-group="${g.id}">Rejoindre</button>
            </div>`
              )
              .join('')
        : '<p class="empty">Aucun groupe.</p>';
    list.querySelectorAll('[data-join-group]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const r = await api(`/api/community/groups/${btn.dataset.joinGroup}/join/`, 'POST');
            showMsg('community-msg', r?.ok ? 'Groupe rejoint.' : r?.data?.detail || 'Erreur', !r?.ok);
        });
    });
}

async function loadEnrollments() {
    const res = await api('/api/learning/enrollments/');
    const list = document.getElementById('enrollments-list');
    if (!res?.ok) {
        list.innerHTML = '<p class="empty">Aucune inscription.</p>';
        return;
    }
    const rows = res.data || [];
    list.innerHTML = rows.length
        ? rows
              .map(
                  (e) => `
            <div class="card">
                <strong>${escapeHtml(e.course_title || 'Cours #' + e.course_id)}</strong>
                <p class="meta">${e.content_type || ''} · ${e.progress_percent}% ${e.completed ? '(terminé)' : ''}</p>
            </div>`
              )
              .join('')
        : '<p class="empty">Aucune inscription pour le moment.</p>';
}

async function loadLearning(contentType) {
    const q = contentType ? `?content_type=${encodeURIComponent(contentType)}` : '';
    const res = await api(`/api/learning/courses/${q}`);
    const listId = contentType === 'tutorial' ? 'tutorials-list' : 'courses-list';
    const list = document.getElementById(listId);
    if (!res?.ok) {
        list.innerHTML = '<p class="empty">Erreur chargement.</p>';
        return;
    }
    const courses = res.data || [];
    list.innerHTML = courses.length
        ? courses
              .map(
                  (c) => `
            <div class="card">
                <strong>${escapeHtml(c.title)}</strong>
                <p>${escapeHtml(c.description || '')}</p>
                <p class="meta">${c.level} · ${c.category || 'général'}</p>
                ${c.video_url ? `<a href="${escapeHtml(c.video_url)}" target="_blank" rel="noopener">Voir la vidéo</a>` : ''}
                <button type="button" class="btn-sm" data-enroll="${c.id}">S'inscrire</button>
                <button type="button" class="btn-sm" data-progress="${c.id}">Marquer 100%</button>
            </div>`
              )
              .join('')
        : '<p class="empty">Aucun contenu publié.</p>';
    list.querySelectorAll('[data-enroll]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const r = await api(`/api/learning/courses/${btn.dataset.enroll}/enroll/`, 'POST');
            showMsg('learning-msg', r?.ok ? 'Inscription enregistrée.' : formatDetail(r?.data), !r?.ok);
            if (r?.ok) loadEnrollments();
        });
    });
    list.querySelectorAll('[data-progress]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const r = await api(`/api/learning/courses/${btn.dataset.progress}/progress/`, 'PATCH', {
                progress_percent: 100,
            });
            showMsg('learning-msg', r?.ok ? 'Progression mise à jour.' : r?.data?.detail || 'Erreur', !r?.ok);
        });
    });
}

async function loadWebinars() {
    const res = await api('/api/learning/webinars/?upcoming=true');
    const list = document.getElementById('webinars-list');
    if (!res?.ok) {
        list.innerHTML = '<p class="empty">Erreur webinaires.</p>';
        return;
    }
    const items = res.data || [];
    list.innerHTML = items.length
        ? items
              .map(
                  (w) => `
            <div class="card">
                <strong>${escapeHtml(w.title)}</strong>
                <p>${escapeHtml(w.description || '')}</p>
                <p class="meta">${new Date(w.scheduled_at).toLocaleString('fr-FR')}</p>
                <button type="button" class="btn-sm" data-register-webinar="${w.id}">S'inscrire</button>
            </div>`
              )
              .join('')
        : '<p class="empty">Aucun webinaire à venir.</p>';
    list.querySelectorAll('[data-register-webinar]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const r = await api(`/api/learning/webinars/${btn.dataset.registerWebinar}/register/`, 'POST');
            showMsg('learning-msg', r?.ok ? 'Inscription webinaire OK.' : r?.data?.detail || 'Erreur', !r?.ok);
        });
    });
}

async function loadCooperatives() {
    const res = await api('/api/cooperatives/');
    const list = document.getElementById('coops-list');
    if (!res?.ok) {
        list.innerHTML = '<p class="empty">Erreur coopératives.</p>';
        return;
    }
    const coops = res.data || [];
    list.innerHTML = coops.length
        ? coops
              .map(
                  (c) => `
            <div class="card coop-card" data-coop-id="${c.id}">
                <strong>${escapeHtml(c.name)}</strong>
                <p>${escapeHtml(c.region || '')} — ${escapeHtml(c.description || '')}</p>
                <button type="button" class="btn-sm" data-join-coop="${c.id}">Demander adhésion</button>
                <button type="button" class="btn-sm" data-dashboard="${c.id}">Tableau de bord</button>
                <button type="button" class="btn-sm" data-purchases="${c.id}">Achats groupés</button>
            </div>`
              )
              .join('')
        : '<p class="empty">Aucune coopérative. Créez-en une ci-dessous.</p>';
    list.querySelectorAll('[data-join-coop]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const r = await api(`/api/cooperatives/${btn.dataset.joinCoop}/join/`, 'POST');
            showMsg('coop-msg', r?.ok ? (r.data?.message || 'Demande envoyée.') : r?.data?.detail || 'Erreur', !r?.ok);
        });
    });
    list.querySelectorAll('[data-dashboard]').forEach((btn) => {
        btn.addEventListener('click', () => loadCoopDashboard(btn.dataset.dashboard));
    });
    list.querySelectorAll('[data-purchases]').forEach((btn) => {
        btn.addEventListener('click', () => loadCoopPurchases(btn.dataset.purchases));
    });
}

async function loadCoopDashboard(coopId) {
    const res = await api(`/api/cooperatives/${coopId}/dashboard/`);
    const box = document.getElementById('coop-detail');
    if (!res?.ok) {
        box.innerHTML = `<p class="empty">${res?.data?.detail || 'Erreur'}</p>`;
        return;
    }
    const d = res.data;
    box.innerHTML = `
        <h3>${escapeHtml(d.name)}</h3>
        <p>Membres actifs: <b>${d.total_members}</b> · Contributions: <b>${d.total_contributions}</b> F CFA</p>
        <p>Achats groupés ouverts: <b>${d.active_group_purchases}</b></p>`;
    document.getElementById('purchase-coop-id').value = coopId;
    document.getElementById('training-coop-id').value = coopId;
    loadCoopTrainings(coopId);
}

async function loadCoopPurchases(coopId) {
    const res = await api(`/api/cooperatives/${coopId}/purchases/?status=open`);
    const box = document.getElementById('purchases-list');
    if (!res?.ok) {
        box.innerHTML = '<p class="empty">Erreur achats.</p>';
        return;
    }
    const items = res.data || [];
    box.innerHTML = items.length
        ? items
              .map(
                  (p) => `
            <div class="card">
                <strong>${escapeHtml(p.product_name)}</strong>
                <p>${p.quantity_committed || 0} / ${p.quantity_needed} · Budget max ${p.budget_max} F CFA</p>
                <input type="number" min="0.1" step="0.1" placeholder="Quantité" id="qty-${p.id}" />
                <button type="button" class="btn-sm" data-join-purchase="${p.id}">Participer</button>
            </div>`
              )
              .join('')
        : '<p class="empty">Aucun achat groupé ouvert.</p>';
    box.querySelectorAll('[data-join-purchase]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const qty = parseFloat(document.getElementById(`qty-${btn.dataset.joinPurchase}`)?.value);
            if (!qty || qty <= 0) {
                showMsg('coop-msg', 'Indiquez une quantité valide.', true);
                return;
            }
            const r = await api(`/api/cooperatives/purchases/${btn.dataset.joinPurchase}/join/`, 'POST', {
                quantity_committed: qty,
            });
            showMsg('coop-msg', r?.ok ? 'Participation enregistrée.' : r?.data?.detail || 'Erreur', !r?.ok);
            loadCoopPurchases(coopId);
        });
    });
}

async function loadCoopTrainings(coopId) {
    const res = await api(`/api/cooperative/trainings/?cooperative_id=${coopId}`);
    const box = document.getElementById('trainings-list');
    if (!res?.ok) {
        box.innerHTML = '<p class="empty">Erreur formations.</p>';
        return;
    }
    const items = res.data || [];
    box.innerHTML = items.length
        ? items
              .map(
                  (t) => `
            <div class="card">
                <strong>${escapeHtml(t.topic)}</strong>
                <p>${new Date(t.session_date).toLocaleString('fr-FR')} · ${t.capacity} places</p>
                <button type="button" class="btn-sm" data-join-training="${t.id}">Rejoindre</button>
            </div>`
              )
              .join('')
        : '<p class="empty">Aucune formation planifiée.</p>';
    box.querySelectorAll('[data-join-training]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const r = await api(`/api/cooperative/trainings/${btn.dataset.joinTraining}/join/`, 'POST');
            showMsg('coop-msg', r?.ok ? 'Inscription formation OK.' : r?.data?.detail || 'Erreur', !r?.ok);
        });
    });
}

function bindForms() {
    document.getElementById('form-post').addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = {
            title: document.getElementById('post-title').value.trim(),
            content: document.getElementById('post-content').value.trim(),
            experience_share: document.getElementById('post-experience').checked,
            group_id: document.getElementById('post-group-id').value
                ? parseInt(document.getElementById('post-group-id').value, 10)
                : null,
        };
        const r = await api('/api/community/posts/', 'POST', body);
        showMsg('community-msg', r?.ok ? 'Publication créée.' : r?.data?.detail || 'Erreur', !r?.ok);
        if (r?.ok) {
            e.target.reset();
            loadFeed();
        }
    });

    document.getElementById('form-group').addEventListener('submit', async (e) => {
        e.preventDefault();
        const r = await api('/api/community/groups/', 'POST', {
            name: document.getElementById('group-name').value.trim(),
            description: document.getElementById('group-desc').value.trim(),
            privacy: document.getElementById('group-privacy').value,
        });
        showMsg('community-msg', r?.ok ? 'Groupe créé.' : r?.data?.detail || 'Erreur', !r?.ok);
        if (r?.ok) loadGroups();
    });

    document.getElementById('form-coop').addEventListener('submit', async (e) => {
        e.preventDefault();
        const r = await api('/api/cooperatives/', 'POST', {
            name: document.getElementById('coop-name').value.trim(),
            region: document.getElementById('coop-region').value.trim(),
            description: document.getElementById('coop-desc').value.trim(),
        });
        showMsg('coop-msg', r?.ok ? 'Coopérative créée.' : r?.data?.detail || 'Erreur', !r?.ok);
        if (r?.ok) loadCooperatives();
    });

    document.getElementById('form-purchase').addEventListener('submit', async (e) => {
        e.preventDefault();
        const r = await api('/api/cooperatives/purchases/', 'POST', {
            cooperative_id: parseInt(document.getElementById('purchase-coop-id').value, 10),
            product_name: document.getElementById('purchase-product').value.trim(),
            quantity_needed: parseFloat(document.getElementById('purchase-qty').value),
            budget_max: parseFloat(document.getElementById('purchase-budget').value),
        });
        showMsg('coop-msg', r?.ok ? 'Achat groupé lancé.' : r?.data?.detail || 'Erreur', !r?.ok);
        if (r?.ok) loadCoopPurchases(document.getElementById('purchase-coop-id').value);
    });

    document.getElementById('form-training').addEventListener('submit', async (e) => {
        e.preventDefault();
        const r = await api('/api/cooperative/trainings/', 'POST', {
            cooperative_id: parseInt(document.getElementById('training-coop-id').value, 10),
            topic: document.getElementById('training-topic').value.trim(),
            description: document.getElementById('training-desc').value.trim(),
            session_date: new Date(document.getElementById('training-date').value).toISOString(),
            capacity: parseInt(document.getElementById('training-capacity').value, 10) || 20,
        });
        showMsg('coop-msg', r?.ok ? 'Formation créée.' : r?.data?.detail || 'Erreur', !r?.ok);
        if (r?.ok) loadCoopTrainings(document.getElementById('training-coop-id').value);
    });

    const formLearning = document.getElementById('form-learning');
    if (formLearning) {
        formLearning.addEventListener('submit', async (e) => {
            e.preventDefault();
            const type = document.getElementById('learn-content-type').value;
            const r = await api('/api/learning/courses/', 'POST', {
                title: document.getElementById('learn-title').value.trim(),
                description: document.getElementById('learn-desc').value.trim(),
                video_url: document.getElementById('learn-video').value.trim() || null,
                category: document.getElementById('learn-category').value.trim() || null,
                level: document.getElementById('learn-level').value,
                content_type: type,
            });
            showMsg('learning-msg', r?.ok ? 'Contenu publié.' : formatDetail(r?.data), !r?.ok);
            if (r?.ok) {
                e.target.reset();
                loadLearning('course');
                loadLearning('tutorial');
            }
        });
    }

    const formWebinar = document.getElementById('form-webinar');
    if (formWebinar) {
        formWebinar.addEventListener('submit', async (e) => {
            e.preventDefault();
            const r = await api('/api/learning/webinars/', 'POST', {
                title: document.getElementById('webinar-title').value.trim(),
                description: document.getElementById('webinar-desc').value.trim(),
                scheduled_at: new Date(document.getElementById('webinar-date').value).toISOString(),
                presenter: document.getElementById('webinar-presenter').value.trim() || null,
                registration_link: document.getElementById('webinar-link').value.trim() || null,
            });
            showMsg('learning-msg', r?.ok ? 'Webinaire créé.' : formatDetail(r?.data), !r?.ok);
            if (r?.ok) {
                e.target.reset();
                loadWebinars();
            }
        });
    }

    document.getElementById('filter-experience').addEventListener('change', loadFeed);
    document.querySelectorAll('.tab-btn').forEach((btn) => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (!getToken()) return;
    bindForms();
    loadFeed();
    loadGroups();
    loadLearning('course');
    loadLearning('tutorial');
    loadWebinars();
    loadEnrollments();
    loadCooperatives();
});
