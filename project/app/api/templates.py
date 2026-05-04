from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.models.user import (
    PollTemplate, PollTemplateOption, PollTemplatePublished, PollTemplatePublishedOption, User,
    Poll as PollModel, PollOption as PollOptionModel
)
from app.schemas.poll import (
    TemplateResponse, TemplateCreate, AdminTemplateReviewResponse
)
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import get_user
import os

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
        can_be_public=template.can_be_public,
        created_by=template.created_by,
        options=options,
    )


def build_admin_template_review_response(
        db: Session,
        template: PollTemplate
):
    creator = db.query(User).filter(User.id == template.created_by).first()
    published = db.query(PollTemplatePublished).filter(
        PollTemplatePublished.original_poll_id == template.id
    ).first()
    options = (
        db.query(PollTemplateOption)
        .filter(PollTemplateOption.template_id == template.id)
        .all()
    )
    return AdminTemplateReviewResponse(
        id=template.id,
        title=template.title,
        description=template.description,
        can_be_public=template.can_be_public,
        is_publish=bool(published and published.is_public),
        created_by=template.created_by,
        creator_username=creator.username if creator else "unknown",
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
            (PollTemplate.can_be_public == True) | (PollTemplate.created_by == user.id)
        ).all()

    return [build_template_response(db, t) for t in templates]


@router.get("/public", response_model=List[TemplateResponse])
def list_public_templates(
        db: Session = Depends(get_db)
):
    published_rows = db.query(PollTemplatePublished).filter(
        PollTemplatePublished.is_public == True
    ).all()
    published_templates = []
    for published in published_rows:
        template = db.query(PollTemplate).filter(PollTemplate.id == published.original_poll_id).first()
        if not template:
            continue
        published_templates.append(build_template_response(db, template))
    return published_templates


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
        can_be_public=data.can_be_public,
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

