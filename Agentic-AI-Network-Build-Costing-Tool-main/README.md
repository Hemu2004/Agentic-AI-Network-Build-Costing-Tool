# FTTP Network Cost Estimation & Optimization

Production-ready **Agentic AI** web application for FTTP (Fiber-to-the-Premises) network cost estimation, budget-based planning, upgrade planning, and map-based planning.

## Tech Stack

- **Frontend:** HTML, CSS, JavaScript (dashboard UI with Chart.js, Leaflet)
- **Backend:** Python, FastAPI
- **Database:** MongoDB
- **LLM:** Ollama (local)
- **Agents:** LangGraph + CrewAI-style agents (validation, cost, optimization, explanation)

## Project Structure

```
V1/
├── config/           # Settings (MongoDB, Ollama)
├── db/               # MongoDB connection & models
├── agents/           # FTTP engine, Ollama client, crew (estimation/budget/upgrade/maps)
├── graph/            # LangGraph flows (estimation → visualization)
├── api/               # FastAPI routes & schemas
├── static/            # Frontend (index.html, css, js)
├── main.py            # FastAPI app
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

1. **Python 3.10+**
2. **MongoDB** running (e.g. `mongod` on port 27017)
3. **Ollama** (optional, for AI-generated explanations):
   - **Without Ollama:** The app works fully: all cost, quantities, ROI, and optimization suggestions use rule-based logic. Only the narrative explanations use fallback text.
   - **With Ollama:** Install from [ollama.ai](https://ollama.ai), start `ollama serve`, then `ollama pull llama3.2`. The UI shows "Ollama: Online" when connected; explanations and Maps inference will use the LLM.

## Setup

1. **Clone / open project**
   ```bash
   cd c:\Users\sumiy\OneDrive\Desktop\V1
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment (optional)**
   - Copy `.env.example` to `.env` and set `MONGODB_URI`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` if needed.
   - Defaults: MongoDB `localhost:27017`, Ollama `http://localhost:11434`, model `llama3.2`.

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

- **API:** http://localhost:8000  
- **App UI:** http://localhost:8000/static/index.html  
- **API docs:** http://localhost:8000/docs  

## Application Layout

- **Left sidebar (fixed):**
  1. **AI Estimator** – Cost Estimation, Budget-Based Planning, Upgrade Planner
  2. **Maps Planner** – Location-based estimation with interactive map
  3. **Projects / History** – Saved estimations (MongoDB)

- **Middle panel:** Dynamic content per section.

## Features

### 1. AI Estimator

- **Cost Estimation:** Area name/code, area type, premises, distance, architecture (PON/P2P/PCP). Output: total cost, breakdown, ROI, payback, quantities, LLM explanation, deployment strategy, optimization suggestions, chart.
- **Budget-Based Planning:** Budget, area type, distance. Output: feasible premises, cost, ROI, payback, trade-offs, deployment plan.
- **Upgrade Planner:** Existing type, current/target capacity. Output: upgrade cost, hardware changes, ROI impact.

### 2. Maps Planner

- Inputs: target location, region, premises, distance, area type, architecture.
- Central interactive map (Leaflet) with Central Office marker.
- Output: cost, error margin, LLM explanation, quantities, deployment, ROI, payback, chart.

### 3. Projects / History

- List all saved estimations.
- View detailed result.
- Delete project.
- Data stored in MongoDB.

## Agent Architecture

- **Input Validation Agent** – Normalizes and validates inputs.
- **Cost Estimation Agent** – Deterministic quantities & cost (fiber, splitters, OLTs, ONTs, cabinets, civil, labor, ops).
- **ROI & Finance Agent** – ROI and payback period.
- **Optimization Agent** – LLM-generated cost optimization suggestions.
- **Explanation Agent** – Human-readable LLM explanation and deployment strategy.

**LangGraph flow:** Input → Estimation → Optimization → Visualization → (Storage on Save).

## MongoDB Schema

- **Collection:** `projects`
- **Fields:** `user_id`, `type`, `title`, `inputs`, `result` (total_cost, cost_breakdown, quantities, roi, payback_period_months, llm_explanation, deployment_strategy, optimization_suggestions, charts_data), `created_at`.

## Example Ollama Model

Use any model that supports ~2k tokens; recommended:

```bash
ollama pull llama3.2
```

Set in `.env`:

```
OLLAMA_MODEL=llama3.2
```

## Sample API Response (Cost Estimation)

See `sample_outputs/cost_estimation_response.json` for an example JSON response.

## License

MIT.
