# Unified Session Data Format (JSON)

## Overview
Starting from the refactored architecture, each session is stored as a single row in the `sessions` table with two main JSON columns:
- `session_data` - immutable snapshot of poll and session metadata
- `responses_data` - mutable user responses and aggregate statistics

All timestamps are stored as Unix timestamps (seconds since epoch) for consistency.

## session_data (JSONB)

Immutable snapshot captured at session creation time.

```json
{
  "schema_version": 1,
  "host": {
    "host_user_id": 1,
    "host_username": "john_doe"
  },
  "poll": {
    "title": "Best coffee shop nearby",
    "description": "Rate coffee places from 0-5",
    "template_id": null,
    "duration_seconds": 180,
    "start_time": 1715428800,
    "voting_mode": "stars",
    "options": [
      {
        "id": 1,
        "option_key": "1",
        "text": "Coffee House A",
        "image_path": "/uploads/coffee_a.jpg",
        "created_from": "custom"
      },
      {
        "id": 2,
        "option_key": "2",
        "text": "Coffee House B",
        "image_path": "/uploads/coffee_b.jpg",
        "created_from": "template"
      }
    ]
  }
}
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| schema_version | int | Version of JSON schema for migrations (currently 1) |
| host.host_user_id | int | Database user ID of session host |
| host.host_username | str | Username of session host (snapshot) |
| poll.title | str | Poll title |
| poll.description | str | Poll description |
| poll.template_id | int \| null | Reference to template if session created from one |
| poll.duration_seconds | int | Total duration of voting in seconds |
| poll.start_time | int | Unix timestamp when poll started |
| poll.voting_mode | str | "stars" (1-5 rating) or "single" (one choice) |
| poll.options[] | array | Array of poll options |
| option.id | int | Sequential numeric ID for option (1-based) |
| option.option_key | str | Stable string key for option (maps votes to options) |
| option.text | str | Display text of option |
| option.image_path | str \| null | Path to optional option image |
| option.created_from | str | "custom", "template", or "legacy" |

---

## responses_data (JSONB)

Mutable data tracking user participation and voting.

```json
{
  "users": {
    "1": {
      "username": "john_doe",
      "joined_at": 1715428800,
      "left_at": null,
      "active": true,
      "votes": {
        "1": 5,
        "2": 4
      },
      "updated_at": 1715428850
    },
    "2": {
      "username": "jane_smith",
      "joined_at": 1715428805,
      "left_at": null,
      "active": true,
      "votes": {
        "1": 3,
        "2": 5
      },
      "updated_at": 1715428860
    }
  },
  "aggregates": {
    "1": {
      "rating_count": 2,
      "total_rating": 8
    },
    "2": {
      "rating_count": 2,
      "total_rating": 9
    }
  }
}
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| users | dict | Users indexed by user_id (string key) |
| users[user_id].username | str | Username snapshot at join time |
| users[user_id].joined_at | int | Unix timestamp when user joined session |
| users[user_id].left_at | int \| null | Unix timestamp when user left (null if still active) |
| users[user_id].active | bool | Whether user is currently in session |
| users[user_id].votes | dict | User's votes: option_key -> rating (0-5) |
| users[user_id].updated_at | int | Unix timestamp of last vote/status change |
| aggregates | dict | Per-option statistics indexed by option_key |
| aggregates[option_key].rating_count | int | Number of votes for this option |
| aggregates[option_key].total_rating | int | Sum of all ratings for this option |

### Usage Notes

- **user_id is the stable key**: User entries are keyed by numeric user ID for stability across username changes
- **option_key stability**: The `option_key` in poll options MUST match the keys in aggregates and votes
- **Backward compatibility**: Legacy data migrated from old tables may have `created_from: "legacy"`
- **Single-choice votes**: In "single" voting_mode, user.votes contains only one entry with value 1
- **Vote tracking**: Votes are only added to aggregates when rating > 0; rating == 0 removes the vote
- **Active status**: `active: false` and `left_at` set when user leaves, but entry remains for audit trail

---

## sessions Table Metadata Columns

| Column | Type | Purpose |
|--------|------|---------|
| id | int | Primary key |
| token | varchar(36) | UUID token for accessing session (UNIQUE, indexed) |
| code | varchar(6) | 6-char alphanumeric code for joining (UNIQUE, indexed) |
| host_username | varchar | Denormalized host username for quick lookup |
| status | varchar(20) | ACTIVE, ENDED, or DELETED (indexed) |
| version | int | Optimistic lock counter for concurrency control |
| session_data | jsonb | Immutable poll snapshot |
| responses_data | jsonb | Mutable user responses |
| created_at | timestamp | Session creation time |
| updated_at | timestamp | Last update time (indexed) |
| ended_at | timestamp | When session ended (null if active) |
| deleted_at | timestamp | When session was deleted (soft delete) |

---

## Migration Strategy

When upgrading from the old relational schema to this unified format:

1. Old `polls` table data → new `session_data.poll`
2. Old `poll_options` → new `session_data.poll.options[]`
3. Old `session_participants` → new `responses_data.users[]` with `joined_at`
4. Old `session_user_votes` (votes_json) → new `responses_data.users[].votes`
5. Computed aggregates from `votes` table → new `responses_data.aggregates`

All legacy records are marked with `created_from: "legacy"` for audit purposes.
