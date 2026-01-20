
import uuid
import os
from datetime import datetime
import shutil
import zipfile
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.config.settings import settings
from backend.app.workflow.orchestrator import WorkflowOrchestrator
from backend.app.agents.transformation import TransformationAgent
from backend.app.agents.validation import ValidationAgent

from backend.app.agents.validation import ValidationAgent

# Setup file logging
import logging
from pathlib import Path

LOG_DIR = Path("backend/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log"),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger(__name__)
logger.info("WebSphere Migration Agent starting...")

app = FastAPI(title="WAS to OSS Migration Agent", version="2.0")

# Ensure directories exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database storage (persistent)
from backend.app.database import db

# Models
class OrchestrationRequest(BaseModel):
    websphere_input: str
    liberty_output: Optional[str] = "migrated_open_liberty"
    max_iterations: int = 3
    
class TransformationRequest(BaseModel):
    source_files: Dict[str, str]
    target_platform: str = "open_liberty"
    llm_provider: str = "claude"

class ValidationRequest(BaseModel):
    project_path: str
    llm_provider: str = "claude"

class DecisionRequest(BaseModel):
    decision: str  # 'llm_fix', 'manual_fix', 'skip', 'abort'
    feedback: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    status: str

async def run_transformation_job(job_id: str, req: TransformationRequest):
    db.update_job(job_id, status='running', progress='Starting transformation...')
    
    agent = TransformationAgent(target_platform=req.target_platform)
    
    # Use the full migration method which handles file writing, POM generation, etc.
    try:
        results = agent.migrate_application(
            req.source_files, 
            llm_provider=req.llm_provider
        )
        
        db.update_job(job_id,
            status='completed',
            progress='Transformation complete',
            output_path=results.get('output_dir')
        )
        
    except Exception as e:
        db.update_job(job_id,
            status='failed',
            error=str(e)
        )


async def run_validation_job(job_id: str, req: ValidationRequest):
    db.update_job(job_id, status='running', progress='Starting validation...')
    
    agent = ValidationAgent(project_path=req.project_path)
    # The ValidationAgent currently only uses OpenAI for analysis in analyze_error
    
    res = agent.validate_project()
    
    db.update_job(job_id,
        status='completed' if res['overall'] == 'success' else 'failed',
        progress='Validation complete'
    )


# Endpoints

@app.get("/api/v1/jobs")
async def list_jobs():
    """List all jobs"""
    jobs = db.get_all_jobs(limit=50)
    return {"jobs": jobs}

