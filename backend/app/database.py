"""
Database layer for persistent job storage using SQLite
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str = "data/migration_agent.db"):
        self.db_path = db_path
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        """Create tables if they don't exist"""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_phase TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    progress TEXT,
                    error TEXT,
                    input_path TEXT,
                    output_path TEXT,
                    output_archive TEXT,
                    metrics TEXT,
                    config TEXT
                );
                
                CREATE TABLE IF NOT EXISTS job_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    data TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );
                
                CREATE TABLE IF NOT EXISTS job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    iteration INTEGER,
                    phase TEXT,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_job_events_job_id ON job_events(job_id);
                CREATE INDEX IF NOT EXISTS idx_job_history_job_id ON job_history(job_id);
            """)
    
    def create_job(self, job_id: str, job_type: str, config: Dict = None) -> None:
        """Create a new job record"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (id, type, status, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_type,
                'starting',
                json.dumps(config or {}),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
    
    def update_job(self, job_id: str, **kwargs) -> None:
        """Update job fields dynamically"""
        if not kwargs:
            return
        
        # Convert dict/list fields to JSON
        for key in ['metrics', 'config']:
            if key in kwargs and isinstance(kwargs[key], (dict, list)):
                kwargs[key] = json.dumps(kwargs[key])
        
        # Build dynamic UPDATE query
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        set_clause += ", updated_at = ?"
        
        values = list(kwargs.values()) + [datetime.now().isoformat(), job_id]
        
        with self.get_connection() as conn:
            conn.execute(f"""
                UPDATE jobs 
                SET {set_clause}
                WHERE id = ?
            """, values)
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job with all related data"""
        with self.get_connection() as conn:
            # Get main job data
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            job = dict(row)
            
            # Parse JSON fields
            for field in ['metrics', 'config']:
                if job.get(field):
                    try:
                        job[field] = json.loads(job[field])
                    except:
                        job[field] = {}
            
            # Get progress details (events)
            cursor = conn.execute("""
                SELECT timestamp, event_type as type, data
                FROM job_events
                WHERE job_id = ?
                ORDER BY timestamp ASC
            """, (job_id,))
            
            events = []
            for event_row in cursor.fetchall():
                event = dict(event_row)
                if event.get('data'):
                    try:
                        event['data'] = json.loads(event['data'])
                    except:
                        pass
                events.append(event)
            
            job['progress_details'] = events
            
            # Get transformation history
            cursor = conn.execute("""
                SELECT iteration, result
                FROM job_history
                WHERE job_id = ? AND phase = 'transformation'
                ORDER BY iteration ASC
            """, (job_id,))
            
            transformation_history = []
            for hist_row in cursor.fetchall():
                hist = dict(hist_row)
                if hist.get('result'):
                    try:
                        transformation_history.append({
                            'iteration': hist['iteration'],
                            'result': json.loads(hist['result'])
                        })
                    except:
                        pass
            
            job['transformation_history'] = transformation_history
            
            # Get validation history
            cursor = conn.execute("""
                SELECT iteration, result
                FROM job_history
                WHERE job_id = ? AND phase = 'validation'
                ORDER BY iteration ASC
            """, (job_id,))
            
            validation_history = []
            for hist_row in cursor.fetchall():
                hist = dict(hist_row)
                if hist.get('result'):
                    try:
                        validation_history.append({
                            'iteration': hist['iteration'],
                            'result': json.loads(hist['result'])
                        })
                    except:
                        pass
            
            job['validation_history'] = validation_history
            
            return job
    
    def get_all_jobs(self, limit: int = 50) -> List[Dict]:
        """Get recent jobs (summary only, no events/history)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, type, status, current_phase, created_at, progress, error
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            jobs = {}
            for row in cursor.fetchall():
                job = dict(row)
                jobs[job['id']] = job
            
            return jobs
    
    def add_job_event(self, job_id: str, event_type: str, data: Dict = None) -> None:
        """Add a progress event to job"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO job_events (job_id, timestamp, event_type, data)
                VALUES (?, ?, ?, ?)
            """, (
                job_id,
                datetime.now().isoformat(),
                event_type,
                json.dumps(data or {})
            ))
    
    def add_job_history(self, job_id: str, iteration: int, phase: str, result: Dict) -> None:
        """Add transformation/validation result to history"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO job_history (job_id, iteration, phase, result, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                iteration,
                phase,
                json.dumps(result),
                datetime.now().isoformat()
            ))
    
    def delete_old_jobs(self, days: int = 30) -> int:
        """Delete jobs older than N days"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        
        with self.get_connection() as conn:
            # Delete related records first (foreign key constraints)
            conn.execute("DELETE FROM job_events WHERE job_id IN (SELECT id FROM jobs WHERE created_at < ?)", (cutoff_iso,))
            conn.execute("DELETE FROM job_history WHERE job_id IN (SELECT id FROM jobs WHERE created_at < ?)", (cutoff_iso,))
            
            # Delete jobs
            cursor = conn.execute("DELETE FROM jobs WHERE created_at < ?", (cutoff_iso,))
            return cursor.rowcount

# Global database instance
db = Database()
