const apiBase = 'https://agrosmart-vi8d.onrender.com/api';

function formatError(detail) {
  if (!detail) return 'Erreur inconnue';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => typeof item === 'string' ? item : JSON.stringify(item)).join(' | ');
  if (typeof detail === 'object') {
    if (detail.message) return detail.message;
    if (detail.detail) return formatError(detail.detail);
    return JSON.stringify(detail);
  }
  return String(detail);
}

function showMessage(text, type = 'success') {
  const message = document.getElementById('setup-message');
  message.textContent = text;
  message.className = `message ${type}`;
  message.style.display = 'block';
}

function hideMessage() {
  const message = document.getElementById('setup-message');
  message.style.display = 'none';
}

function showQrData(qrBase64, backupCodes) {
  const qrSection = document.getElementById('qr-section');
  const qrImage = document.getElementById('qr-image');
  const backupList = document.getElementById('backup-code-list');
  const backupContainer = document.getElementById('backup-codes');

  qrImage.src = qrBase64;
  backupList.innerHTML = '';
  if (Array.isArray(backupCodes) && backupCodes.length > 0) {
    backupCodes.forEach(code => {
      const li = document.createElement('li');
      li.textContent = code;
      backupList.appendChild(li);
    });
    backupContainer.style.display = 'block';
  } else {
    backupContainer.style.display = 'none';
  }
  qrSection.style.display = 'block';
}

async function fetchAPI(endpoint, method = 'GET', body = null) {
  const headers = {};
  let options = { method, headers };
  if (body) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  try {
    const response = await fetch(`${apiBase}${endpoint}`, options);
    const raw = await response.text();
    const data = raw ? JSON.parse(raw) : {};
    return { status: response.status, data };
  } catch (error) {
    console.error('Fetch error:', error);
    return { status: 0, data: { detail: String(error.message) } };
  }
}

async function handleSetup(event) {
  event.preventDefault();
  hideMessage();

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value.trim();

  if (!username || !password) {
    showMessage('Email et mot de passe sont requis.', 'error');
    return;
  }

  const response = await fetchAPI('/auth/mfa/setup', 'POST', { username, password });
  if (response.status !== 200) {
    showMessage(formatError(response.data.detail), 'error');
    return;
  }
  showQrData(response.data.qr_code, response.data.backup_codes);
  showMessage('QR généré. Scannez-le puis entrez le code affiché par votre application MFA.', 'success');
}

async function handleVerify(event) {
  event.preventDefault();
  hideMessage();

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value.trim();
  const totpCode = document.getElementById('totp-code').value.trim();

  if (!username || !password || !totpCode) {
    showMessage('Veuillez renseigner le login, le mot de passe et le code MFA.', 'error');
    return;
  }

  const response = await fetchAPI('/auth/mfa/verify', 'POST', { username, password, totp_code: totpCode });
  if (response.status !== 200) {
    showMessage(formatError(response.data.detail), 'error');
    return;
  }
  showMessage('MFA activée avec succès. Vous pouvez désormais vous connecter avec votre code MFA.', 'success');
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('mfa-setup-form').addEventListener('submit', handleSetup);
  document.getElementById('verify-button').addEventListener('click', handleVerify);
});
