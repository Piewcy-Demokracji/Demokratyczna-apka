CREATE TABLE "users"(
    "id" BIGINT NOT NULL,
    "password" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "nick" TEXT NOT NULL
);
ALTER TABLE
    "users" ADD PRIMARY KEY("id");
CREATE TABLE "pools"(
    "id" BIGINT NOT NULL,
    "set_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "deadline" TIMESTAMP(0) WITHOUT TIME ZONE NOT NULL,
    "active" BOOLEAN NOT NULL
);
ALTER TABLE
    "pools" ADD PRIMARY KEY("id");
CREATE TABLE "sets"(
    "id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "user_id" BIGINT NOT NULL
);
ALTER TABLE
    "sets" ADD PRIMARY KEY("id");
CREATE TABLE "set_options"(
    "id" BIGINT NOT NULL,
    "set_id" BIGINT NOT NULL,
    "text" TEXT NOT NULL,
    "image" TEXT NOT NULL
);
ALTER TABLE
    "set_options" ADD PRIMARY KEY("id");
CREATE TABLE "votes"(
    "id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "pool_id" BIGINT NOT NULL,
    "pool_option_id" BIGINT NOT NULL,
    "vote_value" BOOLEAN NOT NULL
);
ALTER TABLE
    "votes" ADD PRIMARY KEY("id");
CREATE TABLE "pool_options"(
    "id" BIGINT NOT NULL,
    "pool_id" BIGINT NOT NULL,
    "set_option_id" BIGINT NOT NULL,
    "text" TEXT NOT NULL,
    "image" TEXT NOT NULL,
    "active" BOOLEAN NOT NULL,
    "yes_votes" BIGINT NOT NULL,
    "no_votes" BIGINT NOT NULL
);
ALTER TABLE
    "pool_options" ADD PRIMARY KEY("id");
ALTER TABLE
    "pool_options" ADD CONSTRAINT "pool_options_set_option_id_foreign" FOREIGN KEY("set_option_id") REFERENCES "set_options"("id");
ALTER TABLE
    "pool_options" ADD CONSTRAINT "pool_options_pool_id_foreign" FOREIGN KEY("pool_id") REFERENCES "pools"("id");
ALTER TABLE
    "votes" ADD CONSTRAINT "votes_pool_option_id_foreign" FOREIGN KEY("pool_option_id") REFERENCES "pool_options"("id");
ALTER TABLE
    "set_options" ADD CONSTRAINT "set_options_set_id_foreign" FOREIGN KEY("set_id") REFERENCES "sets"("id");
ALTER TABLE
    "sets" ADD CONSTRAINT "sets_user_id_foreign" FOREIGN KEY("user_id") REFERENCES "users"("id");
ALTER TABLE
    "votes" ADD CONSTRAINT "votes_pool_id_foreign" FOREIGN KEY("pool_id") REFERENCES "pools"("id");
ALTER TABLE
    "pools" ADD CONSTRAINT "pools_set_id_foreign" FOREIGN KEY("set_id") REFERENCES "sets"("id");
ALTER TABLE
    "votes" ADD CONSTRAINT "votes_user_id_foreign" FOREIGN KEY("user_id") REFERENCES "users"("id");

CREATE OR REPLACE FUNCTION update_vote_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF NEW.vote_value = true THEN
            UPDATE "pool_options" SET "yes_votes" = "yes_votes" + 1 WHERE "id" = NEW."pool_option_id";
        ELSE
            UPDATE "pool_options" SET "no_votes" = "no_votes" + 1 WHERE "id" = NEW."pool_option_id";
        END IF;
        RETURN NEW;
        
    ELSIF (TG_OP = 'UPDATE') THEN
        IF OLD.vote_value != NEW.vote_value THEN
            IF NEW.vote_value = true THEN
                UPDATE "pool_options" SET "yes_votes" = "yes_votes" + 1, "no_votes" = "no_votes" - 1 WHERE "id" = NEW."pool_option_id";
            ELSE
                UPDATE "pool_options" SET "yes_votes" = "yes_votes" - 1, "no_votes" = "no_votes" + 1 WHERE "id" = NEW."pool_option_id";
            END IF;
        END IF;
        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        IF OLD.vote_value = true THEN
            UPDATE "pool_options" SET "yes_votes" = "yes_votes" - 1 WHERE "id" = OLD."pool_option_id";
        ELSE
            UPDATE "pool_options" SET "no_votes" = "no_votes" - 1 WHERE "id" = OLD."pool_option_id";
        END IF;
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_vote_changes
AFTER INSERT OR UPDATE OR DELETE ON "votes"
FOR EACH ROW
EXECUTE FUNCTION update_vote_counts();
