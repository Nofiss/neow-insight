# Progetto: Neow’s Insight

## 1. Architettura del Sistema

Il sistema è diviso in tre componenti principali:

1. **Core (Python):** Un servizio in background che monitora i file `.run`, esegue il parsing del JSON e gestisce il database.
2. **API (FastAPI):** Espone i dati estratti e i suggerimenti statistici al frontend.
3. **Dashboard (TypeScript/React):** Interfaccia web per visualizzare statistiche live e raccomandazioni durante la partita.

---

## 2. Tech Stack

### Backend (Python)

* **Gestore Pacchetti:** `uv` (moderno, ultra-veloce, sostituto di pip/poetry).
* **Framework API:** `FastAPI`.
* **Monitoraggio File:** `watchdog`.
* **Database ORM:** `SQLModel` (unisce SQLAlchemy e Pydantic).
* **Database:** `SQLite` (locale, leggero, nessuna configurazione).

### Frontend (TypeScript)

* **Build Tool:** `Vite`.
* **Framework UI:** `React`.
* **Styling:** `Tailwind CSS`.
* **UI Components:** `Shadcn`
* **State Management:** `TanStack Query` (per fetch dati real-time).

---

## 3. Setup del Progetto (Backend con `uv`)

Assicurati di avere `uv` installato (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

```bash
# Inizializzazione progetto
mkdir neow-insight && cd neow-insight
uv init

# Installazione dipendenze core
uv add fastapi uvicorn watchdog sqlmodel pydantic
```

---

## 4. Struttura del Database (Schema)

Il database mapperà la struttura del file `.run`:

* **Run:** `id`, `seed`, `character`, `ascension`, `win` (bool).
* **CardChoice:** `id`, `run_id`, `floor`, `offered_cards` (JSON), `picked_card` (string), `is_shop` (bool).
* **RelicHistory:** `id`, `run_id`, `relic_id`, `floor`.

---

## 5. Implementazione Core (Logic)

### A. Monitoraggio File (`watcher.py`)

Il watcher deve rilevare modifiche nella cartella dei salvataggi (solitamente in `Steam/steamapps/common/SlayTheSpire2/runs`).

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json

class RunFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".run"):
            self.process_run(event.src_path)

    def process_run(self, path):
        with open(path, 'r') as f:
            data = json.load(f)
            # Logica per estrarre l'ultimo piano e salvarlo nel DB
            print(f"Aggiornamento rilevato: Piano {len(data['map_point_history'])}")
```

### B. API Service (`main.py`)

Espone le raccomandazioni basate sui dati storici.

```python
from fastapi import FastAPI
from sqlmodel import Session, select

app = FastAPI()

@app.get("/recommendation")
def get_recommendation(current_cards_offered: list[str]):
    # Esempio di logica: conta quante volte le carte offerte
    # sono apparse in run vincenti nel passato
    return {"best_pick": "CARD.DEFILE", "win_rate_boost": "+15%"}
```

---

## 6. Frontend (TypeScript/Vite)

Setup rapido della dashboard:

```bash
pnpm create vite@latest frontend -- --template react-ts
cd frontend
pnpm install
pnpm install -D tailwindcss @tailwindcss/vite
```

### Componente Raccomandazione (Esempio)

```typescript
interface Recommendation {
  best_pick: string;
  win_rate_boost: string;
}

export function SuggestionBox({ offered }: { offered: string[] }) {
  // Fetch dai dati dal backend FastAPI
  const { data } = useQuery(['recommendation', offered], () =>
    fetch(`/api/recommendation?cards=${offered.join(',')}`).then(res => res.json())
  );

  return (
    <div className="p-4 bg-slate-800 text-white rounded-lg shadow-xl">
      <h2 className="text-xl font-bold">Suggerimento IA</h2>
      <p className="text-green-400">Scegli: {data?.best_pick}</p>
      <span className="text-sm opacity-50">Win rate storica: {data?.win_rate_boost}</span>
    </div>
  );
}
```

---

## 7. Roadmap di Sviluppo

1. **Fase 1 (Data Ingestion):** Script Python che legge i file `.run` esistenti e popola il database per avere uno storico.
2. **Fase 2 (Real-time Watcher):** Implementazione di `watchdog` per aggiornare il DB mentre giochi.
3. **Fase 3 (Analytics):** Creazione di query SQL per calcolare la forza delle carte (es. *Win-rate di una carta quando presa nell'Atto 1 vs Atto 2*).
4. **Fase 4 (Interfaccia):** Dashboard web da tenere sul secondo monitor.
5. **Fase 5 (IA Avanzata):** Integrazione di un LLM (via OpenAI API o locale con Ollama) a cui passare l'intero JSON della run attuale per ricevere consigli strategici complessi (es. *"Hai poche difese, ignora l'attacco e prendi 'Onda di Ferro'"*).

---

## 8. Note sui Percorsi dei File

* **Windows:** `%AppData%\SlayTheSpire2\steam\76561198110552884\profile1\saves\history`.
* **Linux/Steam Deck:** `~/.steam/steam/steamapps/compatdata/...` (da verificare al rilascio ufficiale).

Questa documentazione fornisce una base solida. Usando `uv` e `FastAPI`, avrai un backend estremamente leggero che non impatterà sulle prestazioni del gioco mentre è in esecuzione.

---

## 9. Comandi Operativi Rapidi

Dal root del repository:

```bash
# Inizializza settings.toml locale da template
python scripts/init_settings.py

# Ripristina settings.toml dal template (crea backup automatico)
python scripts/reset_settings.py

# Ripristina senza creare backup
python scripts/reset_settings.py --no-backup

# Ripristina con nome backup personalizzato
python scripts/reset_settings.py --backup-name settings.toml.backup-manuale

# Nota: --backup-name accetta solo un filename semplice nel root repository

# Avvio sviluppo full-stack (backend + frontend)
python scripts/dev.py

# Smoke test end-to-end API (avvio backend temporaneo + check endpoint)
python scripts/e2e.py

# Verifica completa (backend lint+test, frontend lint+build)
python scripts/verify.py
```

### Note pratiche

* Il backend espone API su `http://127.0.0.1:8000` (dev normale).
* Il frontend Vite gira su `http://127.0.0.1:5173`.
* Lo smoke E2E usa una porta separata (`8010`) per non interferire con sessioni locali già aperte.

### Configurazione senza variabili d'ambiente

Configura il progetto creando `settings.toml` nel root repository (puoi partire da `settings.toml.example` o usare `python scripts/init_settings.py`):

```toml
[api]
host = "127.0.0.1"
port = 8000
log_level = "INFO"

[storage]
db_path = "data/neow_insight.db"
run_history_path = "C:/Users/<utente>/AppData/Roaming/SlayTheSpire2/steam/76561198110552884/profile1/saves/history"

[watcher]
enabled = true
debounce_seconds = 0.4
```

Con questa configurazione, avvia normalmente:

```bash
uv run api-dev
```

Endpoint utili:

- `GET /health` (include `watcher_enabled`)
- `GET /ingest/status` (stato ultimo import live)

### Codici di uscita script settings

Per `python scripts/reset_settings.py`:

- `0`: esecuzione completata con successo.
- `1`: errore operativo (es. `settings.toml.example` mancante).
- `2`: input non valido per `--backup-name`.
