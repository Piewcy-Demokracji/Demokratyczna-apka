from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Represents an authenticated user account in the application."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Poll(Base):
    """Data model for a stored poll attached to a session or template."""
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    creator_id = Column(Integer)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    duration_seconds = Column(Integer, default=180)
    voting_mode = Column(String, default="stars")
    start_time = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PollOption(Base):
    """Data model for an option within a poll, optionally linking to an uploaded image."""
    __tablename__ = "poll_options"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer)
    text = Column(String)
    image_path = Column(String, nullable=True)
    votes_count = Column(Integer, default=0)


class Vote(Base):
    """Record of a user's vote on a poll option."""
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id"), index=True)
    option_id = Column(Integer, ForeignKey("poll_options.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Session(Base):
    """Represents a live or completed voting session, including poll payload and response aggregates."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    code = Column(String(6), unique=True, index=True)
    host_username = Column(String, index=True)
    session_data = Column(JSON, nullable=False, default=dict)
    responses_data = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), default="ACTIVE", index=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)


class SessionParticipant(Base):
    """Tracks when a user joined or left a session."""
    __tablename__ = "session_participants"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    username = Column(String, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow)


class SessionUserVotes(Base):
    """Stores legacy per-user vote data for a session during schema migration."""
    __tablename__ = "session_user_votes"
    __table_args__ = (UniqueConstraint("session_id", "user_id", name="uq_session_user_votes"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    votes_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PollTemplate(Base):
    """Represents a template for an option set that users can save and edit."""
    __tablename__ = "poll_templates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    can_be_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PollTemplatePublished(Base):
    """Represents a published template available to all users in the public library."""
    __tablename__ = "poll_templates_publish"

    id = Column(Integer, primary_key=True, index=True)
    original_poll_id = Column(Integer, ForeignKey("poll_templates.id"), index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PollTemplateOption(Base):
    """Option item that belongs to a saved template or published template."""
    __tablename__ = "poll_template_options"

    id = Column(Integer, primary_key=True, index=False)
    template_id = Column(Integer, ForeignKey("poll_templates.id"))
    text = Column(String)
    image_path = Column(String, nullable=True)


class PollTemplatePublishedOption(Base):
    """Option item for a published template, containing text and optional image metadata."""
    __tablename__ = "poll_templates_publish_options"

    id = Column(Integer, primary_key=True, index=False)
    published_template_id = Column(Integer, ForeignKey("poll_templates_publish.id"))
    text = Column(String)
    image_path = Column(String, nullable=True)