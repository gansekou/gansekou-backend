# Deploiement Gansekou Backend

Backend FastAPI dockerise pour Docker local, Render, Railway, Fly.io, Oracle Cloud et VPS Linux.

## Fichiers persistants

- PostgreSQL: donnees applicatives, migrees avec Alembic.
- `uploads/`: fichiers envoyes par les utilisateurs. En production, montez un volume persistant ou utilisez un stockage objet.
- `logs/` et `storage/`: exclus de l'image Docker. Montez-les en volume si vous les activez plus tard.
- Firebase Admin: ne mettez jamais `firebase_credentials.json` dans l'image.

## Variables d'environnement

Copiez `.env.example` comme base et remplissez les secrets dans votre plateforme cloud.

Variables principales:

- `DATABASE_URL`: URL PostgreSQL, par exemple `postgresql://postgres:postgres@postgres:5432/gansecou_db`.
- `SECRET_KEY`: secret applicatif.
- `CORS_ORIGINS`: liste separee par des virgules.
- `UPLOAD_DIR`: dossier d'uploads dans le conteneur, par defaut `/app/uploads` en Compose.
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`.
- `CAMPAY_BASE_URL`, `CAMPAY_APP_ID`, `CAMPAY_TOKEN`, `CAMPAY_WEBHOOK_KEY`.

Firebase Admin accepte trois modes:

- `FIREBASE_CREDENTIALS_JSON`: JSON complet du service account dans une variable.
- `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`: champs separes.
- `FIREBASE_CREDENTIALS_PATH`: chemin d'un fichier monte en volume, par exemple `/run/secrets/firebase_credentials.json`.

## Docker local

Build:

```bash
docker build -t gansekou-backend .
```

Run avec une base externe:

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:password@host.docker.internal:5432/gansecou_db" \
  -e SECRET_KEY="change-this-secret" \
  -e CORS_ORIGINS="http://localhost:3000" \
  gansekou-backend
```

Endpoints:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Docker Compose

Demarrer l'API et PostgreSQL:

```bash
docker compose up --build
```

Executer les migrations:

```bash
docker compose exec backend alembic upgrade head
```

Arreter:

```bash
docker compose down
```

Supprimer aussi les volumes:

```bash
docker compose down -v
```

## Render

Le fichier `render.yaml` cree:

- un service web Docker;
- une base PostgreSQL;
- un health check sur `/health`;
- les variables necessaires, avec les secrets a renseigner dans Render.

Apres creation du service, renseignez au minimum:

- `CORS_ORIGINS`
- `FIREBASE_CREDENTIALS_JSON` ou les champs Firebase separes
- `OPENAI_API_KEY`
- les variables Campay si les paiements sont actifs

Puis lancez les migrations depuis un shell Render:

```bash
alembic upgrade head
```

## Railway

Railway detecte le `Dockerfile`. Ajoutez un service PostgreSQL Railway et configurez:

```bash
DATABASE_URL=${{Postgres.DATABASE_URL}}
APP_ENV=production
SECRET_KEY=<secret>
CORS_ORIGINS=<frontend-url>
```

Ajoutez ensuite Firebase, OpenAI et Campay comme variables Railway. La commande de demarrage de l'image est deja:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Migrations:

```bash
alembic upgrade head
```

## VPS, Oracle Cloud, Fly.io

Sur un VPS Linux ou Oracle Cloud:

```bash
docker build -t gansekou-backend .
docker run -d --name gansekou-backend \
  -p 8000:8000 \
  --restart unless-stopped \
  --env-file .env.production \
  -v gansekou_uploads:/app/uploads \
  gansekou-backend
docker exec gansekou-backend alembic upgrade head
```

Sur Fly.io, utilisez le `Dockerfile`, creez une base Postgres Fly ou externe, puis ajoutez les secrets avec `fly secrets set`.

## Validation

Commandes utiles:

```bash
python -m compileall app
docker build -t gansekou-backend .
docker compose up --build
docker compose exec backend alembic upgrade head
```
