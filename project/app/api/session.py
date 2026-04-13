from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import (
    Session as SessionModel,
    SessionParticipant,
    SessionUserVotes,
    Poll as PollModel,
    PollOption as PollOptionModel,
    Vote as VoteModel,
    User,
    PollTemplate,
    PollTemplateOption,
)
from app.schemas.user import (
    SessionCreateResponse,
    SessionJoinRequest, SessionStatusResponse,
    PollResponse,
    PollOptionResponse,
    SessionCreateRequest,
)
from typing import Optional
import random
from datetime import datetime
import string
import uuid
import json

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


def get_poll_response(db: Session, poll: PollModel, session_id: int, current_user_id: Optional[int] = None) -> PollResponse:
    """Get poll with aggregated vote counts from database."""
    options = []
    poll_options = db.query(PollOptionModel).filter(PollOptionModel.poll_id == poll.id).all()

    user_votes = {}
    if current_user_id is not None:
        saved_votes = db.query(SessionUserVotes).filter(
            SessionUserVotes.session_id == session_id,
            SessionUserVotes.user_id == current_user_id,
        ).first()
        if saved_votes and saved_votes.votes_json:
            try:
                user_votes = json.loads(saved_votes.votes_json)
            except json.JSONDecodeError:
                user_votes = {}

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
                user_rating=user_votes.get(str(option.id), 0),
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


def is_poll_expired(poll: PollModel) -> bool:
    now = int(datetime.utcnow().timestamp())
    elapsed = now - poll.start_time
    return elapsed >= poll.duration_seconds


def get_user_by_username(db: Session, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/create", response_model=SessionCreateResponse)
def create_session(
    session_request: SessionCreateRequest = SessionCreateRequest(),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # Get user
    user = get_user_by_username(db, current_user)

    # Create session
    code = generate_session_code(db)
    token = generate_session_token(db)
    session = SessionModel(code=code, token=token, host_username=current_user)
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create poll for this session
    now = int(datetime.utcnow().timestamp())
    
    # Get template if provided
    template = None
    if session_request.template_id:
        template = db.query(PollTemplate).filter(PollTemplate.id == session_request.template_id).first()
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    poll_title = template.title if template else "Best coffee shop nearby"
    poll_description = template.description if template else "Rate coffee places from 0-5"
    
    poll = PollModel(
        title=poll_title,
        description=poll_description,
        creator_id=user.id,
        session_id=session.id,
        duration_seconds=session_request.duration_seconds,
        start_time=now,
    )
    db.add(poll)
    db.commit()
    db.refresh(poll)

    if session_request.options:
        for option_text in session_request.options:
            db.add(PollOptionModel(poll_id=poll.id, text=option_text))
    # Create poll options from template or use defaults
    elif template:
        template_options = db.query(PollTemplateOption).filter(
            PollTemplateOption.template_id == template.id
        ).all()
        for template_option in template_options:
            db.add(PollOptionModel(poll_id=poll.id, text=template_option.text))
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
    user = get_user_by_username(db, current_user)
    poll_data = get_poll_response(db, poll, session.id, user.id) if poll else None

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
    user = get_user_by_username(db, current_user)
    poll_data = get_poll_response(db, poll, session.id, user.id) if poll else None

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

    if is_poll_expired(poll):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voting has ended")

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
    user = get_user_by_username(db, current_user)

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

    # Persist user's votes for this session to support reconnect/device switch.
    user_votes_row = db.query(SessionUserVotes).filter(
        SessionUserVotes.session_id == session.id,
        SessionUserVotes.user_id == user.id,
    ).first()
    if not user_votes_row:
        user_votes_row = SessionUserVotes(session_id=session.id, user_id=user.id, votes_json="{}")
        db.add(user_votes_row)

    votes_dict = {}
    if user_votes_row.votes_json:
        try:
            votes_dict = json.loads(user_votes_row.votes_json)
        except json.JSONDecodeError:
            votes_dict = {}

    votes_dict[str(vote.option_id)] = vote.rating
    user_votes_row.votes_json = json.dumps(votes_dict)
    user_votes_row.updated_at = datetime.utcnow()

    db.commit()
    return {"detail": "Vote recorded successfully"}


@router.post("/{token}/end-poll-early", response_model=SessionStatusResponse)
def end_poll_early(
    token: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.host_username != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the session host can end polling early")

    poll = get_poll_by_session(db, session.id)
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    if not is_poll_expired(poll):
        now = int(datetime.utcnow().timestamp())
        elapsed = max(now - poll.start_time, 0)
        poll.duration_seconds = elapsed
        poll.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(poll)

    user = get_user_by_username(db, current_user)
    poll_data = get_poll_response(db, poll, session.id, user.id)

    return SessionStatusResponse(
        token=session.token,
        code=session.code,
        host=session.host_username,
        status="Host",
        poll=poll_data,
    )


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

    db.query(SessionUserVotes).filter(SessionUserVotes.session_id == session.id).delete()

    db.query(SessionParticipant).filter(SessionParticipant.session_id == session.id).delete()
    db.delete(session)
    db.commit()
