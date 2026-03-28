# Agentic WebSphere to Open Liberty Migration Framework

An autonomous, multi-agent AI framework designed to migrate enterprise Java EE applications from legacy IBM WebSphere Application Server (WAS) to Open Liberty.

## Features
- **Intelligent Transformation:** Uses Anthropic Claude 3.5 Sonnet to rewrite legacy Java topologies (e.g., EJB 2.x to EJB 3/CDI), swapping `javax.ejb.Stateless` beans to `@Inject` mapping seamlessly.
- **Automated Declarative Config:** Generates deterministic `pom.xml` build configurations enforcing Java EE 8 boundaries and scaffolding `server.xml` for Open Liberty.
- **Human-In-The-Loop (HITL) Validation:** Integrates an orchestration layer that halts execution upon encountering migration discrepancies (utilizing OpenAI GPT-4 for static trace analysis).

## Prerequisites
- **Python 3.11+**
- **Maven** (required to build the migrated repositories)
- **API Keys:** You will need your own Anthropic and OpenAI API keys.

## API Key Setup (Important)

Your API keys **must never** be committed to version control. 

1. Create a `.env` file in the root directory:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and paste your actual keys:
   ```env
   # OpenAI API Key (Required for Validation Agent)
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
   
   # Anthropic API Key (Required for Transformation Agent)
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxx
   ```
*(Note: The `.env` file is heavily gitignored. It exists solely to inject keys securely at runtime.)*

## Quickstart

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the Backend Server
```bash
uvicorn backend.app.main:app --reload
```
The FastAPI backend will start on `http://127.0.0.1:8000`. The server creates a persistent local SQLite `data/migration_agent.db` upon initial execution. Do not delete this if you want to retain your migration metrics and job history.

### 3. Open the Dashboard
- Simply double-click `frontend/index.html` in your browser. (The UI is a self-contained vanilla Javascript and HTML panel powered by direct API calls to your local backend).
- Upload the `.zip` archive or the root folder of your legacy WebSphere project.
- Follow the visual flow to start the migration.
- When validation detects an error, the agent halts and requests a Human-In-The-Loop intervention. 

---

## Known Limitations & Active Issues

While this agent efficiently handles raw syntactical transformations and standard entity injections, it exhibits limits when dealing with deeply interconnected, monolithic system components. Specifically:

1. **Token Truncation Limits:**
   - Large monolith files (e.g., over 1,000 lines of complex legacy EJB orchestration) often exceed safe context generation windows. The LLM may unpredictably truncate its own response. Future architecture requires an integrated **Semantic Code Graph** (tracking AST boundaries) rather than pure text replacement.
2. **Contextual Configuration Disconnects (JMS/JNDI):**
   - The agent struggles to autonomously resolve bindings between `ibm-ejb-jar-bnd.xml` physical names and Open Liberty `server.xml` endpoints (such as `jmsTopic` or `ConnectionFactory` references). You may need to manually resolve unmapped JNDI resources in the generated Liberty config.
3. **Database & Lifecycle Bootstraps:**
   - Initialization servlets (e.g., table creation logic during `init()`) aren't safely sequenced. The agent doesn't guarantee `parentLast` EJB classloaders or database schema persistence boot configurations right out of the box.
