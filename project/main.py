import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.models.user import Base, User
from app.core.database import engine, SessionLocal
from app.core.security import get_password_hash
from app.api import auth, polls, session as session_api, templates, upload
from app.models.user import Base, User, PollTemplate
from sqlalchemy import inspect, text


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

Base.metadata.create_all(bind=engine)


def ensure_poll_voting_mode_column() -> None:
    inspector = inspect(engine)
    if "polls" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("polls")}
    if "voting_mode" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE polls ADD COLUMN voting_mode VARCHAR(20) NOT NULL DEFAULT 'stars'"))


def ensure_image_path_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    targets = ("poll_options", "poll_template_options", "poll_templates_publish_options")

    for table in targets:
        if table not in table_names:
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "image_path" in columns:
            continue
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN image_path VARCHAR NULL"))


ensure_poll_voting_mode_column()
ensure_image_path_columns()

def create_default_admin_user() -> None:
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.username == "admin1").first()
        if not existing_admin:
            admin_user = User(
                username="admin1",
                email="admin1@example.com",
                hashed_password=get_password_hash("admin1"),
                is_admin=True,
            )
            db.add(admin_user)
            db.commit()
    finally:
        db.close()

def create_dummy_template() -> None:
    db = SessionLocal()
    try:
        existing = db.query(PollTemplate).filter(PollTemplate.id == 1).first()
        if not existing:
            dummy = PollTemplate(
                id=1,
                title="Domyślna pusta ankieta, nie edytowac",
                description=None,
                created_by=1,
                can_be_public=False,
            )
            db.add(dummy)
            db.commit()
    finally:
        db.close()

create_default_admin_user()
create_dummy_template()

app = FastAPI(
    title="Voting App API",
    description="A voting application API",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(polls.router)
app.include_router(session_api.router)
app.include_router(templates.router)
app.include_router(upload.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Voting App API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
