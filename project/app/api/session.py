from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Session as SessionModel, SessionParticipant
from app.schemas.user import SessionCreateResponse, SessionStatusResponse
import random

router = APIRouter(prefix="/api/session", tags=["session"])


def generate_session_code(db: Session) -> str:
    for _ in range(10):
        code = str(random.randint(1000, 9999))
        existing = db.query(SessionModel).filter(SessionModel.code == code).first()
        if not existing:
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate a unique session code",
    )


def get_session_by_code(db: Session, code: str):
    return db.query(SessionModel).filter(SessionModel.code == code).first()


def get_participant(db: Session, session_id: int, username: str):
    return (
        db.query(SessionParticipant)
        .filter(SessionParticipant.session_id == session_id)
        .filter(SessionParticipant.username == username)
        .first()
    )


@router.post("/create", response_model=SessionCreateResponse)
def create_session(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    code = generate_session_code(db)
    session = SessionModel(code=code, host_username=current_user)
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionCreateResponse(code=session.code, host=session.host_username)


@router.post("/{code}/join", response_model=SessionStatusResponse)
def join_session(code: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    session = get_session_by_code(db, code)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.host_username == current_user:
        status_value = "Host"
    else:
        participant = get_participant(db, session.id, current_user)
        if not participant:
            participant = SessionParticipant(session_id=session.id, username=current_user)
            db.add(participant)
            db.commit()
        status_value = "Participant"

    return SessionStatusResponse(code=session.code, host=session.host_username, status=status_value)


@router.get("/{code}", response_model=SessionStatusResponse)
def get_session(code: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    session = get_session_by_code(db, code)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.host_username == current_user:
        status_value = "Host"
    else:
        participant = get_participant(db, session.id, current_user)
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not part of this session",
            )
        status_value = "Participant"

    return SessionStatusResponse(code=session.code, host=session.host_username, status=status_value)


@router.post("/{code}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_session(code: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    session = get_session_by_code(db, code)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.host_username == current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host cannot leave session; use end session instead",
        )

    participant = get_participant(db, session.id, current_user)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not part of this session",
        )

    db.delete(participant)
    db.commit()


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(code: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    session = get_session_by_code(db, code)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.host_username != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the session host can end this session",
        )

    db.query(SessionParticipant).filter(SessionParticipant.session_id == session.id).delete()
    db.delete(session)
    db.commit()
