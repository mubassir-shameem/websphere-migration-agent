# Architecture Diagram

```mermaid
graph TD
    subgraph Frontend [Single Page Application]
        UI[Dashboard HTML/JS]
        Status[Job Monitor]
        Logs[Log Streamer]
    end

    subgraph Backend [FastAPI Server]
        API[API Endpoints]
        Orch[Workbook Orchestrator]
        Repo[Job/State Store]
    end

    subgraph Agents [AI Agents]
        TA[Transformation Agent]
        VA[Validation Agent]
        LLM[LLM Client (Claude/GPT)]
    end

    subgraph Infrastructure
        FS[File System]
        Maven[Maven Build]
    end

    %% Flows
    UI -->|Upload Zip| API
    UI -->|Start Job| API
    API -->|Async Task| Orch
    
    Orch -->|1. Transform| TA
    TA -->|Prompt| LLM
    TA -->|Write Code| FS
    
    Orch -->|2. Validate| VA
    VA -->|Run Build| Maven
    Maven -->|Result| VA
    
    Orch -->|Update State| Repo
    UI -->|Poll Status| API
    Logs -->|Poll Logs| API
```
