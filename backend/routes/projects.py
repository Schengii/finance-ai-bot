import os, json
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/api/projects", response_model=list)
async def get_projects():
    """Return list of projects for portfolio grid"""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "projects.json")
    if not os.path.isfile(data_path):
        raise HTTPException(status_code=404, detail="Projects data not found")
    with open(data_path, "r", encoding="utf-8") as f:
        try:
            projects = json.load(f)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail="Invalid projects JSON")
    return projects
