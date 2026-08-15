const translations = {
    fr: {
        dashboard: {
            overview: "Aperçu",
            marketplace: "Marketplace",
            orders: "Mes Commandes",
            requests: "Mes Demandes",
            favorites: "Favoris",
            reviews: "Avis",
            weather: "Météo",
            crops: "Cultures",
            finance: "Finance",
            analytics: "Analyses",
            alerts: "Alertes",
            support: "Support"
        },
        auth: {
            login: "Connexion",
            logout: "Déconnexion",
            register: "Inscription",
            email: "Email",
            password: "Mot de passe",
            forgotPassword: "Mot de passe oublié ?",
            loginSuccess: "Connexion réussie",
            loginFailed: "Échec de la connexion"
        },
        farmer: {
            myFields: "Mes Champs",
            myCrops: "Mes Cultures",
            addField: "Ajouter un champ",
            addCrop: "Ajouter une culture",
            harvest: "Récolte",
            planting: "Plantation",
            irrigation: "Irrigation"
        },
        bank: {
            loanRequests: "Demandes de prêt",
            approvedLoans: "Prêts approuvés",
            applyLoan: "Demander un prêt",
            interestRate: "Taux d'intérêt",
            duration: "Durée",
            amount: "Montant"
        },
        insurance: {
            insuranceRequests: "Demandes d'assurance",
            approvedInsurances: "Assurances approuvées",
            claims: "Sinistres",
            applyInsurance: "Souscrire une assurance",
            premium: "Prime",
            coverage: "Couverture"
        },
        common: {
            save: "Enregistrer",
            cancel: "Annuler",
            delete: "Supprimer",
            edit: "Modifier",
            view: "Voir",
            search: "Rechercher",
            filter: "Filtrer",
            loading: "Chargement...",
            noData: "Aucune donnée disponible",
            error: "Erreur",
            success: "Succès",
            confirm: "Confirmer",
            close: "Fermer",
            submit: "Soumettre",
            back: "Retour",
            next: "Suivant",
            previous: "Précédent"
        }
    },
    en: {
        dashboard: {
            overview: "Overview",
            marketplace: "Marketplace",
            orders: "My Orders",
            requests: "My Requests",
            favorites: "Favorites",
            reviews: "Reviews",
            weather: "Weather",
            crops: "Crops",
            finance: "Finance",
            analytics: "Analytics",
            alerts: "Alerts",
            support: "Support"
        },
        auth: {
            login: "Login",
            logout: "Logout",
            register: "Register",
            email: "Email",
            password: "Password",
            forgotPassword: "Forgot password?",
            loginSuccess: "Login successful",
            loginFailed: "Login failed"
        },
        farmer: {
            myFields: "My Fields",
            myCrops: "My Crops",
            addField: "Add Field",
            addCrop: "Add Crop",
            harvest: "Harvest",
            planting: "Planting",
            irrigation: "Irrigation"
        },
        bank: {
            loanRequests: "Loan Requests",
            approvedLoans: "Approved Loans",
            applyLoan: "Apply for Loan",
            interestRate: "Interest Rate",
            duration: "Duration",
            amount: "Amount"
        },
        insurance: {
            insuranceRequests: "Insurance Requests",
            approvedInsurances: "Approved Insurances",
            claims: "Claims",
            applyInsurance: "Apply for Insurance",
            premium: "Premium",
            coverage: "Coverage"
        },
        common: {
            save: "Save",
            cancel: "Cancel",
            delete: "Delete",
            edit: "Edit",
            view: "View",
            search: "Search",
            filter: "Filter",
            loading: "Loading...",
            noData: "No data available",
            error: "Error",
            success: "Success",
            confirm: "Confirm",
            close: "Close",
            submit: "Submit",
            back: "Back",
            next: "Next",
            previous: "Previous"
        }
    },
    ar: {
        dashboard: {
            overview: "نظرة عامة",
            marketplace: "السوق",
            orders: "طلباتي",
            requests: "طلباتي",
            favorites: "المفضلة",
            reviews: "التقييمات",
            weather: "الطقس",
            crops: "المحاصيل",
            finance: "المالية",
            analytics: "التحليلات",
            alerts: "التنبيهات",
            support: "الدعم"
        },
        auth: {
            login: "تسجيل الدخول",
            logout: "تسجيل الخروج",
            register: "التسجيل",
            email: "البريد الإلكتروني",
            password: "كلمة المرور",
            forgotPassword: "نسيت كلمة المرور؟",
            loginSuccess: "تم تسجيل الدخول بنجاح",
            loginFailed: "فشل تسجيل الدخول"
        },
        farmer: {
            myFields: "حقولي",
            myCrops: "محاصيلي",
            addField: "إضافة حقل",
            addCrop: "إضافة محصول",
            harvest: "الحصاد",
            planting: "الزراعة",
            irrigation: "الري"
        },
        bank: {
            loanRequests: "طلبات القروض",
            approvedLoans: "القروض المعتمدة",
            applyLoan: "طلب قرض",
            interestRate: "سعر الفائدة",
            duration: "المدة",
            amount: "المبلغ"
        },
        insurance: {
            insuranceRequests: "طلبات التأمين",
            approvedInsurances: "التأمينات المعتمدة",
            claims: "المطالبات",
            applyInsurance: "التقدم للتأمين",
            premium: "القسط",
            coverage: "التغطية"
        },
        common: {
            save: "حفظ",
            cancel: "إلغاء",
            delete: "حذف",
            edit: "تعديل",
            view: "عرض",
            search: "بحث",
            filter: "تصفية",
            loading: "جاري التحميل...",
            noData: "لا توجد بيانات متاحة",
            error: "خطأ",
            success: "نجاح",
            confirm: "تأكيد",
            close: "إغلاق",
            submit: "إرسال",
            back: "رجوع",
            next: "التالي",
            previous: "السابق"
        }
    }
};

class I18n {
    constructor() {
        this.currentLang = localStorage.getItem('agrosmart_lang') || 'fr';
        this.translations = translations;
    }

    setLanguage(lang) {
        if (this.translations[lang]) {
            this.currentLang = lang;
            localStorage.setItem('agrosmart_lang', lang);
            this.updatePage();
        }
    }

    getLanguage() {
        return this.currentLang;
    }

    t(key) {
        const keys = key.split('.');
        let value = this.translations[this.currentLang];
        
        for (const k of keys) {
            if (value && value[k]) {
                value = value[k];
            } else {
                return key;
            }
        }
        
        return value;
    }

    updatePage() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            element.textContent = this.t(key);
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = this.t(key);
        });

        document.documentElement.lang = this.currentLang;
        document.documentElement.dir = this.currentLang === 'ar' ? 'rtl' : 'ltr';
    }
}

const i18n = new I18n();

document.addEventListener('DOMContentLoaded', () => {
    i18n.updatePage();
});
