#!/usr/bin/env python3
"""
Migration script: Convert old session schema to unified JSON schema.

Usage:
    python migrate_sessions.py

This script:
1. Connects to the database
2. Finds all sessions with old relational data (polls, participants, votes)
3. Consolidates them into the new session_data and responses_data JSON columns
4. Marks all entries with created_from: "legacy" for audit
5. Reports summary statistics

Run this ONCE after deploying the new schema columns.
Subsequent sessions are created directly in the new format.
"""

import json
from datetime import datetime
from app.core.database import SessionLocal
from app.models.user import (
    Session as SessionModel,
    Poll,
    PollOption,
    Vote,
    SessionParticipant,
    SessionUserVotes,
    User,
)


def migrate_sessions_to_json():
    """Migrate all sessions from old relational schema to unified JSON."""
    db = SessionLocal()
    migrated_count = 0
    skipped_count = 0
    error_count = 0

    try:
        sessions = db.query(SessionModel).all()
        
        for session_row in sessions:
            try:
                session_data = session_row.session_data if isinstance(session_row.session_data, dict) else {}
                responses_data = session_row.responses_data if isinstance(session_row.responses_data, dict) else {}

                if session_data.get("poll") and responses_data.get("users"):
                    skipped_count += 1
                    continue

                poll = db.query(Poll).filter(Poll.session_id == session_row.id).first()
                if poll:
                    poll_options = db.query(PollOption).filter(PollOption.poll_id == poll.id).all()
                    option_rows = []
                    aggregates = {}

                    for option in poll_options:
                        option_key = str(option.id)
                        votes = db.query(Vote).filter(Vote.option_id == option.id).all()
                        rating_count = len(votes)
                        total_rating = sum(vote.rating for vote in votes) if votes else 0
                        option_rows.append(
                            {
                                "id": option.id,
                                "option_key": option_key,
                                "text": option.text,
                                "image_path": option.image_path,
                                "created_from": "legacy",
                            }
                        )
                        aggregates[option_key] = {
                            "rating_count": rating_count,
                            "total_rating": total_rating,
                        }

                    poll_payload = {
                        "title": poll.title,
                        "description": poll.description,
                        "template_id": None,
                        "duration_seconds": poll.duration_seconds,
                        "start_time": poll.start_time,
                        "voting_mode": getattr(poll, "voting_mode", "stars"),
                        "options": option_rows,
                    }
                    session_data = {
                        "schema_version": 1,
                        "host": {
                            "host_user_id": None,
                            "host_username": session_row.host_username,
                        },
                        "poll": poll_payload,
                    }

                users = {}
                participant_rows = db.query(SessionParticipant).filter(SessionParticipant.session_id == session_row.id).all()
                for participant in participant_rows:
                    user = db.query(User).filter(User.username == participant.username).first()
                    if not user:
                        continue
                    users[str(user.id)] = {
                        "username": user.username,
                        "joined_at": int(participant.joined_at.timestamp()) if participant.joined_at else None,
                        "left_at": None,
                        "active": True,
                        "votes": {},
                        "updated_at": int(participant.joined_at.timestamp()) if participant.joined_at else None,
                    }

                vote_rows = db.query(SessionUserVotes).filter(SessionUserVotes.session_id == session_row.id).all()
                for vote_row in vote_rows:
                    user = db.query(User).filter(User.id == vote_row.user_id).first()
                    if not user:
                        continue
                    vote_payload = {}
                    if isinstance(vote_row.votes_json, dict):
                        vote_payload = vote_row.votes_json
                    elif isinstance(vote_row.votes_json, str) and vote_row.votes_json.strip():
                        try:
                            loaded_votes = json.loads(vote_row.votes_json)
                            if isinstance(loaded_votes, dict):
                                vote_payload = loaded_votes
                        except json.JSONDecodeError:
                            vote_payload = {}

                    user_entry = users.get(str(user.id), {
                        "username": user.username,
                        "joined_at": None,
                        "left_at": None,
                        "active": True,
                        "votes": {},
                        "updated_at": None,
                    })
                    votes_map = user_entry.get("votes", {}) if isinstance(user_entry.get("votes", {}), dict) else {}
                    votes_map.update(vote_payload if isinstance(vote_payload, dict) else {})
                    user_entry["votes"] = votes_map
                    users[str(user.id)] = user_entry

                if not responses_data.get("aggregates"):
                    responses_data["aggregates"] = aggregates
                if not responses_data.get("users"):
                    responses_data["users"] = users

                session_row.session_data = session_data or session_row.session_data or {}
                session_row.responses_data = responses_data or session_row.responses_data or {}
                session_row.updated_at = session_row.updated_at or session_row.created_at
                db.add(session_row)

                migrated_count += 1

            except Exception as e:
                print(f"Error migrating session {session_row.id}: {e}")
                error_count += 1
                continue

        db.commit()
        print(f"\n✓ Migration complete!")
        print(f"  Migrated: {migrated_count}")
        print(f"  Skipped (already in new format): {skipped_count}")
        print(f"  Errors: {error_count}")

    except Exception as e:
        print(f"Fatal migration error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting session migration from old relational schema to unified JSON schema...")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    migrate_sessions_to_json()
