
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

    async def run_workflow(self, job_id, db):
        """Execute the migration loop"""
        
        # Initialize
        trans_agent = TransformationAgent()
        val_agent = ValidationAgent()
        
        files = self._discover_files()
        if not files:
            db.update_job(job_id, status='failed', error='No source files found')
            return

        # Add discovery event
        db.add_job_event(job_id, 'discovery', {
            'file_count': len(files),
            'files': list(files.keys())
        })

        feedback = None
        
        for i in range(1, self.max_iterations + 1):
            db.update_job(job_id, 
                progress=f"Iteration {i}: Transforming...",
                current_phase='transforming'
            )
            db.add_job_event(job_id, 'iteration_start', {
                'iteration': i, 
                'total_files': len(files)
            })
            
            # 1. Transform
            trans_res = trans_agent.migrate_application(
                files, 
                llm_provider=settings.DEFAULT_LLM_PROVIDER,
                validation_feedback=feedback
            )
            
            db.add_job_history(job_id, i, 'transformation', trans_res)
            db.add_job_event(job_id, 'transformation_done', {
                'iteration': i,
                'files_transformed': trans_res.get('files_transformed', 0)
            })
            
            # 2. Validate
            db.update_job(job_id, 
                progress=f"Iteration {i}: Validating...",
                current_phase='validating'
            )
            db.add_job_event(job_id, 'validation_start', {'iteration': i})
            
            val_res = val_agent.validate_project(trans_agent.output_dir)
            
            db.add_job_history(job_id, i, 'validation', val_res)
            
            validation_success = val_res.get('overall') == 'success'
            db.add_job_event(job_id, 'validation_done', {
                'success': validation_success,
                'overall': val_res.get('overall'),
                'log_snippet': str(val_res.get('output', ''))[:500]
            })
            
            if val_res['overall'] == 'success':
                 db.update_job(job_id,
                     status='completed',
                     current_phase='output_ready',
                     progress='Migration Successful',
                     output_path=trans_agent.output_dir
                 )
                 return
                 
            # 3. Handle Failure -> HITL: Pause for human decision
            feedback = val_res
            
            # HITL: Pause and wait for human decision after EVERY failure
            db.update_job(job_id,
                status='waiting_for_human',
                progress=f"Iteration {i}: Validation failed. Awaiting human decision...",
                error="Validation failed. Choose: LLM Fix, Manual Fix, Skip, or Cancel.",
                output_path=trans_agent.output_dir
            )
            
            # Exit the loop - human decision will determine next action
            return
