if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/frontend/service-worker.js');
      console.log('PWA: service worker enregistré avec succès', registration.scope);
    } catch (error) {
      console.warn('PWA: échec de l\'enregistrement du service worker', error);
    }
  });
}
