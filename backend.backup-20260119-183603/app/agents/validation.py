
import os
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
            
        # Check if Maven is available (Local first, then system)
        local_mvn = os.path.abspath(os.path.join(os.path.dirname(self.project_dir), '..', 'apache-maven-3.9.6', 'bin', 'mvn'))
        mvn_cmd = 'mvn'
        
        if os.path.exists(local_mvn):
            self.logger.info(f"Using local Maven: {local_mvn}")
            mvn_cmd = local_mvn
        else:
            try:
                check_mvn = subprocess.run(['which', 'mvn'], capture_output=True, text=True, timeout=5)
                if check_mvn.returncode != 0:
                    return {'status': 'skipped', 'message': 'Maven not installed'}
            except Exception:
                return {'status': 'skipped', 'message': 'Maven check failed'}
            
        try:
            # Setup environment with local JDK if available
            env = os.environ.copy()
            
            # Check for local JDK (macOS structure) - Corrected path
            # self.project_dir is .../output/migrated_open_liberty
            # dirname is .../output
            # .. is .../was2oss_agent (Root)
            local_jdk = os.path.abspath(os.path.join(os.path.dirname(self.project_dir), '..', 'jdk-17.0.9+9', 'Contents', 'Home'))
            
            if os.path.exists(local_jdk):
                self.logger.info(f"Using local JDK: {local_jdk}")
                env['JAVA_HOME'] = local_jdk
                env['PATH'] = f"{local_jdk}/bin:{env.get('PATH', '')}"
            
            # ensure we run in the project dir
            res = subprocess.run(
                [mvn_cmd, 'clean', 'compile'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300,
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
