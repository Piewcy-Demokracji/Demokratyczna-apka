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
    SessionOptionInput,
)
from app.api.upload import validate_image_path, copy_image_for_session
from typing import Optional, Union
import random
from datetime import datetime
import string
import uuid
import json
from PIL import Image, ImageDraw, ImageFont
import base64
import io
import platform

router = APIRouter(prefix="/api/session", tags=["session"])


def _normalize_session_option(raw: Union[SessionOptionInput, str]) -> SessionOptionInput:
    if isinstance(raw, str):
        return SessionOptionInput(text=raw, image_path=None)
    return raw


def generate_image_with_poll_results(poll: PollResponse) -> str:
    """
        Generates an image with the poll results, showing the top 10 options based on their average rating.

        param poll: PollResponse - The poll containing the options and their ratings.

        return: An image as base64 string with the poll results displayed.
    """
    options_scored = []
    max_name_length = 0

    for option in poll.options:
        final_score = (option.total_rating / option.rating_count) if (option.rating_count > 0) else 0
        options_scored.append((option, final_score))
        max_name_length = max(max_name_length, len(option.name))

    options_scored.sort(key=lambda x: x[1], reverse=True)
    
    image_width = max_name_length * 40 + 50
    image_height = 400 #Add adjustable height once options with images are implemented
    background_color = (134,0,21)
    font_color = (34,177,76)

    results_img = Image.new("RGB", (image_width,image_height), color=background_color)
    d = ImageDraw.Draw(results_img)
    font_size = 20
    
    if platform.system() == 'Windows':
        try:
            font = ImageFont.truetype('C:\\Windows\\Fonts\\arial.ttf', font_size)
        except OSError:
            font = ImageFont.load_default()
    else:
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', font_size)
        except OSError:
            font = ImageFont.load_default()
    
    row_modifier = 1
    column = 0 

    for i in range(0, min(10, len(options_scored))):
        option, final_score = options_scored[i]
        x = 100 + max_name_length * 20 * column
        y = 30 + 50 * row_modifier
        d.text(( x , y ),
            f"{i+1}. {option.name}: {final_score:.2f}",
                fill=font_color,
                font=font, 
                stroke_width=1, 
                stroke_fill=font_color)
        row_modifier += 1
        if i % 5 == 4:
            column += 1
            row_modifier = 1

    buf = io.BytesIO()
    results_img.save(buf, format='PNG')
    img_str = base64.b64encode(buf.getvalue()).decode('utf-8')

    return img_str 

def generate_session_code(db: Session) -> str:
    """
    Generates a unique 6-character session code consisting of uppercase letters and digits.

    param db: Database session for checking existing codes.

    return: A unique session code.
    """
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
    """
    Generates a unique session token using UUID4.

    param db: Database session for checking existing tokens.

    return: A unique session token.
    """
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
    """
    Fetches a session from the database based on the provided token.

    param db: Database session for querying.
    param token: The unique token associated with the session.

    return: The session object if found, otherwise None.
    """
    return db.query(SessionModel).filter(SessionModel.token == token).first()


def get_session_by_code(db: Session, code: str):
    """
    Fetches a session from the database based on the provided session code.

    param db: Database session for querying.
    param code: The unique session code.

    return: The session object if found, otherwise None.
    """
    return db.query(SessionModel).filter(SessionModel.code == code).first()


def get_participant(db: Session, session_id: int, username: str):
    """
    Fetches a session participant from the database based on the session ID and username.

    param db: Database session for querying.
    param session_id: The ID of the session.
    param username: The username of the participant.

    return: The session participant object if found, otherwise None.
    """
    return (
        db.query(SessionParticipant)
        .filter(SessionParticipant.session_id == session_id)
        .filter(SessionParticipant.username == username)
        .first()
    )


def get_poll_response(db: Session, poll: PollModel, session_id: int, current_user_id: Optional[int] = None) -> PollResponse:
    """
    Get poll with aggregated vote counts from database.

    param db: Database session for querying.
    param poll: The poll for which to fetch the results.
    param session_id: The ID of the session to which the poll belongs.
    param current_user_id: The ID of the current user (optional, used to include user's own vote in the response).

    return: A PollResponse object containing the poll details and aggregated vote counts.
    """
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
                image_path=option.image_path,
            )
        )

    return PollResponse(
        id=poll.id,
        title=poll.title,
        duration_seconds=poll.duration_seconds,
        start_time=poll.start_time,
        voting_mode=getattr(poll, "voting_mode", "stars"),
        options=options,
    )


def get_poll_by_session(db: Session, session_id: int):
    """
    Fetches the poll associated with a given session ID.

    param db: Database session for querying.
    param session_id: The ID of the session for which to fetch the poll.

    return: The poll object if found, otherwise None.
    """
    return db.query(PollModel).filter(PollModel.session_id == session_id).first()


def is_poll_expired(poll: PollModel) -> bool:
    """
    Checks if the poll has expired based on its start time and duration.
    
    param poll: The poll to ckeck for expiration.
    
    return: True if the poll has expired, otherwise False.
    """
    now = int(datetime.utcnow().timestamp())
    elapsed = now - poll.start_time
    return elapsed >= poll.duration_seconds


