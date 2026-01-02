# Deployment Guide - PrenoPinzo

Guida al deployment dell'applicazione PrenoPinzo con Docker.

## Prerequisiti

- Docker e Docker Compose installati
- Account SendGrid (gratuito: 100 email/giorno)
- Git

## Quick Start

```bash
# 1. Clona il repository
git clone <repository-url>
cd PrenoPinzo2

# 2. Crea il file .env
cp .env.example .env

# 3. Modifica .env con i tuoi valori (vedi sezione Configurazione)
nano .env

# 4. Build e avvio
docker-compose up -d --build

# 5. Verifica che tutto funzioni
docker-compose ps
curl http://localhost/health/
```

## Configurazione

### 1. Genera una SECRET_KEY sicura

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copia il risultato in `.env`:
```
SECRET_KEY=il-tuo-token-generato
```

### 2. Configura SendGrid

1. Registrati su [SendGrid](https://signup.sendgrid.com/)
2. Vai su **Settings > API Keys**
3. Crea una nuova API Key con permessi "Mail Send"
4. Copia la chiave in `.env`:
```
SENDGRID_API_KEY=SG.xxxxx
```

5. Configura un **Sender Identity**:
   - Vai su **Settings > Sender Authentication**
   - Aggiungi un mittente verificato
   - Usa quell'email in `FROM_EMAIL`

### 3. Configura gli host

```
ALLOWED_HOSTS=localhost,192.168.1.100,prenopinzo.example.com
APP_BASE_URL=http://192.168.1.100
```

## Comandi Utili

```bash
# Visualizza i log
docker-compose logs -f

# Riavvia i servizi
docker-compose restart

# Stop
docker-compose down

# Rebuild dopo modifiche
docker-compose up -d --build

# Accedi al container Django
docker-compose exec web bash

# Crea un superuser
docker-compose exec web python manage.py createsuperuser

# Backup database
docker-compose exec web cat /app/data/db.sqlite3 > backup.sqlite3
```

## Migrazione Dati Esistenti

Se hai già dati in sviluppo:

```bash
# 1. Copia il database esistente nella cartella data
mkdir -p data
cp db.sqlite3 data/

# 2. Avvia i container
docker-compose up -d --build
```

## Struttura Files

```
PrenoPinzo2/
├── Dockerfile              # Build dell'immagine Django
├── docker-compose.yml      # Orchestrazione servizi
├── nginx/
│   └── nginx.conf          # Configurazione reverse proxy
├── data/                   # Volume per SQLite (creato automaticamente)
├── .env                    # Variabili d'ambiente (NON committare!)
├── .env.example            # Template variabili
├── entrypoint.sh           # Script avvio container
├── gunicorn.conf.py        # Configurazione Gunicorn
└── PrenoPinzo/
    └── settings_prod.py    # Settings di produzione
```

## Troubleshooting

### Container non si avvia
```bash
docker-compose logs web
```

### Errore permessi su data/
```bash
sudo chown -R 1000:1000 data/
```

### Email non arrivano
1. Verifica API key SendGrid in `.env`
2. Controlla i log: `docker-compose logs web | grep -i email`
3. Verifica che il Sender Identity sia verificato

### Static files non caricati
```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```
