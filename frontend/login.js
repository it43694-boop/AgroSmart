const apiBase = (window.location.origin || '') + '/api';
const accessTokenKey = 'accessToken';

function formatError(detail) {
  if (!detail) return 'Erreur inconnue';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'string' ? item : JSON.stringify(item)))
      .join(' | ');
  }
  if (typeof detail === 'object') {
    if (detail.message) return detail.message;
    if (detail.detail) return formatError(detail.detail);
    return JSON.stringify(detail);
  }
  return String(detail);
}

function showLoginError(message) {
  const errorDiv = document.getElementById('login-error');
  errorDiv.textContent = message;
  errorDiv.classList.add('visible');
}

function clearLoginError() {
  const errorDiv = document.getElementById('login-error');
  errorDiv.textContent = '';
  errorDiv.classList.remove('visible');
}

async function fetchAPI(endpoint, method = 'GET', body = null, auth = false) {
  const headers = {};
  let options = { method, headers };

  if (auth) {
    const token = localStorage.getItem(accessTokenKey);
    if (!token) {
      window.location.href = '/login';
      return { status: 401, data: { detail: 'Token manquant' } };
    }
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (body) {
    if (body instanceof URLSearchParams) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
      options.body = body.toString();
    } else {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
  }

  try {
    const response = await fetch(`${apiBase}${endpoint}`, options);
    const raw = await response.text();
    let data = {};
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch {
        data = {
          detail: response.ok
            ? 'Réponse serveur invalide.'
            : raw.startsWith('Internal')
              ? 'Erreur interne du serveur. Réessayez ou contactez le support.'
              : raw.slice(0, 200),
        };
      }
    }
    return { status: response.status, data };
  } catch (error) {
    console.error('Fetch error:', error);
    return { status: 0, data: { detail: String(error.message) } };
  }
}

async function handleLogin(event) {
  event.preventDefault();
  clearLoginError();

  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value.trim();
  const mfaCode = document.getElementById('mfa-code').value.trim();
  const adminCode = document.getElementById('admin-code').value.trim();

  // Si on utilise un admin code, le nom d'utilisateur (email) est obligatoire
  if (adminCode && !email) {
    showLoginError("Nom d'utilisateur requis pour connexion admin via code");
    return;
  }

  if (!adminCode && (!email || !password)) {
    showLoginError('Veuillez saisir votre email et votre mot de passe, ou un code administrateur.');
    return;
  }

  const formData = new URLSearchParams();
  if (adminCode) {
    formData.append('admin_code', adminCode);
    if (email) {
      formData.append('username', email);
    }
    if (password) {
      formData.append('password', password);
    }
  } else {
    formData.append('username', email);
    formData.append('password', password);
  }
  if (mfaCode) {
    formData.append('mfa_code', mfaCode);
  }

  const response = await fetchAPI('/token', 'POST', formData, false);
  if (response.status !== 200) {
    const errorMessage = formatError(response.data.detail) || 'Impossible de se connecter.';
    showLoginError(errorMessage);
    return;
  }

  const token = response.data.access_token;
  if (!token) {
    showLoginError('Réponse invalide du serveur.');
    return;
  }

  localStorage.setItem(accessTokenKey, token);

  const meResult = await fetchAPI('/me', 'GET', null, true);
  if (meResult.status !== 200) {
    const errorMessage = formatError(meResult.data.detail) || 'Impossible de récupérer les informations du compte.';
    showLoginError(errorMessage);
    return;
  }

  const user = meResult.data;
  if (user.is_admin) {
    window.location.href = '/admin';
  } else if (user.account_type === 'client') {
    window.location.href = '/client-dashboard';
  } else if (user.account_type === 'farmer') {
    window.location.href = '/farmer-dashboard';
  } else if (user.account_type === 'bank') {
    window.location.href = '/bank-dashboard';
  } else if (user.account_type === 'insurance') {
    window.location.href = '/insurance-dashboard';
  } else {
    window.location.href = '/login';
  }
}