@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/api/v1/transform", response_model=JobResponse)
async def start_transformation(req: TransformationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    db.create_job(job_id, 'transformation', {
        'target_platform': req.target_platform,
        'llm_provider': req.llm_provider
    })
    background_tasks.add_task(run_transformation_job, job_id, req)
    return JobResponse(job_id=job_id, status="started")

@app.post("/api/v1/validate", response_model=JobResponse)
async def start_validation(req: ValidationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    db.create_job(job_id, 'validation', {
        'project_path': req.project_path,
        'llm_provider': req.llm_provider
    })
    background_tasks.add_task(run_validation_job, job_id, req)
    return JobResponse(job_id=job_id, status="started")

@app.post("/api/v1/orchestrate", response_model=JobResponse)
async def start_orchestration(req: OrchestrationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    # Create job in database
    db.create_job(job_id, 'HITL Orchestration', {
        'websphere_input': req.websphere_input,
        'liberty_output': req.liberty_output,
        'max_iterations': req.max_iterations
    })
    
    # Initialize job with default values
    db.update_job(job_id,
        status='running',  # Set to running when starting workflow
        progress='Initializing migration workflow...',
        metrics={
            'files_discovered': 0,
            'files_transformed': 0,
            'total_tokens': 0,
            'total_cost': 0.0
        }
    )
    
    # Start Background Task
    orchestrator = WorkflowOrchestrator(req.websphere_input, req.max_iterations)
    background_tasks.add_task(orchestrator.run_workflow, job_id, db)
    
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

@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a source file (ZIP or Java)"""
    try:
        # Create unique ID for this upload
        upload_id = str(uuid.uuid4())
        upload_path = UPLOAD_DIR / upload_id
        upload_path.mkdir(exist_ok=True)
        
        file_path = upload_path / file.filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        final_path = str(file_path.absolute())
        
        # If ZIP, extract it
        if file.filename.endswith('.zip'):
            extract_dir = upload_path / "extracted"
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            final_path = str(extract_dir.absolute())
            
        return {
            "upload_id": upload_id,
            "filename": file.filename,
            "path": final_path,
            "message": "Upload successful"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/v1/jobs/{job_id}/decision")
async def submit_decision(job_id: str, req: DecisionRequest, background_tasks: BackgroundTasks):
    """HITL Decision endpoint - allows human to control workflow after failure"""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    decision = req.decision
    
    if decision == 'abort':
        db.update_job(job_id, status='cancelled', progress='Cancelled by user')
        return {"status": "cancelled", "message": "Job cancelled"}
    
    elif decision == 'skip':
        db.update_job(job_id, 
            status='completed',
            current_phase='output_ready',
            progress='Completed (validation skipped)'
        )
        return {"status": "completed", "message": "Validation skipped, output available"}
    
    elif decision == 'manual_fix':
        db.update_job(job_id,
            status='waiting_manual_fix',
            progress='Waiting for manual fixes...'
        )
        output_dir = job.get('output_path', 'output/migrated_open_liberty')
        return {
            "status": "waiting_manual_fix", 
            "message": "Waiting for manual fixes",
            "output_path": output_dir
        }
    
    elif decision == 'llm_fix':
        # Resume workflow with LLM retry
        db.update_job(job_id,
            status='running',
            progress='Retrying with LLM fix...'
        )
        
        # Get job config
        config = job.get('config', {})
        
        # Re-run orchestration workflow
        orchestrator = WorkflowOrchestrator(
            input_dir=config.get('websphere_input'),
            max_iterations=config.get('max_iterations', 3)
        )
        
        # Run workflow in background
        background_tasks.add_task(orchestrator.run_workflow, job_id, db)
        
        return {
            "status": "retrying",
            "message": "Workflow resuming with LLM fix"
        }
        raise HTTPException(status_code=400, detail="Invalid decision")


@app.get("/api/v1/system/logs")
async def get_system_logs(lines: int = 100):
    """Return recent backend logs for debugging and monitoring"""
    from pathlib import Path
    
    # Try multiple log locations
    log_paths = [
        Path("backend/logs/app.log"),
        Path("logs/app.log"),
        Path("app.log")
    ]
    
    log_file = None
    for path in log_paths:
        if path.exists():
            log_file = path
            break
    
    if not log_file:
        # Return helpful message if no log file exists
        return {
            "logs": [
                "[INFO] No log file found - application may be logging to console only",
                "[INFO] Check terminal/console output for system logs",
                "[INFO] Log file locations checked:",
                *[f"  - {path}" for path in log_paths]
            ],
            "total_lines": 0,
            "log_file": None
        }
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            # Get last N lines
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "logs": [line.rstrip('\n') for line in recent],
            "total_lines": len(all_lines),
            "log_file": str(log_file)
        }
    except Exception as e:
        return {
            "logs": [f"[ERROR] Failed to read log file: {str(e)}"],
            "total_lines": 0,
            "error": str(e)
        }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0"}

# Mount Frontend (Dashboard)
app.mount("/", StaticFiles(directory=str(settings.FRONTEND_DIR), html=True), name="frontend")

@app.get("/api/v1/jobs/{job_id}/download")
async def download_job_output(job_id: str):
    """Download the migration output as a ZIP file"""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    output_path = job.get('output_path')
    if not output_path or not os.path.exists(output_path):
         # Fallback check
         output_path = str(settings.OUTPUT_DIR / 'migrated_open_liberty')
         if not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="Output directory not found")

    try:
        # Create ZIP
        zip_base = settings.UPLOAD_DIR / f"migration_{job_id}"
        shutil.make_archive(str(zip_base), 'zip', output_path)
        zip_file = f"{zip_base}.zip"
        
        return FileResponse(
            zip_file, 
            media_type='application/zip', 
            filename=f"migration_result_{job_id}.zip"
        )
    except Exception as e:
        logger.error(f"Failed to zip output: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate download: {str(e)}")

@app.post("/api/v1/system/open_folder")
async def open_system_folder(req: dict):
    """Try to open the folder in system explorer (Dev mode only)"""
    path = req.get('path')
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    try:
        if os.name == 'nt': # Windows
            os.startfile(path)
        elif os.uname().sysname == 'Darwin': # macOS
            subprocess.run(['open', path])
        else: # Linux
            subprocess.run(['xdg-open', path])
        return {"status": "success"}
    except Exception as e:
        # Don't fail hard, just return info
        return {"status": "failed", "message": "Could not open folder (running in container?)"}
