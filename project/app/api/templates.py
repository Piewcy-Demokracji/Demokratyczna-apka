from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.models.user import (
    PollTemplate, PollTemplateOption, User,
    Poll as PollModel, PollOption as PollOptionModel
)
from app.schemas.poll import (
    TemplateResponse, TemplateCreate
)
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import get_user

router = APIRouter(prefix="/api/templates", tags=["templates"])

def get_template(
        db: Session,
        template_id: int
):
    template = db.query(PollTemplate).filter(PollTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template

def build_template_response(
        db: Session,
        template: PollTemplate
):
    options = (
        db.query(PollTemplateOption)
        .filter(PollTemplateOption.template_id == template.id)
        .all()
    )
    return TemplateResponse(
        id=template.id,
        title=template.title,
        description=template.description,
        is_public=template.is_public,
        created_by=template.created_by,
        options=options,
    )


@router.get("/", response_model=List[TemplateResponse])
def list_public_templates(
        filter: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if filter == "mine":
        templates = db.query(PollTemplate).filter(
            PollTemplate.created_by == user.id
        ).all()
    else:
        templates = db.query(PollTemplate).filter(
            (PollTemplate.is_public == True) | (PollTemplate.created_by == user.id)
        ).all()

    return [build_template_response(db, t) for t in templates]


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
        data: TemplateCreate,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    user = get_user(db, current_user)
    template = PollTemplate(
        title=data.title,
        description=data.description,
        is_public=data.is_public,
        created_by=user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    for option_text in data.options:
        db.add(PollTemplateOption(
            template_id=template.id,
            text=option_text
        ))
    db.commit()

    return build_template_response(db, template)

@router.get("/{template_id}", response_model=TemplateResponse)
def get_template_by_id(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    template = get_template(db, template_id)
    user = get_user(db, current_user)
    if not template.is_public and template.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return build_template_response(db, template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    template = get_template(db, template_id)
    user = get_user(db, current_user)

    if template.created_by != user.id:
        raise  HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can delete this template")

    db.query(PollTemplateOption).filter(PollTemplateOption.template_id == template.id).delete()
    db.delete(template)
    db.commit()