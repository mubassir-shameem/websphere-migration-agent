
@app.post("/api/v1/jobs/{job_id}/decision")
async def submit_decision(job_id: str, req: DecisionRequest, background_tasks: BackgroundTasks):
    """HITL Decision endpoint - allows human to control workflow after failure"""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    decision = req.decision
    feedback = req.feedback
    
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
            "message": f"Please fix files in: {output_dir}",
            "output_dir": output_dir
        }
    
    elif decision == 'llm_fix':
        # Resume workflow with LLM fix attempt
        db.update_job(job_id,
            status='running',
            progress='Retrying with LLM feedback...'
        )
        # TODO: Implement LLM retry logic
        return {"status": "retrying", "message": "LLM fix initiated"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")
