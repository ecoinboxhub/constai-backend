from fastapi import APIRouter

router = APIRouter()

@router.get("")
def search_site(q: str = ""):
    return {"status": "success", "results": []}
