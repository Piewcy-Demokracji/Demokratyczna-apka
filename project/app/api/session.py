from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import (
    Session as SessionModel,
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
from app.api.upload import validate_image_path, copy_image_for_session, claim_image_for_session, safe_delete_image
from typing import Optional, Union
import copy
import random
from datetime import datetime
import string
import uuid
from PIL import Image, ImageDraw, ImageFont
import base64
import io
import platform
import os

router = APIRouter(prefix="/api/session", tags=["session"])


def _normalize_session_option(raw: Union[SessionOptionInput, str]) -> SessionOptionInput:
    if isinstance(raw, str):
        return SessionOptionInput(text=raw, image_path=None)
    return raw


def _now_ts() -> int:
    return int(datetime.utcnow().timestamp())


def _empty_dict(value):
    return value if isinstance(value, dict) else {}


def _session_poll(session_row: SessionModel):
    return _empty_dict(_empty_dict(session_row.session_data).get("poll"))


def _session_options(session_row: SessionModel):
    options = _session_poll(session_row).get("options", [])
    return options if isinstance(options, list) else []


def _responses_users(session_row: SessionModel):
    responses = copy.deepcopy(_empty_dict(session_row.responses_data))
    users = responses.get("users", {})
    if not isinstance(users, dict):
        users = {}
        responses["users"] = users
    session_row.responses_data = responses
    return users


def _responses_aggregates(session_row: SessionModel):
    responses = copy.deepcopy(_empty_dict(session_row.responses_data))
    aggregates = responses.get("aggregates", {})
    if not isinstance(aggregates, dict):
        aggregates = {}
        responses["aggregates"] = aggregates
    session_row.responses_data = responses
    return aggregates


def _get_session_user_entry(users: dict, user: User) -> dict:
    entry = users.get(str(user.id))
    if isinstance(entry, dict):
        return entry

    legacy_entry = users.get(user.username)
    if isinstance(legacy_entry, dict):
        users[str(user.id)] = legacy_entry
        users.pop(user.username, None)
        return legacy_entry

    return {}


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
    background_color = (255,255,255)
    font_color = (0,0,0)

    results_img = Image.new("RGB", (image_width,image_height), color=background_color)
    d = ImageDraw.Draw(results_img)
    font_size = 20
    
    linux_font_paths = [
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf'
    ]
    font = None
    if platform.system() == 'Windows':
        try:
            font = ImageFont.truetype('C:\\Windows\\Fonts\\arial.ttf', font_size)
        except OSError:
            font = ImageFont.load_default()
    else:
        for path in linux_font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except OSError:
                    continue
    if font is None:
        font = ImageFont.load_default(size=font_size)
    
    row_modifier = 1
    column = 0 

    for i in range(0, min(10, len(options_scored))):
        option, final_score = options_scored[i]
        
        x = 100 + max_name_length * 20 * column
        y = 30 + 50 * row_modifier

        d.text(( x , y ),
            f"{i+1}. {option.name}: {final_score:.2f}",
                fill=font_color,
                font=font)
        row_modifier += 1
        if i % 5 == 4:
            column += 1
            row_modifier = 1

    buf = io.BytesIO()
    results_img.save(buf, format='PNG')
    img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
    results_img.show()
    results_img.close()

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
    return (
        db.query(SessionModel)
        .filter(SessionModel.token == token)
        .filter(SessionModel.status != "DELETED")
        .first()
    )


def get_session_by_code(db: Session, code: str):
    """
    Fetches a session from the database based on the provided session code.

    param db: Database session for querying.
    param code: The unique session code.

    return: The session object if found, otherwise None.
    """
    return (
        db.query(SessionModel)
        .filter(SessionModel.code == code)
        .filter(SessionModel.status != "DELETED")
        .first()
    )


def _is_poll_expired(poll_data: PollResponse) -> bool:
    elapsed = _now_ts() - poll_data.start_time
    return elapsed >= poll_data.duration_seconds


def _mark_session_ended_if_expired(session_row: SessionModel) -> None:
    if session_row.status != "ACTIVE":
        return

    poll = _session_poll(session_row)
    start_time = int(poll.get("start_time", _now_ts()))
    duration_seconds = int(poll.get("duration_seconds", 0))
    if _now_ts() - start_time < duration_seconds:
        return

    session_row.status = "ENDED"
    session_row.ended_at = datetime.utcnow()
    session_row.updated_at = datetime.utcnow()
    session_row.version = (session_row.version or 1) + 1


def _poll_response_from_session(session_row: SessionModel, current_user_id: Optional[int]) -> Optional[PollResponse]:
    poll = _session_poll(session_row)
    options_data = _session_options(session_row)
    if not poll:
        return None

    users = _responses_users(session_row)
    aggregates = _responses_aggregates(session_row)

    user_votes = {}
    if current_user_id is not None:
        user_entry = users.get(str(current_user_id), {})
        if isinstance(user_entry, dict):
            user_votes = user_entry.get("votes", {}) if isinstance(user_entry.get("votes", {}), dict) else {}

    options = []
    for idx, option in enumerate(options_data, start=1):
        option_id = int(option.get("id", idx))
        option_key = str(option.get("option_key", option_id))
        aggregate = aggregates.get(option_key, {}) if isinstance(aggregates.get(option_key, {}), dict) else {}
        options.append(
            PollOptionResponse(
                id=option_id,
                name=str(option.get("text", "")),
                rating_count=int(aggregate.get("rating_count", 0)),
                total_rating=int(aggregate.get("total_rating", 0)),
                user_rating=int(user_votes.get(option_key, 0)),
                image_path=option.get("image_path"),
            )
        )

    return PollResponse(
        id=session_row.id,
        title=str(poll.get("title", "")),
        duration_seconds=int(poll.get("duration_seconds", 0)),
        start_time=int(poll.get("start_time", _now_ts())),
        voting_mode=str(poll.get("voting_mode", "stars")),
        options=options,
    )


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
    Endpoint to create a new session. Per-option images are handled smartly:
    - Paths already referenced by a template/published option are physically copied
      so the session owns its own snapshot (isolation from later edits).
    - Paths from fresh uploads (not referenced anywhere) are claimed directly to
      avoid an unnecessary duplicate.
    """
    user = get_user_by_username(db, current_user)

    code = generate_session_code(db)
    token = generate_session_token(db)
    now = _now_ts()

    template = None
    if session_request.template_id:
        template = db.query(PollTemplate).filter(PollTemplate.id == session_request.template_id).first()
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    poll_title = template.title if template else "Best coffee shop nearby"
    poll_description = template.description if template else "Rate coffee places from 0-5"
    
    options_payload = []

    if session_request.options:
        for idx, raw_option in enumerate(session_request.options, start=1):
            option_input = _normalize_session_option(raw_option)
            validated_path = validate_image_path(option_input.image_path)
            stored_image = claim_image_for_session(db, validated_path)
            options_payload.append({
                "id": idx,
                "option_key": str(idx),
                "text": option_input.text,
                "image_path": stored_image,
                "created_from": "custom",
            })
    elif template:
        template_options = db.query(PollTemplateOption).filter(
            PollTemplateOption.template_id == template.id
        ).all()
        for idx, template_option in enumerate(template_options, start=1):
            copied_image = copy_image_for_session(template_option.image_path)
            options_payload.append({
                "id": idx,
                "option_key": str(idx),
                "text": template_option.text,
                "image_path": copied_image,
                "created_from": "template",
            })

    responses_users = {
        str(user.id): {
            "username": user.username,
            "joined_at": now,
            "left_at": None,
            "active": True,
            "votes": {},
            "updated_at": now,
        }
    }
    responses_aggregates = {
        str(option["option_key"]): {"rating_count": 0, "total_rating": 0}
        for option in options_payload
    }

    session = SessionModel(
        code=code,
        token=token,
        host_username=current_user,
        status="ACTIVE",
        version=1,
        session_data={
            "schema_version": 1,
            "host": {
                "host_user_id": user.id,
                "host_username": current_user,
            },
            "poll": {
                "title": poll_title,
                "description": poll_description,
                "template_id": session_request.template_id,
                "duration_seconds": session_request.duration_seconds,
                "start_time": now,
                "voting_mode": session_request.voting_mode if session_request.voting_mode in {"stars", "single"} else "stars",
                "options": options_payload,
            },
        },
        responses_data={
            "users": responses_users,
            "aggregates": responses_aggregates,
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

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
    session_row = get_session_by_code(db, code)
    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session_row.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session is not active")

    user = get_user_by_username(db, current_user)
    users = _responses_users(session_row)
    now = _now_ts()
    user_key = str(user.id)
    
    is_host = session_row.host_username == current_user

    existing = _get_session_user_entry(users, user)
    users[user_key] = {
        "username": user.username,
        "joined_at": existing.get("joined_at", now),
        "left_at": None,
        "active": True,
        "votes": existing.get("votes", {}) if isinstance(existing.get("votes", {}), dict) else {},
        "updated_at": now,
    }
    responses = copy.deepcopy(_empty_dict(session_row.responses_data))
    responses["users"] = users
    session_row.responses_data = responses
    session_row.updated_at = datetime.utcnow()
    session_row.version = (session_row.version or 1) + 1
    db.commit()

    _mark_session_ended_if_expired(session_row)
    if session_row.status != "ACTIVE":
        db.commit()
    db.refresh(session_row)
    
    status_value = "Host" if is_host else "Participant"
    poll_data = _poll_response_from_session(session_row, user.id)

    return SessionStatusResponse(
        token=session_row.token,
        host=session_row.host_username,
        status=status_value,
        session_status=session_row.status,
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
    session_row = get_session_by_token(db, token)
    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    user = get_user_by_username(db, current_user)

    if session_row.host_username != current_user:
        users = _responses_users(session_row)
        user_entry = _get_session_user_entry(users, user)
        if not user_entry or not user_entry.get("active", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this session")
        status_value = "Participant"
    else:
        status_value = "Host"

    _mark_session_ended_if_expired(session_row)
    db.commit()
    db.refresh(session_row)

    poll_data = _poll_response_from_session(session_row, user.id)
    img_str = generate_image_with_poll_results(poll_data) if poll_data and _is_poll_expired(poll_data) else None

    return SessionStatusResponse(
        token=session_row.token,
        code=session_row.code,
        host=session_row.host_username,
        status=status_value,
        session_status=session_row.status,
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
    session_row = (
        db.query(SessionModel)
        .filter(SessionModel.token == token)
        .filter(SessionModel.status != "DELETED")
        .with_for_update()
        .first()
    )
    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    user = get_user_by_username(db, current_user)

    users = _responses_users(session_row)
    user_key = str(user.id)
    user_entry = _get_session_user_entry(users, user)

    if not user_entry or not user_entry.get("active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this session")

    poll_data = _poll_response_from_session(session_row, user.id)
    if not poll_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    _mark_session_ended_if_expired(session_row)
    if session_row.status == "ENDED" or _is_poll_expired(poll_data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voting has ended")

    options = _session_options(session_row)
    selected_option = None
    selected_key = None
    for option in options:
        option_id = int(option.get("id", 0))
        if option_id == vote.option_id:
            selected_option = option
            selected_key = str(option.get("option_key", option_id))
            break
    if not selected_option or not selected_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")

    if vote.rating < 0 or vote.rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 0 and 5")

    is_single_choice = poll_data.voting_mode == "single"
    if is_single_choice and vote.rating != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Single-choice polls accept only one selected option")

    votes = user_entry.get("votes", {}) if isinstance(user_entry.get("votes", {}), dict) else {}
    aggregates = _responses_aggregates(session_row)

    def ensure_aggregate(option_key: str):
        item = aggregates.get(option_key)
        if not isinstance(item, dict):
            item = {"rating_count": 0, "total_rating": 0}
            aggregates[option_key] = item
        item["rating_count"] = int(item.get("rating_count", 0))
        item["total_rating"] = int(item.get("total_rating", 0))
        return item

    if is_single_choice:
        previous_votes = {k: int(v) for k, v in votes.items()}
        for key, previous_value in previous_votes.items():
            if key == selected_key:
                continue
            agg = ensure_aggregate(key)
            agg["rating_count"] = max(0, agg["rating_count"] - 1)
            agg["total_rating"] = max(0, agg["total_rating"] - previous_value)

        selected_agg = ensure_aggregate(selected_key)
        if selected_key not in votes:
            selected_agg["rating_count"] += 1
            selected_agg["total_rating"] += 1

        votes = {selected_key: 1}
    else:
        previous = int(votes.get(selected_key, 0))
        current = int(vote.rating)
        agg = ensure_aggregate(selected_key)

        if previous == 0 and current > 0:
            agg["rating_count"] += 1
            agg["total_rating"] += current
            votes[selected_key] = current
        elif previous > 0 and current == 0:
            agg["rating_count"] = max(0, agg["rating_count"] - 1)
            agg["total_rating"] = max(0, agg["total_rating"] - previous)
            votes.pop(selected_key, None)
        elif previous > 0 and current > 0:
            agg["total_rating"] += current - previous
            votes[selected_key] = current
        else:
            votes.pop(selected_key, None)

    now = _now_ts()
    user_entry["votes"] = votes
    user_entry["active"] = True
    user_entry["left_at"] = None
    user_entry["updated_at"] = now
    users[user_key] = user_entry

    responses = copy.deepcopy(_empty_dict(session_row.responses_data))
    responses["users"] = users
    responses["aggregates"] = aggregates
    session_row.responses_data = responses

    session_row.version = (session_row.version or 1) + 1
    session_row.updated_at = datetime.utcnow()

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
    session_row = (
        db.query(SessionModel)
        .filter(SessionModel.token == token)
        .filter(SessionModel.status != "DELETED")
        .with_for_update()
        .first()
    )
    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session_row.host_username != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the session host can end polling early")

    poll_data = _poll_response_from_session(session_row, None)
    if not poll_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    poll = _session_poll(session_row)
    now = _now_ts()
    elapsed = max(now - int(poll.get("start_time", now)), 0)
    poll["duration_seconds"] = elapsed

    session_data = copy.deepcopy(_empty_dict(session_row.session_data))
    session_data["poll"] = poll
    session_row.session_data = session_data

    session_row.status = "ENDED"
    session_row.ended_at = datetime.utcnow()
    session_row.updated_at = datetime.utcnow()
    session_row.version = (session_row.version or 1) + 1

    db.commit()
    db.refresh(session_row)

    user = get_user_by_username(db, current_user)
    poll_data = _poll_response_from_session(session_row, user.id)
    img_str = generate_image_with_poll_results(poll_data) if poll_data and _is_poll_expired(poll_data) else None

    return SessionStatusResponse(
        token=session_row.token,
        code=session_row.code,
        host=session_row.host_username,
        status="Host",
        session_status=session_row.status,
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
    session_row = (
        db.query(SessionModel)
        .filter(SessionModel.token == token)
        .filter(SessionModel.status != "DELETED")
        .with_for_update()
        .first()
    )
    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session_row.host_username == current_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host cannot leave session; use end session instead")

    user = get_user_by_username(db, current_user)
    users = _responses_users(session_row)
    user_key = str(user.id)
    user_entry = _get_session_user_entry(users, user)
    if not user_entry or not user_entry.get("active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this session")

    user_entry["active"] = False
    user_entry["left_at"] = _now_ts()
    user_entry["updated_at"] = _now_ts()
    users[user_key] = user_entry

    responses = copy.deepcopy(_empty_dict(session_row.responses_data))
    responses["users"] = users
    session_row.responses_data = responses
    session_row.updated_at = datetime.utcnow()
    session_row.version = (session_row.version or 1) + 1

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
    session_row = (
        db.query(SessionModel)
        .filter(SessionModel.token == token)
        .filter(SessionModel.status != "DELETED")
        .with_for_update()
        .first()
    )
    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session_row.host_username != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the session host can end this session")

    option_image_paths = [
        option.get("image_path")
        for option in _session_options(session_row)
        if option.get("image_path")
    ]
    for path in option_image_paths:
        safe_delete_image(path)

    session_row.status = "DELETED"
    session_row.deleted_at = datetime.utcnow()
    session_row.ended_at = session_row.ended_at or datetime.utcnow()
    session_row.updated_at = datetime.utcnow()
    session_row.version = (session_row.version or 1) + 1

    db.commit()
