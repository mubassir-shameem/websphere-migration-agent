
import os
import asyncio
from datetime import datetime
from backend.app.agents.transformation import TransformationAgent
from backend.app.agents.validation import ValidationAgent
from backend.config.settings import settings

class WorkflowOrchestrator:
    def __init__(self, input_path, max_iterations=3):
        self.input_path = input_path
        self.max_iterations = max_iterations
        
    def _discover_files(self):
        """Discover Java and XML files in input path"""
        files = {}
        # Simple recursive walk
        try:
             for root, _, filenames in os.walk(self.input_path):
                 for f in filenames:
                     if f.endswith('.java') or f.endswith('.xml'):
                         full_path = os.path.join(root, f)
                         files[f] = full_path
        except Exception as e:
            print(f"Error checking input path: {e}")
            
        return files

    async def run_workflow(self, job_id, jobs_store, state_store):
        """Execute the migration loop"""
        
        # Initialize
        state_store[job_id]['current_iteration'] = 0
        trans_agent = TransformationAgent()
        val_agent = ValidationAgent()
        
        files = self._discover_files()
        if not files:
            jobs_store[job_id]['status'] = 'failed'
            jobs_store[job_id]['error'] = 'No source files found'
            return

        feedback = None
        
        for i in range(1, self.max_iterations + 1):
            state_store[job_id]['current_iteration'] = i
            jobs_store[job_id]['progress'] = f"Iteration {i}: Transforming..."
            
            # 1. Transform
            trans_res = trans_agent.migrate_application(
                files, 
                llm_provider=settings.DEFAULT_LLM_PROVIDER,
                validation_feedback=feedback
            )
            
            state_store[job_id]['transformation_history'].append({
                'iteration': i,
                'result': trans_res
            })
            
            # 2. Validate
            jobs_store[job_id]['progress'] = f"Iteration {i}: Validating..."
            val_res = val_agent.validate_project() # defaulting to configured output dir
            
            state_store[job_id]['validation_history'].append({
                'iteration': i,
                'result': val_res
            })
            
            if val_res['overall'] == 'success':
                 jobs_store[job_id]['status'] = 'completed'
                 jobs_store[job_id]['result'] = 'Migration Successful'
                 return
                 
            # 3. Handle Failure -> Loop or Human Input
            feedback = val_res # Pass full validation result as feedback
            
            # Simple HITL Simulation: Stop if we want human check, 
            # In this automated flow we might just loop, but let's update state for UI
            state_store[job_id]['validation_results'] = val_res
            
            # If we want to simulate "WAITING FOR HUMAN" we would return here
            # But for now, let's auto-retry unless it's the last iteration
            if i < self.max_iterations:
                 jobs_store[job_id]['progress'] = f"Iteration {i}: Failed. Retrying with feedback..."
            else:
                 jobs_store[job_id]['status'] = 'failed'
                 jobs_store[job_id]['progress'] = 'Max iterations reached without success.'
                 