def get_user_by_username(db: Session, username: str) -> User:
    """
    Fetches a user from the database based on the provided username.

    param db: Database session for querying.
    param username: The username of the user to fetch.

    return: The user object if found, otherwise raises HTTPException with 404 status.
    """
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
    """
    Endpoint to create a new session.

    param session_request: The request body containing optional template ID, duration, and options for the poll.
    param db: Database session for querying and persisting data.
    param current_user: The username of the currently authenticated user.

    return: A SessionCreateResponse object containing the session token, code and host username.
    """
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
        voting_mode=session_request.voting_mode if session_request.voting_mode in {"stars", "single"} else "stars",
        start_time=now,
    )
    db.add(poll)
    db.commit()
    db.refresh(poll)

    if session_request.options:
        for raw_option in session_request.options:
            option_input = _normalize_session_option(raw_option)
            validated_path = validate_image_path(option_input.image_path)
            copied_image = copy_image_for_session(validated_path)
            db.add(PollOptionModel(
                poll_id=poll.id,
                text=option_input.text,
                image_path=copied_image,
            ))
    elif template:
        template_options = db.query(PollTemplateOption).filter(
            PollTemplateOption.template_id == template.id
        ).all()
        for template_option in template_options:
            copied_image = copy_image_for_session(template_option.image_path)
            db.add(PollOptionModel(
                poll_id=poll.id,
                text=template_option.text,
                image_path=copied_image,
            ))
    db.commit()

    return SessionCreateResponse(token=session.token, code=session.code, host=session.host_username)


@router.post("/join", response_model=SessionStatusResponse)
def join_session(
    session_join: SessionJoinRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Endpoint to join an existing session using a session code.

    param session_join: The request body containing the session code to join.
    param db: Database session for querying and persisting data.
    param current_user: The username of the currently authenticated user.

    return: A SessionStatusResponse object containing the session token, host username, status (Host/Participant), and poll details if available.
    """
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
    """
    Endpoint to get the current status of a session, including poll details if available.

    param token: The unique token associated with the session.
    param db: Database session for querying.
    param current_user: The username of the currently authenticated user.

    return: A SessionStatusResponse object containing the session token, host username, status (Host/Participant), and poll details and image with results if available.
    """
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
    img_str = generate_image_with_poll_results(poll_data) if is_poll_expired(poll) else None

    return SessionStatusResponse(
        token=session.token,
        code=session.code,
        host=session.host_username,
        status=status_value,
        poll=poll_data,
        image_base64=img_str,     
    )


class VoteRequest(BaseModel):
    """
    Request body for voting on a poll option, containing the option ID and the rating value.

    Arg:
    option_id (int): The ID of the poll option being voted on.
    rating (int): The rating value for the option, typically between 0 and 5.
    """
    option_id: int
    rating: int


@router.post("/{token}/vote", response_model=dict)
def vote_on_option(token: str, vote: VoteRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Records a vote on a poll option. 

    param token: The unique token associated with the session.
    param vote: The request body containing the option ID and rating value.
    param db: Database session for querying and persisting data.
    param current_user: The username of the currently authenticated user.

    return: A dictionary containing a success message if the vote was recorded successfully, otherwise raises an HTTPException with an appropriate error message and status code.
    """
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

    is_single_choice = getattr(poll, "voting_mode", "stars") == "single"
    if is_single_choice and vote.rating != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Single-choice polls accept only one selected option")

    # Get user
    user = get_user_by_username(db, current_user)

    existing_votes = db.query(VoteModel).filter(
        VoteModel.poll_id == poll.id,
        VoteModel.user_id == user.id,
    ).all()

    if is_single_choice:
        for existing_vote in existing_votes:
            if existing_vote.option_id != vote.option_id:
                db.delete(existing_vote)

        existing_vote = next((existing for existing in existing_votes if existing.option_id == vote.option_id), None)
        if existing_vote:
            existing_vote.rating = 1
            existing_vote.updated_at = datetime.utcnow()
        else:
            new_vote = VoteModel(
                poll_id=poll.id,
                option_id=vote.option_id,
                user_id=user.id,
                rating=1,
            )
            db.add(new_vote)
    else:
        # Check if user already voted on this option
        existing_vote = next((existing for existing in existing_votes if existing.option_id == vote.option_id), None)

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

    if is_single_choice:
        votes_dict = {str(vote.option_id): 1}
    else:
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
    """
    Endpoint to end the poll early, allowing the host to finalize the results before the original duration has expired.

    param token: The unique token associated with the session.
    param db: Database session for querying and persisting data.
    param current_user: The username of the currently authenticated user.
    
    return: A SessionStatusResponse object containing the session token, host username, status (Host), poll details and image with final results.
    """
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
    img_str = generate_image_with_poll_results(poll_data) if is_poll_expired(poll) else None

    return SessionStatusResponse(
        token=session.token,
        code=session.code,
        host=session.host_username,
        status="Host",
        poll=poll_data,
        image_base64=img_str,
    )


@router.post("/{token}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_session(token: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Endpoint for a participant to leave a session. The host cannot leave the session and must end it instead.

    param token: The unique token associated with the session.
    param db: Database session for querying and persisting data.
    param current_user: The username of the currently authenticated user.

    return: No content if the participant succesfully leaves the session, otehrwise raises an HTTPException with an appropriate error message and status code.
    """
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
    """
    Endpoint to delete a session. Only the host can delete the session, which will remove all associated data including the poll, options, votes and prticipants.

    param token: The unique token associated with the session.
    param db: Database session for querying and persisting data.
    param current_user: The username of the currently authenticated user.

    return: No content if the session was deleted successfully, otherwise raises an HTTPException with an appropriate error message and status code.
    """
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
