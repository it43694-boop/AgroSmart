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

function showError(message) {
  const errorDiv = document.getElementById('signup-error');
  errorDiv.textContent = message;
  errorDiv.classList.add('visible');
}

function clearError() {
  const errorDiv = document.getElementById('signup-error');
  errorDiv.textContent = '';
  errorDiv.classList.remove('visible');
}

async function fetchAPI(endpoint, method = 'GET', body = null) {
  const headers = {};
  let options = { method, headers };

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
    const data = await response.json();
    return { status: response.status, data };
  } catch (error) {
    console.error('Fetch error:', error);
    return { status: 0, data: { detail: String(error.message) } };
  }
}

async function handleSignup(event) {
  event.preventDefault();
  clearError();

  const firstName = document.getElementById('first-name').value.trim();
  const lastName = document.getElementById('last-name').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value.trim();
  const confirmPassword = document.getElementById('confirm-password').value.trim();
  const region = document.getElementById('region').value.trim();
  const surfaceValue = document.getElementById('surface').value.trim();
  const surface = surfaceValue ? parseFloat(surfaceValue) : 0;
  const accountType = document.getElementById('account-type').value;

  // Validation
  if (!firstName || !lastName || !phone || !email || !password || !confirmPassword || !region) {
    showError('Tous les champs sont obligatoires.');
    return;
  }

  if (accountType === 'farmer') {
    if (!surfaceValue || isNaN(surface) || surface <= 0) {
      showError('La surface agricole est obligatoire et doit être positive pour les agriculteurs.');
      return;
    }
  } else {
    if (surfaceValue && (isNaN(surface) || surface < 0)) {
      showError('La surface doit être un nombre positif ou vide.');
      return;
    }
  }

  if (password.length < 8) {
    showError('Le mot de passe doit avoir au moins 8 caractères.');
    return;
  }

  if (password !== confirmPassword) {
    showError('Les mots de passe ne correspondent pas.');
    return;
  }

  const phoneDigits = phone.replace(/[^0-9]/g, '');
  if (phoneDigits.length < 8) {
    showError('Le numéro de téléphone doit contenir au moins 8 chiffres.');
    return;
  }

  if (firstName.length < 2 || lastName.length < 2) {
    showError('Le prénom et le nom doivent comporter au moins 2 caractères.');
    return;
  }

  // Créer le compte
  const userData = {
    full_name: `${firstName} ${lastName}`,
    phone: phone,
    email: email,
    password: password,
    region: region,
    total_surface: surface,
    account_type: accountType,
    role: accountType
  };

  const response = await fetchAPI('/users/', 'POST', userData);

  if (response.status !== 200 && response.status !== 201) {
    const errorMessage = formatError(response.data.detail) || 'Impossible de créer le compte.';
    showError(errorMessage);
    return;
  }

  // Succès - rediriger vers connexion
  alert('Compte créé avec succès ! Votre compte est en attente de validation par un administrateur. Vous recevrez un email une fois validé.');
  window.location.href = '/login';
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('signup-form').addEventListener('submit', handleSignup);
});
