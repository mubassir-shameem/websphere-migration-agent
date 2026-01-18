# WAS to OSS Migration Agent - User Guide

## Overview
The **WAS2OSS Agent** is an automated migration assistant that converts legacy **IBM WebSphere Traditional** applications (Java EE) to modern **Open Liberty** applications (Jakarta EE/MicroProfile).

It uses **Generative AI (Claude/OpenAI)** to intelligently transform source code, rewrite configurations (`web.xml` -> `server.xml`), and validate the results using **Maven**.

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Docker** (Optional, for containerized run)
- **API Key**: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (in `.env`)

### 2. Setup (Local)
```bash
# 1. Clone & Setup
cp .env.example .env
# Edit .env and add your API Key

# 2. Run the Agent
./scripts/start.sh
```
*The agent will start on port **8000**.*

## 🖥️ Using the Dashboard
Open your browser to `http://localhost:8000`.

### Step 1: Upload Application
You have two options:
1.  **Drag & Drop**: Drag a ZIP file of your legacy source code (e.g., `App.zip`) onto the drop zone.
2.  **Server Path**: If the code is already on the server, type the absolute path.

> **Tip**: For a quick test, use the included sample:
> `backend/sample_legacy/sample_minimal.zip`

### Step 2: Start Migration
1.  Review your input.
2.  Click **Start Migration Pipeline**.
3.  The request is sent to the Orchestrator.

### Step 3: Monitor Progress
- **Job Monitor**: A card will appear showing the status (e.g., "Iteration 1: Transforming...").
- **System Logs Tab**: Switch to this tab (bottom panel) to see real-time detailed logs of what the AI is doing.

### Step 4: Download Results
When the job completes (Status: `completed`):
- A **"📥 Download Result"** button will appear in the Job Monitor card.
- Click it to download a ZIP containing the fully migrated Open Liberty application (`server.xml`, `pom.xml`, source code).

## 💰 Cost & Optimization
- **Default Behavior**: The agent runs **1 Pass** (Iteration) to keep costs low (~$3-4 for a medium app).
- **Auto-Repair**: In future versions, you can enable multi-pass to fix compilation errors automatically (costs more).

## ❓ Troubleshooting

### "API call failed" or Dashboard Stuck?
- Check the **System Logs** tab.
- If the server seems unresponsive, check your terminal. Ensure `uvicorn` is running.
- If you see "Blocking" warnings, don't worry—the backend now runs heavy tasks in a background threadpool to keep the UI valid.

### "Validation Failed"?
- Check the `target/migrated_open_liberty/logs` or the System Logs.
- Common issues: Missing dependencies in `pom.xml` (the AI tries to guess them, but sometimes fails).
