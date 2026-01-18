# Backend API Reference

Base URL: `http://localhost:8000`

## 1. System
### `GET /health`
Returns the health status of the API.
- **Response**: `{"status": "healthy", "version": "2.0"}`

### `GET /api/v1/system/logs`
Streams the backend server logs.
- **Params**: `lines` (int, default=100)
- **Response**: `{"logs": ["log line 1", ...]}`

## 2. File Operations
### `POST /api/v1/upload`
Upload a legacy application ZIP or file.
- **Body**: `multipart/form-data` with `file`.
- **Response**:
  ```json
  {
    "upload_id": "uuid",
    "filename": "app.zip",
    "path": "/abs/path/to/extracted",
    "message": "Upload successful"
  }
  ```

### `GET /api/v1/download`
Download the migrated output as a ZIP.
- **Response**: Binary stream (`application/zip`).

## 3. Orchestration
### `POST /api/v1/orchestrate`
Start the migration pipeline.
- **Body**:
  ```json
  {
    "websphere_input": "/abs/path/to/source",
    "liberty_output": "migrated_open_liberty",
    "max_iterations": 1
  }
  ```
- **Response**: `{"job_id": "uuid", "status": "started"}`

### `GET /api/v1/jobs`
List all jobs and their status.

### `GET /api/v1/jobs/{job_id}`
Get detailed status of a specific job.
