import os, json
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/api/blog", response_model=list)
async def get_blog_posts():
    """Return list of blog posts for portfolio site"""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "blog.json")
    if not os.path.isfile(data_path):
        raise HTTPException(status_code=404, detail="Blog data not found")
    with open(data_path, "r", encoding="utf-8") as f:
        try:
            posts = json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid blog JSON")
    return posts
