from fastapi import APIRouter

router = APIRouter(prefix="/api/polls", tags=["polls"])


@router.get("/")
def get_polls():
    """Get all polls"""
    return {"message": "Get all polls - Coming soon"}


@router.post("/")
def create_poll():
    """Create a new poll"""
    return {"message": "Create poll - Coming soon"}


@router.get("/{poll_id}")
def get_poll(poll_id: int):
    """Get a specific poll"""
    return {"message": f"Get poll {poll_id} - Coming soon"}


@router.post("/{poll_id}/vote")
def vote_on_poll(poll_id: int):
    """Vote on a poll option"""
    return {"message": "Vote on poll - Coming soon"}
