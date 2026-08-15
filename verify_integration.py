"""
Script de vérification de l'intégration des nouveaux services AgroSmart
Vérifie que tous les services et routers sont correctement connectés
"""

import sys
import os

def check_service_files():
    """Vérifie que tous les fichiers de services existent"""
    print("🔍 Vérification des fichiers de services...")
    
    services = [
        'services/cache_service.py',
        'services/mfa_service.py',
        'services/mobile_money_service.py',
        'services/gamification_service.py',
        'services/recommendation_service.py',
        'services/sms_ussd_service.py',
        'services/push_notification_service.py'
    ]
    
    missing = []
    for service in services:
        if not os.path.exists(service):
            missing.append(service)
            print(f"❌ {service} - MANQUANT")
        else:
            print(f"✅ {service} - OK")
    
    if missing:
        print(f"\n⚠️ Services manquants: {len(missing)}")
        return False
    print(f"\n✅ Tous les services sont présents ({len(services)})")
    return True

def check_router_files():
    """Vérifie que tous les fichiers de routers existent"""
    print("\n🔍 Vérification des fichiers de routers...")
    
    routers = [
        'routers/gamification.py',
        'routers/recommendations.py',
        'routers/notifications.py',
        'routers/sms_ussd.py',
        'routers/mobile_money.py'
    ]
    
    missing = []
    for router in routers:
        if not os.path.exists(router):
            missing.append(router)
            print(f"❌ {router} - MANQUANT")
        else:
            print(f"✅ {router} - OK")
    
    if missing:
        print(f"\n⚠️ Routers manquants: {len(missing)}")
        return False
    print(f"\n✅ Tous les routers sont présents ({len(routers)})")
    return True

def check_frontend_files():
    """Vérifie que tous les fichiers frontend existent"""
    print("\n🔍 Vérification des fichiers frontend...")
    
    frontend_files = [
        'frontend/i18n.js',
        'frontend/language-selector.js',
        'frontend/push-notifications.js',
        'frontend/manifest.json',
        'frontend/sw.js'
    ]
    
    missing = []
    for file in frontend_files:
        if not os.path.exists(file):
            missing.append(file)
            print(f"❌ {file} - MANQUANT")
        else:
            print(f"✅ {file} - OK")
    
    if missing:
        print(f"\n⚠️ Fichiers frontend manquants: {len(missing)}")
        return False
    print(f"\n✅ Tous les fichiers frontend sont présents ({len(frontend_files)})")
    return True

def check_main_py_integration():
    """Vérifie que main.py a les imports et enregistrements nécessaires"""
    print("\n🔍 Vérification de l'intégration dans main.py...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_imports = [
            'from routers.gamification import router as gamification_router',
            'from routers.recommendations import router as recommendations_router',
            'from routers.notifications import router as notifications_router',
            'from routers.sms_ussd import router as sms_ussd_router',
            'from routers.mobile_money import router as mobile_money_router'
        ]
        
        required_registrations = [
            'app.include_router(gamification_router)',
            'app.include_router(recommendations_router)',
            'app.include_router(notifications_router)',
            'app.include_router(sms_ussd_router)',
            'app.include_router(mobile_money_router)'
        ]
        
        missing_imports = []
        for imp in required_imports:
            if imp not in content:
                missing_imports.append(imp)
                print(f"❌ Import manquant: {imp}")
            else:
                print(f"✅ Import OK: {imp}")
        
        missing_registrations = []
        for reg in required_registrations:
            if reg not in content:
                missing_registrations.append(reg)
                print(f"❌ Enregistrement manquant: {reg}")
            else:
                print(f"✅ Enregistrement OK: {reg}")
        
        if missing_imports or missing_registrations:
            print(f"\n⚠️ Problèmes d'intégration main.py: {len(missing_imports) + len(missing_registrations)}")
            return False
        print(f"\n✅ main.py correctement intégré")
        return True
    except Exception as e:
        print(f"❌ Erreur lecture main.py: {e}")
        return False

def check_requirements_txt():
    """Vérifie que requirements.txt a les nouvelles dépendances"""
    print("\n🔍 Vérification des dépendances dans requirements.txt...")
    
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_deps = [
            'pyotp',
            'qrcode',
            'twilio',
            'africastalking',
            'firebase-admin'
        ]
        
        missing = []
        for dep in required_deps:
            if dep not in content:
                missing.append(dep)
                print(f"❌ Dépendance manquante: {dep}")
            else:
                print(f"✅ Dépendance OK: {dep}")
        
        if missing:
            print(f"\n⚠️ Dépendances manquantes: {len(missing)}")
            return False
        print(f"\n✅ Toutes les dépendances sont présentes ({len(required_deps)})")
        return True
    except Exception as e:
        print(f"❌ Erreur lecture requirements.txt: {e}")
        return False

def check_html_integration():
    """Vérifie que les fichiers HTML ont les scripts nécessaires"""
    print("\n🔍 Vérification de l'intégration dans les fichiers HTML...")
    
    html_files = [
        'frontend/index.html',
        'frontend/farmer-dashboard.html',
        'frontend/admin.html',
        'frontend/bank-dashboard.html',
        'frontend/client-dashboard.html',
        'frontend/iot-dashboard.html',
        'frontend/insurance-dashboard.html'
    ]
    
    required_scripts = [
        '/frontend/i18n.js',
        '/frontend/language-selector.js',
        '/frontend/push-notifications.js'
    ]
    
    issues = []
    for html_file in html_files:
        if not os.path.exists(html_file):
            print(f"⚠️ {html_file} - Fichier manquant")
            continue
        
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for script in required_scripts:
            if script not in content:
                issues.append(f"{html_file} - Script manquant: {script}")
                print(f"❌ {html_file} - {script} manquant")
        
        print(f"✅ {html_file} - Scripts vérifiés")
    
    if issues:
        print(f"\n⚠️ Problèmes d'intégration HTML: {len(issues)}")
        return False
    print(f"\n✅ Tous les fichiers HTML ont les scripts nécessaires")
    return True

def main():
    """Fonction principale de vérification"""
    print("=" * 60)
    print("🔧 VÉRIFICATION DE L'INTÉGRATION AGROSMART")
    print("=" * 60)
    
    results = {
        'services': check_service_files(),
        'routers': check_router_files(),
        'frontend': check_frontend_files(),
        'main_py': check_main_py_integration(),
        'requirements': check_requirements_txt(),
        'html': check_html_integration()
    }
    
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    
    for check, result in results.items():
        status = "✅ OK" if result else "❌ ÉCHEC"
        print(f"{check.upper()}: {status}")
    
    all_ok = all(results.values())
    
    print("\n" + "=" * 60)
    if all_ok:
        print("🎉 TOUT EST CORRECTEMENT INTÉGRÉ!")
        print("=" * 60)
        return 0
    else:
        print("⚠️ CERTAINS PROBLÈMES ONT ÉTÉ DÉTECTÉS")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
