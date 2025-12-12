# Analisi e Specifiche Tecniche - PrenoPinzo

Questo documento fornisce un'analisi approfondita e le specifiche tecniche per ricreare l'applicazione di gestione prenotazioni vacanze "PrenoPinzo". L'applicazione gestisce la condivisione di una casa vacanze tra due nuclei familiari ("Andrea" e "Fabrizio").

## 1. Panoramica
L'obiettivo è permettere ai due gruppi familiari di prenotare periodi di vacanza in modo equo, con un sistema di approvazione reciproca e negoziazione.

## 2. Entità e Dati

### 2.1 Utenti e Gruppi
- **Gruppi**: Esistono due gruppi fondamentali: `Famiglia Andrea` e `Famiglia Fabrizio`.
- **Utenti**: Ogni utente appartiene a uno di questi due gruppi.
- **Ruoli**:
    - **Owner** (Richiedente): Chi crea la prenotazione.
    - **Approver** (Controparte): Il gruppo opposto che deve approvare la richiesta.

### 2.2 Prenotazione (Booking)
- **Campi Principali**:
    - `user`: Utente che ha creato la prenotazione (FK User).
    - `family_group`: Gruppo di appartenenza ('Andrea' o 'Fabrizio').
    - `start_date`, `end_date`: Date del soggiorno.
    - `title`: Titolo/Descrizione (es. "Vacanze Estive").
    - `status`: Stato corrente della prenotazione.
    - `pending_with`: Indica quale gruppo deve compiere la prossima azione ('Andrea' o 'Fabrizio').
    - `rejection_note`: Motivazione dell'ultimo rifiuto (se presente).

- **Campi Deroga (Revisione)**:
    - Utilizzati quando un non-proprietario chiede di spostare una prenotazione già approvata.
    - `original_start_date`, `original_end_date`: Backup delle date approvate.
    - `deroga_requested_by`: Chi ha chiesto la modifica.
    - `deroga_note`: Motivo della richiesta.

### 2.3 Audit Log (BookingAudit)
- Traccia ogni modifica significativa per la cronologia ("Storico").
- **Azioni Tracciate**: Creazione, Modifica Date, Approvazione, Rifiuto, Richiesta Deroga, Accettazione/Rifiuto Deroga, Cancellazione.

## 3. Macchina a Stati (Workflow)

### 3.1 Stati Possibili
- `NEGOTIATION` (In Negoziazione): Stato iniziale o dopo una modifica. Richiede approvazione.
- `APPROVED` (Approvata): Prenotazione confermata. Visibile come "ferma" nel calendario.
- `REJECTED` (Rifiutata Definitiva): Raramente usato nel flusso corrente (preferita la negoziazione).
- `CANCELLED` (Cancellata): Eliminata dal proprietario.
- `DEROGA` (Richiesta Revisione): Stato speciale per richieste di modifica su periodi approvati.

### 3.2 Flusso Standard
1.  **Creazione**: Utente A crea prenotazione.
    -   Stato: `NEGOTIATION`
    -   Pending: Gruppo B (Altro)
2.  **Approvazione**: Utente del Gruppo B approva.
    -   Stato: `APPROVED`
    -   Pending: Nessuno
3.  **Rifiuto (Negoziazione)**: Utente del Gruppo B rifiuta (con motivazione/proposta).
    -   Stato: `NEGOTIATION`
    -   Pending: Gruppo A (Owner) --> *Torna al mittente per modifica*
4.  **Modifica**: Utente A modifica le date (in risposta al rifiuto o spontaneamente).
    -   Stato: `NEGOTIATION`
    -   Pending: Gruppo B --> *Torna in approvazione*

### 3.3 Flusso Deroga (Revisione su Approvato)
Permette al Gruppo B di chiedere al Gruppo A di spostarsi, anche se A è già approvato.
1.  **Richiesta**: Utente B chiede modifica su prenotazione di A (Approvata).
    -   Stato: `DEROGA`
    -   Date: Salvate in `original_*`, nuove date proposte in `start/end`.
    -   Pending: Gruppo A (Owner)
2.  **Accettazione**: Utente A accetta lo spostamento.
    -   Stato: `APPROVED` (con le nuove date proposte).
    -   Campi deroga: puliti.
3.  **Rifiuto**: Utente A rifiuta lo spostamento.
    -   Stato: `APPROVED` (ripristino date originali da `original_*`).

## 4. Specifiche UI/UX

### 4.1 Calendario (`calendar.html`)
- **Libreria**: FullCalendar.
- **Visualizzazione**:
    -   Verde: Prenotazioni approvate Famiglia Andrea.
    -   Blu: Prenotazioni approvate Famiglia Fabrizio.
    -   Giallo: Le mie richieste in attesa.
    -   Arancione: Richieste altrui in attesa.
- **Interazioni**:
    -   Click su data vuota -> Popup Creazione.
    -   Drag & Drop -> Modifica date (se owner).

### 4.2 Dashboard (`dashboard.html`)
Strutturata in 3 colonne + Sezioni speciali:
1.  **Richieste di Deroga (in cima)**: Card rossa speciale per gestire le richieste di revisione ricevute.
2.  **Periodi Approvati (lista)**: Tabella di tutte le prenotazioni confermate.
    -   Azioni Owner: "Modifica" (riporta in negoziazione).
    -   Azioni Altri: "Richiedi Modifica" (avvia flusso Deroga).
3.  **Richiedono Attenzione (Colonna 1)**: Richieste dell'ALTRA famiglia che aspettano il TUO gruppo (Approve/Reject).
4.  **Le Tue Richieste (Colonna 2)**: Le tue prenotazioni in attesa (o che devi correggere dopo un rifiuto).
5.  **Storico (Colonna 3)**: Log delle ultime 10 azioni globali.

### 4.3 Finestre Modali (SweetAlert2)
Deve esserci validazione in tutti i form (Data Inizio < Data Fine).
- **Crea/Modifica**: Titolo, Start, End.
- **Rifiuta**: Motivo obbligatorio.
- **Richiedi Deroga**: Note, Nuova Data Inizio, Nuova Data Fine.

## 5. Requisiti Tecnici
- **Backend**: Django & Python.
- **Database**: SQLite (o PostgreSQL per prod).
- **Frontend**: HTML5, Bootstrap 5, HTMX (per interazioni dinamiche senza reload), SweetAlert2 (popup), FullCalendar.
- **Validazione**:
    -   Server-side: Controllo sovrapposizioni date.
    -   Client-side: Controllo coerenza date (start < end).

## 6. Sicurezza e Permessi
- **Login Required**: Tutto il sito è protetto.
- **Object Permissions**:
    -   Nessuno può modificare/cancellare prenotazioni altrui (tranne via flussi regolati come Reject o Request Deroga).
    -   View `update_booking_view` deve controllare rigorosamente `booking.user == request.user`.

---
Questo documento può essere consegnato a uno sviluppatore per ricostruire l'applicazione fedelmente mantenendo tutte le logiche di business attuali.
