from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import (
    Session as SessionModel,
    SessionParticipant,
    Poll as PollModel,
    PollOption as PollOptionModel,
    Vote as VoteModel,
    User,
)
from app.schemas.user import (
    SessionCreateResponse,
    SessionJoinRequest, SessionStatusResponse,
    PollResponse,
    PollOptionResponse,
)
import random
from datetime import datetime
import string
import uuid

router = APIRouter(prefix="/api/session", tags=["session"])


def generate_session_code(db: Session) -> str:
    allowed = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = ''.join(random.choice(allowed) for _ in range(6))
        existing = db.query(SessionModel).filter(SessionModel.code == code).first()
        if not existing:
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate a unique session code",
    )


def generate_session_token(db: Session) -> str:
    for _ in range(10):
        token = str(uuid.uuid4())
        existing = db.query(SessionModel).filter(SessionModel.token == token).first()
        if not existing:
            return token
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate a unique session token",
    )


def get_session_by_token(db: Session, token: str):
    return db.query(SessionModel).filter(SessionModel.token == token).first()


def get_session_by_code(db: Session, code: str):
    return db.query(SessionModel).filter(SessionModel.code == code).first()


def get_participant(db: Session, session_id: int, username: str):
    return (
        db.query(SessionParticipant)
        .filter(SessionParticipant.session_id == session_id)
        .filter(SessionParticipant.username == username)
        .first()
    )


def get_poll_response(db: Session, poll: PollModel) -> PollResponse:
    """Get poll with aggregated vote counts from database."""
    options = []
    poll_options = db.query(PollOptionModel).filter(PollOptionModel.poll_id == poll.id).all()

    for option in poll_options:
        votes = db.query(VoteModel).filter(VoteModel.option_id == option.id).all()
        rating_count = len(votes)
        total_rating = sum(v.rating for v in votes) if votes else 0

        options.append(
            PollOptionResponse(
                id=option.id,
                name=option.text,
                rating_count=rating_count,
                total_rating=total_rating,
            )
        )

    return PollResponse(
        id=poll.id,
        title=poll.title,
        duration_seconds=poll.duration_seconds,
        start_time=poll.start_time,
        options=options,
    )


def get_poll_by_session(db: Session, session_id: int):
    return db.query(PollModel).filter(PollModel.session_id == session_id).first()


@router.post("/create", response_model=SessionCreateResponse)
def create_session(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    # Get user
    user = db.query(User).filter(User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Create session
    code = generate_session_code(db)
    token = generate_session_token(db)
    session = SessionModel(code=code, token=token, host_username=current_user)
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create poll for this session
    now = int(datetime.utcnow().timestamp())
    poll = PollModel(
        title="Best coffee shop nearby",
        description="Rate coffee places from 0-5",
        creator_id=user.id,
        session_id=session.id,
        duration_seconds=180,
        start_time=now,
    )
    db.add(poll)
    db.commit()
    db.refresh(poll)

    # Create poll options
    options = ["Starbucks", "Costa", "Local Cafe"]
    for option_text in options:
        db.add(PollOptionModel(poll_id=poll.id, text=option_text))
    db.commit()

    return SessionCreateResponse(token=session.token, code=session.code, host=session.host_username)


@router.post("/join", response_model=SessionStatusResponse)
def join_session(
    session_join: SessionJoinRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    code = session_join.code.strip().upper()
    session = get_session_by_code(db, code)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.host_username != current_user:
        participant = get_participant(db, session.id, current_user)
        if not participant:
            participant = SessionParticipant(session_id=session.id, username=current_user)
            db.add(participant)
            db.commit()
        status_value = "Participant"
    else:
        status_value = "Host"

    # Get the actual poll for this session
    poll = get_poll_by_session(db, session.id)
    poll_data = get_poll_response(db, poll) if poll else None

    return SessionStatusResponse(
        token=session.token,
        host=session.host_username,
        status=status_value,
        poll=poll_data,
    )


@router.get("/{token}", response_model=SessionStatusResponse)
def get_session(token: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.host_username != current_user:
        participant = get_participant(db, session.id, current_user)
        if not participant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this session")
        status_value = "Participant"
    else:
        status_value = "Host"
        response_code = session.code

    # Get the actual poll for this session
    poll = get_poll_by_session(db, session.id)
    poll_data = get_poll_response(db, poll) if poll else None

    return SessionStatusResponse(
        token=session.token,
        code=session.code,
        host=session.host_username,
        status=status_value,
        poll=poll_data,
    )


class VoteRequest(BaseModel):
    option_id: int
    rating: int


@router.post("/{token}/vote", response_model=dict)
def vote_on_option(token: str, vote: VoteRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """Record a vote on a poll option."""
    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Check if user is part of this session
    is_host = session.host_username == current_user
    if not is_host:
        participant = get_participant(db, session.id, current_user)
        if not participant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this session")

    # Get poll and option
    poll = get_poll_by_session(db, session.id)
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    option = db.query(PollOptionModel).filter(
        PollOptionModel.id == vote.option_id,
        PollOptionModel.poll_id == poll.id
    ).first()
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")

    # Validate rating
    if vote.rating < 0 or vote.rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 0 and 5")

    # Get user
    user = db.query(User).filter(User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if user already voted on this option
    existing_vote = db.query(VoteModel).filter(
        VoteModel.poll_id == poll.id,
        VoteModel.option_id == vote.option_id,
        VoteModel.user_id == user.id
    ).first()

    if existing_vote:
        # Update existing vote
        existing_vote.rating = vote.rating
        existing_vote.updated_at = datetime.utcnow()
    else:
        # Create new vote
        new_vote = VoteModel(
            poll_id=poll.id,
            option_id=vote.option_id,
            user_id=user.id,
            rating=vote.rating
        )
        db.add(new_vote)

    db.commit()
    return {"detail": "Vote recorded successfully"}


@router.post("/{token}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_session(token: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.host_username == current_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host cannot leave session; use end session instead")

    participant = get_participant(db, session.id, current_user)
    if not participant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this session")

    db.delete(participant)
    db.commit()


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(token: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.host_username != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the session host can end this session")

    poll = get_poll_by_session(db, session.id)
    if poll:
        db.query(VoteModel).filter(VoteModel.poll_id == poll.id).delete()
        db.query(PollOptionModel).filter(PollOptionModel.poll_id == poll.id).delete()
        db.delete(poll)

    db.query(SessionParticipant).filter(SessionParticipant.session_id == session.id).delete()
    db.delete(session)
    db.commit()
