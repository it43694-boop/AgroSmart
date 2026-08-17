class PushNotificationManager {
    constructor() {
        this.registration = null;
        this.subscription = null;
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
    }

    async init() {
        if (!this.isSupported) {
            console.warn('Push notifications non supportées');
            return;
        }

        try {
            this.registration = await navigator.serviceWorker.register('/sw.js');
            console.log('Service Worker enregistré pour push:', this.registration);
            
            const existingSubscription = await this.registration.pushManager.getSubscription();
            if (existingSubscription) {
                this.subscription = existingSubscription;
                console.log('Subscription existante trouvée');
            }
        } catch (error) {
            console.error('Erreur initialisation push notifications:', error);
        }
    }

    async requestPermission() {
        if (!this.isSupported) return false;

        try {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('Permission accordée');
                return true;
            }
            return false;
        } catch (error) {
            console.error('Erreur demande permission:', error);
            return false;
        }
    }

    async subscribeToPush() {
        if (!this.registration) {
            await this.init();
        }

        if (!this.registration) {
            throw new Error('Service Worker non disponible');
        }

        try {
            const vapidPublicKey = this.getVapidPublicKey();
            const subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(vapidPublicKey)
            });

            this.subscription = subscription;
            
            await this.sendSubscriptionToServer(subscription);
            
            console.log('Subscription réussie');
            return subscription;
        } catch (error) {
            console.error('Erreur subscription:', error);
            throw error;
        }
    }

    async unsubscribeFromPush() {
        if (!this.subscription) return;

        try {
            await this.subscription.unsubscribe();
            this.subscription = null;
            await this.removeSubscriptionFromServer();
            console.log('Désabonnement réussi');
        } catch (error) {
            console.error('Erreur désabonnement:', error);
        }
    }

    async sendSubscriptionToServer(subscription) {
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch('https://agrosmart-vi8d.onrender.com/api/notifications/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    subscription: subscription.toJSON()
                })
            });

            if (!response.ok) {
                throw new Error('Erreur envoi subscription au serveur');
            }

            console.log('Subscription envoyée au serveur');
        } catch (error) {
            console.error('Erreur envoi subscription:', error);
        }
    }

    async removeSubscriptionFromServer() {
        try {
            const token = localStorage.getItem('accessToken');
            await fetch('https://agrosmart-vi8d.onrender.com/api/notifications/unsubscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
        } catch (error) {
            console.error('Erreur suppression subscription:', error);
        }
    }

    getVapidPublicKey() {
        return localStorage.getItem('vapidPublicKey') || 'BD7sX8Y9Z0A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6A7B8C9';
    }

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        
        return outputArray;
    }

    async showLocalNotification(title, body, data = {}) {
        if (Notification.permission === 'granted') {
            new Notification(title, {
                body: body,
                icon: '/icons/icon-192x192.png',
                badge: '/icons/badge-72x72.png',
                data: data
            });
        }
    }
}

const pushNotificationManager = new PushNotificationManager();

document.addEventListener('DOMContentLoaded', () => {
    pushNotificationManager.init();
});
