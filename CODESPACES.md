# 🚀 Guida GitHub Codespaces

Questa guida spiega come utilizzare l'applicazione di migrazione contatti tramite GitHub Codespaces, senza dover installare nulla sul tuo computer.

## 📋 Prerequisiti

1. **Account GitHub** (gratuito)
2. **Token Notion** e ID dei database (vedi sezione Configurazione)

## 🎯 Avvio Rapido (2 minuti)

### 1️⃣ Creare il Codespace

1. Vai su https://github.com/albertocabasvidani/migrazione-partechipazione
2. Clicca sul bottone verde **`Code`**
3. Seleziona la tab **`Codespaces`**
4. Clicca **`Create codespace on master`**

> ⏱️ Il Codespace si avvierà in circa 30-60 secondi

### 2️⃣ Configurare le Credenziali Notion

Una volta aperto il Codespace (VS Code nel browser):

1. **Copia il file di esempio:**
   ```bash
   cp .env.example .env
   ```

2. **Apri il file `.env`** nel editor (clicca su di esso nel pannello file)

3. **Inserisci le tue credenziali:**
   ```
   NOTION_TOKEN=secret_xxxxxxxxxxxxx
   CONTATTI_DB_ID=xxxxxxxxxx
   COMUNI_DB_ID=xxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxx (opzionale)
   ```

### 3️⃣ Avviare il Server

Nel terminale del Codespace, esegui:

```bash
python3 server.py
```

Vedrai:
```
🚀 CSV Import Server - VERSIONE FINALE
📍 URL: http://localhost:8000
```

### 4️⃣ Aprire l'Applicazione

1. Apparirà una notifica popup: **"Your application running on port 8000 is available"**
2. Clicca **"Open in Browser"**
3. Si aprirà l'interfaccia web dell'applicazione

> 💡 **Alternativa:** Vai alla tab `PORTS` in basso, trova la porta 8000 e clicca sull'icona del globo

## 🔧 Configurazione Notion

### Ottenere il Token Notion

1. Vai su https://www.notion.so/my-integrations
2. Clicca **"New integration"**
3. Dai un nome (es. "Importatore CSV")
4. Seleziona il workspace
5. Copia il **"Internal Integration Token"** che inizia con `secret_`

### Ottenere gli ID dei Database

1. Apri il database Notion nel browser
2. L'URL sarà tipo: `https://www.notion.so/workspace/xxxxxxxxxxxxx?v=yyy`
3. Copia la parte `xxxxxxxxxxxxx` (32 caratteri)

### Condividere i Database con l'Integration

1. Apri ogni database in Notion
2. Clicca sui **tre puntini** in alto a destra
3. Vai su **"Connections"**
4. Cerca e aggiungi la tua integration

## 📝 Utilizzo dell'Applicazione

1. **Carica un file CSV** usando il pulsante nell'interfaccia
2. **Verifica il mapping** dei campi
3. **Clicca "Importa"** per trasferire i dati in Notion

## 🔄 Riavviare il Codespace (Sessioni Successive)

I Codespaces si fermano dopo 30 minuti di inattività. Per riavviare:

1. Vai su https://github.com/codespaces
2. Trova il tuo Codespace nella lista
3. Clicca sui **tre puntini** → **"Open in browser"**
4. Nel terminale: `python3 server.py`

## ⚡ Comandi Utili

| Comando | Descrizione |
|---------|-------------|
| `python3 server.py` | Avvia il server |
| `Ctrl+C` | Ferma il server |
| `cat .env` | Visualizza configurazione |
| `ls CSV_Export/` | Vedi file CSV disponibili |

## 🆘 Troubleshooting

### "NOTION_TOKEN non configurato!"
- Assicurati di aver creato e compilato il file `.env`
- Verifica che il token inizi con `secret_`

### "Porta 8000 già in uso"
- Ferma il server precedente con `Ctrl+C`
- O modifica la porta nel file `server.py`

### L'app non si apre
1. Vai alla tab **PORTS**
2. Verifica che la porta 8000 sia listata
3. Clicca sull'icona del globo per aprire

### Codespace lento o non risponde
- I Codespaces gratuiti hanno risorse limitate
- Prova a riavviare: Menu → "Codespaces: Rebuild Container"

## 💰 Costi e Limiti

- **GitHub Free:** 60 ore/mese di Codespaces gratuiti
- **Timeout:** Il Codespace si ferma dopo 30 minuti di inattività
- **Storage:** 15 GB inclusi

## 🏃 Esecuzione Locale (Alternativa)

Se preferisci eseguire localmente:

```bash
# Clona il repository
git clone https://github.com/albertocabasvidani/migrazione-partechipazione.git
cd migrazione-partechipazione

# Configura le variabili
cp .env.example .env
# Modifica .env con un editor

# Avvia il server
python3 server.py
```

Poi apri http://localhost:8000 nel browser.

## 📚 Risorse

- [Documentazione GitHub Codespaces](https://docs.github.com/en/codespaces)
- [Notion API](https://developers.notion.com/)
- [Repository del progetto](https://github.com/albertocabasvidani/migrazione-partechipazione)