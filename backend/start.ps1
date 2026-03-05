Write-Host "Activating virtual environment..."
& "..\.venv311\Scripts\Activate.ps1"

Write-Host "Starting FastAPI server..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
