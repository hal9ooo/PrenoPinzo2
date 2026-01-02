# 🏖️ PrenoPinzo

**Sistema di prenotazione per casa vacanze condivisa tra due famiglie**

PrenoPinzo è un'applicazione web Django che permette a due famiglie di gestire la prenotazione della loro casa vacanze in modo equo e trasparente, con un sistema di approvazione reciproca.

## ✨ Funzionalità

### 📅 Gestione Prenotazioni
- **Creazione prenotazioni** con approvazione dall'altra famiglia
- **Drag & Drop** sul calendario per modificare date (con approvazione smart)
- **Sistema di Deroga** per richiedere modifiche su prenotazioni altrui
- **Storico completo** di tutte le azioni (audit log)

### 📱 Mobile-First
- **PWA installabile** su iOS e Android
- **Interfaccia touch-friendly** con FAB e bottom sheet
- **Layout responsive** ottimizzato per ogni schermo
- **Calendario compatto** per mobile

### 💬 Chat Real-Time
- **WebSocket** per messaggi istantanei
- **Emoji picker** integrato
- **Indicatore "sta scrivendo..."**
- **Storico messaggi** persistente

### 📧 Notifiche
- **Email automatiche** per ogni azione importante
- **Supporto SendGrid** per produzione
- **Template HTML** per email professionali
- **Promemoria automatici**:
  - Controllo messaggi chat non letti (ogni 6 ore)
  - Riepilogo settimanale prenotazioni in attesa (Lunedì ore 08:00)

### 📊 Statistiche
- **Dashboard statistiche** con grafici mensili
- **Export iCal** per sincronizzazione calendario
- **Confronto utilizzo** tra famiglie

---

## 🚀 Quick Start

### Prerequisiti
- Docker & Docker Compose
- Git

### Sviluppo Locale

```bash
# Clona il repository
git clone https://github.com/YOUR_USERNAME/PrenoPinzo.git
cd PrenoPinzo

# Crea un virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installa dipendenze
pip install -r requirements.txt

# Crea database e utenti di test
python manage.py migrate
python manage.py createsuperuser

# Avvia server di sviluppo
python manage.py runserver
```

### Produzione con Docker

```bash
# Crea file .env
cp .env.example .env
# Modifica .env con i tuoi valori

# Build e deploy
docker compose up -d --build
```

---

## ⚙️ Configurazione

### Variabili d'Ambiente

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (obbligatorio) |
| `DEBUG` | Modalità debug | `False` |
| `ALLOWED_HOSTS` | Host permessi (comma-separated) | `localhost` |
| `DATABASE_PATH` | Path al database SQLite | `/app/data/db.sqlite3` |
| `SENDGRID_API_KEY` | API key SendGrid per email | - |
| `FROM_EMAIL` | Email mittente | `noreply@prenopinzo.local` |
| `APP_BASE_URL` | URL base dell'app | `http://localhost` |
| `EMAIL_ANDREA` | Email famiglia Andrea | `andrea@example.com` |
| `EMAIL_FABRIZIO` | Email famiglia Fabrizio | `fabrizio@example.com` |

### Esempio .env

```env
SECRET_KEY=your-super-secret-key-here
DEBUG=False
ALLOWED_HOSTS=prenopinzo.example.com,localhost
APP_BASE_URL=https://prenopinzo.example.com
SENDGRID_API_KEY=SG.xxxxx
FROM_EMAIL=PrenoPinzo <noreply@example.com>
EMAIL_ANDREA=andrea@example.com
EMAIL_FABRIZIO=fabrizio@example.com
```

---

## 🛠️ Management Commands

### Reset Database

Cancella tutti i dati e ricrea utenti di test:

```bash
# In Docker
docker exec -it prenopinzo-web python manage.py reset_database

# In sviluppo locale
python manage.py reset_database
```

Questo comando:
- Cancella tutte le prenotazioni, messaggi e audit log
- Ricrea gli utenti `andrea` e `fabrizio` con password di default (da cambiare dopo il primo login)
- Imposta i profili famiglia corretti

---

## 📁 Struttura Progetto

```
PrenoPinzo/
├── bookings/                # App principale
│   ├── consumers.py         # WebSocket consumer per chat
│   ├── email_utils.py       # Utility invio email
│   ├── models.py            # Modelli Django
│   ├── routing.py           # WebSocket routing
│   ├── views.py             # Views HTTP
│   └── templates/           # Template HTML
├── PrenoPinzo/              # Configurazione Django
│   ├── settings.py          # Settings sviluppo
│   ├── settings_prod.py     # Settings produzione
│   └── asgi.py              # ASGI per WebSocket
├── docker-compose.yaml      # Docker Compose config
├── Dockerfile               # Multi-stage Dockerfile
├── entrypoint.sh            # Script avvio container
└── requirements.txt         # Dipendenze Python
```

---

## 🔧 Stack Tecnologico

- **Backend**: Django 6.0, Python 3.12
- **WebSocket**: Django Channels + Daphne
- **Frontend**: Bootstrap 5, FullCalendar, SweetAlert2
- **Database**: SQLite (PostgreSQL-ready)
- **Container**: Docker, Docker Compose
- **Email**: SendGrid SMTP

---

## 📱 PWA

L'app è installabile come Progressive Web App:

- **iOS Safari**: Condividi → Aggiungi a Home
- **Android Chrome**: Menu → Installa App

---

## 🧪 Testing

```bash
# Reset database per test puliti
python manage.py reset_database

# Utenti di test creati:
# - andrea / <password scelta durante setup>
# - fabrizio / <password scelta durante setup>
```

---

## 📄 Licenza

MIT License - Vedi [LICENSE](LICENSE) per dettagli.

---

## 🤝 Contributi

Pull request benvenute! Per modifiche importanti, apri prima un issue.

---

Creato con ❤️ per gestire le vacanze in famiglia senza stress!
