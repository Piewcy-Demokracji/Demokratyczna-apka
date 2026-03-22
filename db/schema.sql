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
    "set_options" ADD CONSTRAINT "set_options_set_id_foreign" FOREIGN KEY("set_id") REFERENCES "sets"("id");
ALTER TABLE
    "sets" ADD CONSTRAINT "sets_user_id_foreign" FOREIGN KEY("user_id") REFERENCES "users"("id");
ALTER TABLE
    "votes" ADD CONSTRAINT "votes_pool_id_foreign" FOREIGN KEY("pool_id") REFERENCES "pools"("id");
ALTER TABLE
    "pools" ADD CONSTRAINT "pools_set_id_foreign" FOREIGN KEY("set_id") REFERENCES "sets"("id");
ALTER TABLE
    "votes" ADD CONSTRAINT "votes_id_foreign" FOREIGN KEY("id") REFERENCES "pool_options"("id");
ALTER TABLE
    "votes" ADD CONSTRAINT "votes_user_id_foreign" FOREIGN KEY("user_id") REFERENCES "users"("id");