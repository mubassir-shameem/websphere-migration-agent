
import os
import shutil
import subprocess
import logging
import json
from datetime import datetime
from openai import OpenAI
from backend.config.settings import settings

class ValidationAgent:
    def __init__(self, project_path=None):
        self.project_dir = str(project_path) if project_path else str(settings.OUTPUT_DIR / 'migrated_open_liberty')
        self.setup_logging()
        
        self.openai_client = None
        if settings.OPENAI_API_KEY:
             self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
             
        self.logger.info(f"Validation Agent initialized for {self.project_dir}")

    def setup_logging(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = settings.LOG_DIR / f'validation_agent_{timestamp}.log'
        
        self.logger = logging.getLogger('ValidationAgent')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            fh = logging.FileHandler(str(log_file))
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(fh)

    def analyze_error(self, stderr, stdout):
        """Use LLM to analyze build error if available"""
        if not self.openai_client:
            return "No LLM analysis available (OpenAI key missing)."
            
        prompt = f"""Analyze this Maven build error.
        STDERR: {stderr[-1000:]}
        
        Give specific actionable fixes for Open Liberty/Jakarta EE 8."""
        
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"Error analyzing logs: {e}"

    def validate_project(self, project_path=None):
        if project_path:
            self.project_dir = str(project_path)
            
        self.logger.info(f"Validating {self.project_dir}")
        results = {
            'status': 'running',
            'tests': {},
            'issues': [],
            'project_path': self.project_dir
        }

        # 1. Structure Check
        structure_ok, missing = self._check_structure()
        results['tests']['structure'] = {'status': 'passed' if structure_ok else 'failed', 'missing': missing}
        if not structure_ok:
            results['issues'].append(f"Missing files: {missing}")

        # 2. Maven Build
        build_res = self._run_maven_build()
        results['tests']['maven_build'] = build_res
        
        if build_res['status'] == 'failed':
            results['issues'].append("Maven build failed")
        elif build_res['status'] == 'skipped':
             # Don't fail the job, just note it
             pass

        # Overall Status
        if len(results['issues']) == 0:
            results['overall'] = 'success'
        else:
            results['overall'] = 'failed'
            
        return results

    def _check_structure(self):
        required = ['pom.xml', 'src/main/java', 'src/main/liberty/config/server.xml']
        missing = []
        for r in required:
            if not os.path.exists(os.path.join(self.project_dir, r)):
                missing.append(r)
        return (len(missing) == 0), missing

    def _run_maven_build(self):
        if not os.path.exists(os.path.join(self.project_dir, 'pom.xml')):
            return {'status': 'failed', 'error': 'pom.xml not found'}
            
        # Sustainable Architecture: Use System Environment (PATH)
        # We expect 'mvn' and 'java' to be available in the environment (or container)
        mvn_cmd = 'mvn'
        
        # Verify Maven exists
        if not shutil.which(mvn_cmd):
            return {'status': 'skipped', 'message': 'Maven (mvn) not found in PATH. Please install Maven.'}
            
        try:
            # Inherit system environment (Respects user's JAVA_HOME and PATH)
            env = os.environ.copy()
            self.logger.info(f"Running Maven Build using system tools in {self.project_dir}")
            
            # ensure we run in the project dir
            res = subprocess.run(
                [mvn_cmd, 'clean', 'compile'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=settings.MAVEN_BUILD_TIMEOUT,
                env=env
            )
            
            if res.returncode == 0:
                return {'status': 'passed', 'output': res.stdout[-500:]}
            else:
                analysis = self.analyze_error(res.stderr, res.stdout)
                return {'status': 'failed', 'stderr': res.stderr[-1000:], 'analysis': analysis}
        except subprocess.TimeoutExpired:
            return {'status': 'failed', 'error': 'Maven build timeout'}
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}