@router.get("/{template_id:int}", response_model=TemplateResponse)
def get_template_by_id(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    template = get_template(db, template_id)
    user = get_user(db, current_user)
    if not template.can_be_public and template.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return build_template_response(db, template)


@router.put("/{template_id:int}", response_model=TemplateResponse)
def update_template(
        template_id: int,
        data: TemplateCreate,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    template = get_template(db, template_id)
    user = get_user(db, current_user)
    
    if template.created_by != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator or an admin can update this template")
    
    # Update template
    template.title = data.title
    template.description = data.description
    template.can_be_public = data.can_be_public

    old_options = db.query(PollTemplateOption).filter(PollTemplateOption.template_id == template.id).all()
    for option in old_options:
        if option.image_filename:
            file_path = os.path.join("uploads", option.image_filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    # Delete existing options
    db.query(PollTemplateOption).filter(PollTemplateOption.template_id == template.id).delete()
    
    # Add new options
    for option_text in data.options:
        db.add(PollTemplateOption(
            template_id=template.id,
            text=option_text
        ))
    
    db.commit()
    db.refresh(template)
    
    return build_template_response(db, template)


@router.patch("/{template_id:int}/can-be-public", response_model=TemplateResponse)
def update_template_can_be_public(
        template_id: int,
        can_be_public: bool,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    template = get_template(db, template_id)
    user = get_user(db, current_user)

    if template.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can update this template")

    template.can_be_public = can_be_public
    db.commit()
    db.refresh(template)

    return build_template_response(db, template)


@router.delete("/{template_id:int}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    template = get_template(db, template_id)
    user = get_user(db, current_user)

    if template.created_by != user.id and not user.is_admin:
        raise  HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator or an admin can delete this template")

    options = db.query(PollTemplateOption).filter(PollTemplateOption.template_id == template.id).all()
    for option in options:
        if option.image_filename:
            file_path = os.path.join("uploads", option.image_filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    db.query(PollTemplateOption).filter(PollTemplateOption.template_id == template.id).delete()
    db.delete(template)
    db.commit()


@router.get("/admin/review", response_model=List[AdminTemplateReviewResponse])
def list_templates_for_admin_review(
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    user = get_user(db, current_user)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    templates = db.query(PollTemplate).filter(PollTemplate.can_be_public == True).all()
    return [build_admin_template_review_response(db, template) for template in templates]


@router.get("/admin/review/{template_id}", response_model=AdminTemplateReviewResponse)
def get_template_for_admin_review(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    user = get_user(db, current_user)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    template = get_template(db, template_id)
    if not template.can_be_public:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template is not marked for publication")

    return build_admin_template_review_response(db, template)


@router.post("/admin/review/{template_id}/publish", status_code=status.HTTP_201_CREATED)
def publish_template_from_admin_review(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    user = get_user(db, current_user)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    template = get_template(db, template_id)
    if not template.can_be_public:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template is not marked for publication")

    existing = db.query(PollTemplatePublished).filter(
        PollTemplatePublished.original_poll_id == template.id
    ).first()
    if existing:
        return {"id": existing.id, "message": "Template already published"}

    published = PollTemplatePublished(
        original_poll_id=template.id,
        title=template.title,
        description=template.description,
        created_by=template.created_by,
        is_public=True
    )
    db.add(published)
    db.commit()
    db.refresh(published)

    options = db.query(PollTemplateOption).filter(
        PollTemplateOption.template_id == template.id
    ).all()

    for option in options:
        db.add(PollTemplatePublishedOption(
            published_template_id=published.id,
            text=option.text
        ))

    db.commit()
    return {"id": published.id, "message": "Template published successfully"}


@router.post("/admin/review/{template_id}/reject", status_code=status.HTTP_200_OK)
def reject_template_from_admin_review(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    user = get_user(db, current_user)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    template = get_template(db, template_id)
    template.can_be_public = False

    published_rows = db.query(PollTemplatePublished).filter(
        PollTemplatePublished.original_poll_id == template.id
    ).all()
    for published in published_rows:
        db.query(PollTemplatePublishedOption).filter(
            PollTemplatePublishedOption.published_template_id == published.id
        ).delete()
        db.delete(published)

    db.commit()

    return {"message": "Template rejected and removed from publication queue and published tables"}


@router.post("/{template_id:int}/publish", status_code=status.HTTP_201_CREATED)
def publish_template(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    """Publish a template to make it available as a public option set"""
    template = get_template(db, template_id)
    user = get_user(db, current_user)
    
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can publish templates")
    
    # Check if template is marked as can_be_public
    if not template.can_be_public:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This template is not marked as able to be published")
    
    existing = db.query(PollTemplatePublished).filter(
        PollTemplatePublished.original_poll_id == template.id
    ).first()
    if existing:
        return {"id": existing.id, "message": "Template already published"}

    published = PollTemplatePublished(
        original_poll_id=template.id,
        title=template.title,
        description=template.description,
        created_by=template.created_by,
        is_public=True
    )
    db.add(published)
    db.commit()
    db.refresh(published)
    
    # Copy options from original template
    options = db.query(PollTemplateOption).filter(
        PollTemplateOption.template_id == template.id
    ).all()
    
    for option in options:
        db.add(PollTemplatePublishedOption(
            published_template_id=published.id,
            text=option.text
        ))
    
    db.commit()
    
    return {"id": published.id, "message": "Template published successfully"}


@router.patch("/{template_id:int}/options/{option_id:int}/image")
def set_option_image(
        template_id: int,
        option_id: int,
        filename: str,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
    template = get_template(db, template_id)
    user = get_user(db, current_user)

    if template.created_by != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    option = db.query(PollTemplateOption).filter(
        PollTemplateOption.id == option_id,
        PollTemplateOption.template_id == template_id
    ).first()

    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    option.image_filename = filename
    db.commit()
    db.refresh(option)

    return {"option_id": option.id, "image_filename": option.image_filename}