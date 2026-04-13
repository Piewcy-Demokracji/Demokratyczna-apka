from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.models.user import Base
from app.core.database import engine
from app.api import auth, polls, session as session_api, templates


def run_sqlite_migrations() -> None:
    with engine.begin() as connection:
        users_exists = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users' LIMIT 1")
        ).first()
        if users_exists:
            users_columns = {
                row[1] for row in connection.execute(text("PRAGMA table_info(users)"))
            }
            if "is_admin" not in users_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))

        templates_exists = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='poll_templates' LIMIT 1")
        ).first()
        if templates_exists:
            template_columns = {
                row[1] for row in connection.execute(text("PRAGMA table_info(poll_templates)"))
            }
            if "can_be_public" not in template_columns:
                if "is_public" in template_columns:
                    connection.execute(text("ALTER TABLE poll_templates RENAME COLUMN is_public TO can_be_public"))
                else:
                    connection.execute(text("ALTER TABLE poll_templates ADD COLUMN can_be_public BOOLEAN DEFAULT 0"))

        legacy_publish_exists = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='poll_templates_published' LIMIT 1")
        ).first()
        publish_exists = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='poll_templates_publish' LIMIT 1")
        ).first()
        if legacy_publish_exists and not publish_exists:
            connection.execute(text("ALTER TABLE poll_templates_published RENAME TO poll_templates_publish"))

        legacy_publish_options_exists = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='poll_templates_published_options' LIMIT 1")
        ).first()
        publish_options_exists = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='poll_templates_publish_options' LIMIT 1")
        ).first()
        if legacy_publish_options_exists and not publish_options_exists:
            connection.execute(text("ALTER TABLE poll_templates_published_options RENAME TO poll_templates_publish_options"))


run_sqlite_migrations()

# Create database tables
Base.metadata.create_all(bind=engine)

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

# Include routers
app.include_router(auth.router)
app.include_router(polls.router)
app.include_router(session_api.router)
app.include_router(templates.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Voting App API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
