class LanguageSelector {
    constructor() {
        this.currentLang = localStorage.getItem('agrosmart_lang') || 'fr';
        this.languages = [
            { code: 'fr', name: 'Français', flag: '🇫🇷' },
            { code: 'en', name: 'English', flag: '🇬🇧' },
            { code: 'ar', name: 'العربية', flag: '🇸🇦' }
        ];
    }

    init() {
        this.render();
        this.attachEvents();
    }

    render() {
        const container = document.createElement('div');
        container.className = 'language-selector';
        container.innerHTML = `
            <button class="lang-toggle" id="langToggle">
                <span class="current-flag">${this.getCurrentFlag()}</span>
                <span class="current-lang">${this.getCurrentLangName()}</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            </button>
            <div class="lang-dropdown" id="langDropdown">
                ${this.languages.map(lang => `
                    <button class="lang-option ${lang.code === this.currentLang ? 'active' : ''}" 
                            data-lang="${lang.code}">
                        <span class="lang-flag">${lang.flag}</span>
                        <span class="lang-name">${lang.name}</span>
                    </button>
                `).join('')}
            </div>
        `;

        const existingSelector = document.querySelector('.language-selector');
        if (existingSelector) {
            existingSelector.replaceWith(container);
        } else {
            document.body.appendChild(container);
        }
    }

    attachEvents() {
        const toggle = document.getElementById('langToggle');
        const dropdown = document.getElementById('langDropdown');

        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('open');
        });

        document.addEventListener('click', () => {
            dropdown.classList.remove('open');
        });

        dropdown.querySelectorAll('.lang-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const lang = option.dataset.lang;
                this.setLanguage(lang);
                dropdown.classList.remove('open');
            });
        });
    }

    setLanguage(lang) {
        if (typeof i18n !== 'undefined') {
            i18n.setLanguage(lang);
        }
        this.currentLang = lang;
        this.render();
        this.attachEvents();
    }

    getCurrentFlag() {
        const lang = this.languages.find(l => l.code === this.currentLang);
        return lang ? lang.flag : '🇫🇷';
    }

    getCurrentLangName() {
        const lang = this.languages.find(l => l.code === this.currentLang);
        return lang ? lang.name : 'Français';
    }
}

const languageSelector = new LanguageSelector();

document.addEventListener('DOMContentLoaded', () => {
    languageSelector.init();
});
