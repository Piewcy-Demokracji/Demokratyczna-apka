# Session Database Migration Guide

## Overview

The application has been refactored to use a unified single-row session storage model with two JSON columns instead of multiple relational tables.

## What Changed

**Old Schema:**
- `sessions` - basic session metadata
- `session_participants` - list of who joined
- `session_user_votes` - JSON votes per user
- `polls`, `poll_options`, `votes` - full poll structure

**New Schema:**
- `sessions` with two JSON columns:
  - `session_data` - immutable snapshot of poll and options
  - `responses_data` - mutable user responses and aggregates
- Plus lifecycle columns: `status`, `version`, `updated_at`, `ended_at`, `deleted_at`

See `SESSION_DATA_FORMAT.md` for detailed JSON structure.

## Migration Steps

### 1. Deploy New Code

Pull the latest code with the new unified session model:

```bash
git pull origin main
```

### 2. Ensure Database Columns Exist

The application startup will automatically add missing columns to the `sessions` table:
- `session_data` (JSONB)
- `responses_data` (JSONB)
- `status` (VARCHAR(20))
- `version` (INTEGER)
- `updated_at` (TIMESTAMP)
- `ended_at` (TIMESTAMP)
- `deleted_at` (TIMESTAMP)

This happens during `Base.metadata.create_all()` via `ensure_unified_session_columns()` in `main.py`.

### 3. Run Data Migration (One-Time)

After deployment, run the migration script to convert old session data to new format:

```bash
# From project root
python migrate_sessions.py
```

**Output:**
```
Starting session migration from old relational schema to unified JSON schema...
Timestamp: 2026-05-11T14:30:00.000000
✓ Migration complete!
  Migrated: 42
  Skipped (already in new format): 0
  Errors: 0
```

- **Migrated**: Sessions converted from old relational tables
- **Skipped**: Sessions already in new JSON format (created after code deploy)
- **Errors**: Sessions that failed conversion (check logs for details)

### 4. Verify Migration

Check that sessions are properly loaded:

```bash
# Log in and verify session functionality in the app
# Or use the admin dashboard to inspect migrated sessions
```

### 5. Optional: Archive Old Tables

After confirming all sessions work correctly, you can optionally archive old data:

```sql
-- Backup old tables (recommended)
CREATE TABLE session_participants_backup AS SELECT * FROM session_participants;
CREATE TABLE session_user_votes_backup AS SELECT * FROM session_user_votes;
CREATE TABLE polls_backup AS SELECT * FROM polls;
CREATE TABLE poll_options_backup AS SELECT * FROM poll_options;
CREATE TABLE votes_backup AS SELECT * FROM votes;

-- Delete old data (after backup)
-- DELETE FROM votes;
-- DELETE FROM poll_options;
-- DELETE FROM polls;
-- DELETE FROM session_user_votes;
-- DELETE FROM session_participants;
```

The old tables are kept in the schema for backward compatibility, but new sessions use only the JSON columns.

## Troubleshooting

### Migration Failed

Check the detailed error message from `migrate_sessions.py`. Common issues:

1. **Database connection**: Verify `DATABASE_URL` is correct
2. **Missing columns**: Run the app startup once to create columns
3. **Data integrity**: Old votes might be malformed JSON; the script will skip those

### Sessions Not Loading

1. Check `session_data.poll` is not empty
2. Verify `responses_data.users` exists
3. Look for errors in `status` field (should be "ACTIVE", "ENDED", or "DELETED")

### Rolling Back

If you need to revert to old schema:

1. Restore database backup
2. Checkout previous code version
3. Restart application

## Performance Notes

- **Old model**: One session row + multiple participant/vote rows = N+M database rows
- **New model**: One session row with JSON = 1 database row
- **Query speed**: Faster lookups (single row), but JSON traversal overhead is minimal
- **Indexes**: Added indexes on `status`, `created_at`, `updated_at` for filtering

## What Happens to New Sessions?

Sessions created AFTER code deployment are automatically created in the new format:
- `session_data` populated directly
- `responses_data` initialized with user and aggregate structures
- No migration needed

## Questions?

Check `SESSION_DATA_FORMAT.md` for detailed JSON structure reference.
