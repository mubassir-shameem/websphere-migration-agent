# Dashboard UI

Located in: `frontend/index.html` (Single Page Application)

## Architecture
- **Vanilla JS**: No frameworks (React/Vue) were used to keep the deployment simple (just one HTML file served by FastAPI).
- **Polling**: The UI polls `/api/v1/jobs` every 2 seconds to update the Job Monitor.

## Key Features
1.  **Global Input**: A sticky header for Project Path / Upload to ensure context is always visible.
2.  **Job Monitor**:
    - Displays active and past jobs.
    - Shows "Status" (Running, Completed, Failed).
    - **Download Button**: Appears dynamically when a job completes.
3.  **System Logs Tab**:
    - Polls `/api/v1/system/logs`.
    - Auto-scrolls to show the latest backend activity.
    - Essential for debugging "Long Running" processes (like LLM Transformation).

## Styling
- **CSS Variables**: Used for theme (Colors, Spacing).
- **Responsive**: `flex` and `grid` layouts allow it to work on different screen sizes.
