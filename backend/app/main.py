
import uuid
import os
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.config.settings import settings
from backend.app.workflow.orchestrator import WorkflowOrchestrator
from backend.app.agents.transformation import TransformationAgent
from backend.app.agents.validation import ValidationAgent

app = FastAPI(title="WAS to OSS Migration Agent", version="2.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (Prototype style)
jobs = {}
orchestration_states = {}

# Models
class OrchestrationRequest(BaseModel):
    input_path: str
    max_iterations: int = 3
    
class TransformationRequest(BaseModel):
    source_files: Dict[str, str]
    target_platform: str = "open_liberty"
    llm_provider: str = "claude"

class ValidationRequest(BaseModel):
    project_path: str
    llm_provider: str = "claude"

class JobResponse(BaseModel):
    job_id: str
    status: str

async def run_transformation_job(job_id: str, req: TransformationRequest):
    jobs[job_id]['status'] = 'running'
    jobs[job_id]['progress'] = 'Starting transformation...'
    
    agent = TransformationAgent(target_platform=req.target_platform)
    
    # Use the full migration method which handles file writing, POM generation, etc.
    try:
        results = agent.migrate_application(
            req.source_files, 
            llm_provider=req.llm_provider
        )
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['progress'] = 'Transformation complete'
        jobs[job_id]['target_platform'] = results.get('target_platform')
        jobs[job_id]['output_directory'] = results.get('output_dir')
        jobs[job_id]['files_transformed'] = results.get('files_transformed', {})
        jobs[job_id]['new_files'] = results.get('new_files', [])
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)


async def run_validation_job(job_id: str, req: ValidationRequest):
    jobs[job_id]['status'] = 'running'
    jobs[job_id]['progress'] = 'Starting validation...'
    
    agent = ValidationAgent(project_path=req.project_path)
    # Ensure validation uses the requested LLM if agent supports it (currently uses settings env var, but logic could be passed)
    # The ValidationAgent currently only uses OpenAI for analysis in analyze_error
    
    res = agent.validate_project()
    
    jobs[job_id]['status'] = 'completed' if res['overall'] == 'success' else 'failed'
    jobs[job_id]['progress'] = 'Validation complete'
    jobs[job_id]['validation_results'] = res.get('tests', {})
    jobs[job_id]['issues'] = res.get('issues', [])


# Endpoints

@app.get("/api/v1/jobs")
async def list_jobs():
    """List all jobs"""
    return {"jobs": jobs}

@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.post("/api/v1/transform", response_model=JobResponse)
async def start_transformation(req: TransformationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'starting',
        'type': 'transformation',
        'created_at': datetime.now().isoformat()
    }
    background_tasks.add_task(run_transformation_job, job_id, req)
    return JobResponse(job_id=job_id, status="started")

@app.post("/api/v1/validate", response_model=JobResponse)
async def start_validation(req: ValidationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'starting',
        'type': 'validation',
        'created_at': datetime.now().isoformat()
    }
    background_tasks.add_task(run_validation_job, job_id, req)
    return JobResponse(job_id=job_id, status="started")

@app.post("/api/v1/orchestrate", response_model=JobResponse)
async def start_orchestration(req: OrchestrationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    # Init storage
    jobs[job_id] = {
        'status': 'starting', 
        'type': 'orchestration',
        'progress': 'Initializing...',
        'created_at': datetime.now().isoformat()
    }
    orchestration_states[job_id] = {
        'transformation_history': [],
        'validation_history': []
    }
    
    # Start Background Task
    orchestrator = WorkflowOrchestrator(req.input_path, req.max_iterations)
    background_tasks.add_task(orchestrator.run_workflow, job_id, jobs, orchestration_states)
    
    return JobResponse(job_id=job_id, status="started")

@app.get("/api/v1/orchestrate/{job_id}/status")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": job_id,
        "status": jobs[job_id].get("status"),
        "progress": jobs[job_id].get("progress"),
        "state": orchestration_states.get(job_id, {})
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0"}

# Mount Frontend (Dashboard)
app.mount("/", StaticFiles(directory=str(settings.FRONTEND_DIR), html=True), name="frontend")
