# Déploiement — AgroSmart

Ce fichier décrit les étapes pour déployer la base de données sur Supabase et le frontend sur Cloudflare Pages.

Étapes principales
- Ajouter les Secrets GitHub (Repository Settings → Secrets):
  - `SUPABASE_DATABASE_URL` : chaîne de connexion Postgres (ex: `postgres://user:pass@db.host.supabase.co:5432/postgres`)
  - `SUPABASE_SERVICE_ROLE_KEY` : la `service_role` key (clé privée) — fournie par Supabase
  - `SUPABASE_URL` : l'URL du projet (ex: `https://xxx.supabase.co`)
  - `SECRET_KEY` : clé secrète de l'application
  - `CLOUDFLARE_API_TOKEN` : token API Cloudflare (avec permissions Pages & Accounts)
  - `CLOUDFLARE_ACCOUNT_ID` : ton `Account ID` Cloudflare
  - `CLOUDFLARE_PROJECT_NAME` : nom du projet Pages (optionnel si tu utilises account+project)

Workflows ajoutés
- `.github/workflows/apply_migrations.yml` — déclenchable manuellement ou sur push sur `main`. Installe les dépendances et exécute `alembic upgrade head` en utilisant `SUPABASE_DATABASE_URL`.
- `.github/workflows/deploy_pages.yml` — déploie automatiquement le dossier `frontend/` vers Cloudflare Pages sur push `main`.

Exécution manuelle des migrations (local)
1. Configurer `DATABASE_URL` localement :
```bash
export DATABASE_URL="postgres://user:pass@db.host.supabase.co:5432/postgres"
pip install -r requirements.txt
alembic upgrade head
```
Sous PowerShell (Windows) :
```powershell
$env:DATABASE_URL = "postgres://user:pass@db.host.supabase.co:5432/postgres"
pip install -r requirements.txt
alembic upgrade head
```

Notes de sécurité
- Révoque/rotate les tokens (`SUPABASE_SERVICE_ROLE_KEY`, `CLOUDFLARE_API_TOKEN`) après usage si tu les as exposés ici.
- Ne mets jamais la `service_role` key en clair dans le code ou dans un commit.

Prochaine étape que j'effectue : j'ai ajouté les workflows ; tu peux maintenant pousser ou déclencher manuellement la workflow `apply_migrations` depuis l'onglet Actions.