async function checkExistingSession() {
  const token = localStorage.getItem(accessTokenKey);
  if (!token) {
    return;
  }
  const meResult = await fetchAPI('/me', 'GET', null, true);
  if (meResult.status === 200) {
    const user = meResult.data;
    if (user.is_admin) {
      window.location.href = '/admin';
    } else if (user.account_type === 'client') {
      window.location.href = '/client-dashboard';
    } else if (user.account_type === 'farmer') {
      window.location.href = '/farmer-dashboard';
    } else if (user.account_type === 'bank') {
      window.location.href = '/bank-dashboard';
    } else if (user.account_type === 'insurance') {
      window.location.href = '/insurance-dashboard';
    } else {
      window.location.href = '/login';
    }
  } else {
    localStorage.removeItem(accessTokenKey);
  }
}

function setMfaSetupVisible(visible) {
  const panel = document.getElementById('mfa-setup-panel');
  if (!panel) return;
  panel.style.display = visible ? 'block' : 'none';
}

function openMfaSetup() {
  setMfaSetupVisible(true);
  setMfaMessage('');

  const loginEmail = document.getElementById('email')?.value.trim();
  const loginPassword = document.getElementById('password')?.value.trim();
  const setupUsername = document.getElementById('mfa-username');
  const setupPassword = document.getElementById('mfa-password');

  if (loginEmail && !setupUsername.value.trim()) {
    setupUsername.value = loginEmail;
  }
  if (loginPassword && !setupPassword.value.trim()) {
    setupPassword.value = loginPassword;
  }

  const username = setupUsername.value.trim();
  const password = setupPassword.value.trim();
  if (!username || !password) {
    setMfaMessage('Renseignez votre email et mot de passe, puis cliquez à nouveau sur Configurer la MFA pour générer le QR.', false);
    return;
  }

  startMfaSetup();
}

function setMfaQrVisible(visible) {
  const container = document.getElementById('mfa-qr-container');
  if (!container) return;
  container.style.display = visible ? 'block' : 'none';
}

function setMfaMessage(text, isError = false) {
  const msg = document.getElementById('mfa-setup-message');
  if (!msg) return;
  msg.textContent = text;
  msg.style.display = text ? 'block' : 'none';
  msg.style.color = isError ? '#fecaca' : '#bbf7d0';
}

async function startMfaSetup() {
  setMfaMessage('');
  const username = document.getElementById('mfa-username').value.trim();
  const password = document.getElementById('mfa-password').value.trim();
  if (!username || !password) {
    setMfaMessage('Email et mot de passe sont requis pour configurer la MFA.', true);
    return;
  }

  const response = await fetchAPI('/auth/mfa/setup', 'POST', { username, password });
  if (response.status !== 200) {
    setMfaMessage(formatError(response.data.detail), true);
    return;
  }

  const qrImage = document.getElementById('mfa-qr-image');
  const backupList = document.getElementById('mfa-backup-list');
  const backupContainer = document.getElementById('mfa-backup-codes');

  qrImage.src = response.data.qr_code;
  backupList.innerHTML = '';
  if (Array.isArray(response.data.backup_codes) && response.data.backup_codes.length > 0) {
    response.data.backup_codes.forEach(code => {
      const li = document.createElement('li');
      li.textContent = code;
      backupList.appendChild(li);
    });
    backupContainer.style.display = 'block';
  } else {
    backupContainer.style.display = 'none';
  }

  setMfaQrVisible(true);
  setMfaMessage('QR généré. Scannez-le puis entrez le code TOTP.', false);
}

async function confirmMfaSetup() {
  setMfaMessage('');
  const username = document.getElementById('mfa-username').value.trim();
  const password = document.getElementById('mfa-password').value.trim();
  const totpCode = document.getElementById('mfa-totp-code').value.trim();
  if (!username || !password || !totpCode) {
    setMfaMessage('Tous les champs sont requis pour valider la MFA.', true);
    return;
  }

  const response = await fetchAPI('/auth/mfa/verify', 'POST', { username, password, totp_code: totpCode });
  if (response.status !== 200) {
    setMfaMessage(formatError(response.data.detail), true);
    return;
  }

  setMfaMessage('MFA activée avec succès. Vous pouvez maintenant vous connecter avec votre code MFA.', false);
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('login-form').addEventListener('submit', handleLogin);
  document.getElementById('mfa-setup-button').addEventListener('click', openMfaSetup);
  document.getElementById('start-mfa-setup').addEventListener('click', startMfaSetup);
  document.getElementById('confirm-mfa-setup').addEventListener('click', confirmMfaSetup);
  checkExistingSession();
});
