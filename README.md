# CSV Import Tool for Notion

Strumento per l'importazione massiva di contatti CSV in un database Notion, con correzione automatica dei nomi dei comuni tramite AI.

## 🚀 Avvio Rapido

### Opzione 1: GitHub Codespaces (Consigliato)
**[📖 Guida completa Codespaces](./CODESPACES.md)** - Usa l'app direttamente nel browser senza installare nulla

### Opzione 2: Esecuzione Locale
Segui le istruzioni di installazione qui sotto

## Funzionalità

- 📊 Importazione CSV con mapping personalizzato dei campi
- 🤖 Correzione automatica dei nomi comuni tramite OpenAI
- 🌐 Interface web per upload e configurazione
- 📧 Estrazione intelligente del comune dall'email
- 🔒 Gestione sicura delle credenziali
- 📝 Report dettagliato dell'importazione

## Requisiti

- Python 3.6+
- Account Notion con accesso API
- Token Notion API
- Account OpenAI (opzionale)

## Installazione

1. Clona il repository:
```bash
git clone <url-repository>
cd migrazione-partechipazione
```

2. Configura le variabili di ambiente:
```bash
cp .env.example .env
```

3. Modifica `.env` con i tuoi valori:
```bash
NOTION_TOKEN=your_notion_token_here
CONTATTI_DB_ID=your_contatti_database_id_here
COMUNI_DB_ID=your_comuni_database_id_here
OPENAI_API_KEY=your_openai_api_key_here  # Opzionale
```

## Utilizzo

1. Avvia il server:
```bash
python server.py
```

2. Apri il browser all'indirizzo:
```
http://localhost:8000
```

3. Carica il file CSV e configura il mapping dei campi

4. Avvia l'importazione e monitora i risultati

## Struttura Database Notion

### Database Contatti
Campi richiesti:
- `Email primaria` (Title)
- `Nome e cognome` (Rich Text)
- `Carica` (Rich Text)
- `Comune` (Relation al database Comuni)
- `Status` (Select)

### Database Comuni
Campi richiesti:
- `Name` (Title)

## Funzionalità Avanzate

### Correzione Automatica Comuni
Il sistema può correggere automaticamente i nomi dei comuni usando:
- Estrazione dall'email istituzionale
- Correzione tramite OpenAI GPT-4
- Cache per ottimizzare le performance

### Formato CSV Supportato
- Separatore: virgola (,)
- Encoding: UTF-8, Latin-1, ISO-8859-1, CP1252
- Prima riga deve contenere i nomi delle colonne

## Troubleshooting

### Errori Comuni

**"NOTION_TOKEN non configurato"**
- Verifica che il file `.env` esista e contenga il token

**"Comune non trovato"**
- Verifica che il database Comuni sia popolato
- Configura la chiave OpenAI per la correzione automatica

**"Errore di encoding"**
- Salva il CSV in formato UTF-8
- Verifica che non ci siano caratteri speciali problematici

## Licenza

Questo progetto è rilasciato sotto licenza MIT.