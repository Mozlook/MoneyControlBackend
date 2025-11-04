-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;    -- case-insensitive text

-- Enums
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'item_importance') THEN
    CREATE TYPE item_importance AS ENUM ('WAZNY', 'NIEZBEDNY', 'NIEPOTRZEBNY');
  END IF;
END $$;

-- updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- USERS
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT UNIQUE NOT NULL,
  timezone TEXT NOT NULL,
  period_anchor_day SMALLINT NOT NULL CHECK (period_anchor_day BETWEEN 1 AND 31),
  home_currency CHAR(3) NOT NULL DEFAULT 'PLN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- OAUTH IDENTITIES
CREATE TABLE IF NOT EXISTS oauth_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  subject TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS oauth_identities_provider_subject_key
  ON oauth_identities (provider, subject);

-- CATEGORIES
CREATE TABLE IF NOT EXISTS categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  archived_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS categories_user_name_unique
  ON categories (user_id, lower(name));

CREATE UNIQUE INDEX IF NOT EXISTS categories_user_id_id_unique
  ON categories (user_id, id);

CREATE INDEX IF NOT EXISTS categories_active_idx
  ON categories (user_id, lower(name))
  WHERE archived_at IS NULL;
CREATE TRIGGER categories_set_updated_at
  BEFORE UPDATE ON categories
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ITEMS
CREATE TABLE IF NOT EXISTS items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  importance item_importance NOT NULL,
  archived_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS items_user_cat_name_unique
  ON items (user_id, category_id, lower(name));

CREATE UNIQUE INDEX IF NOT EXISTS items_user_id_id_unique
  ON items (user_id, id);

ALTER TABLE items
  ADD CONSTRAINT items_category_belongs_to_user
  FOREIGN KEY (user_id, category_id)
  REFERENCES categories (user_id, id)
  ON DELETE RESTRICT;
CREATE INDEX IF NOT EXISTS items_active_idx
  ON items (user_id, category_id)
  WHERE archived_at IS NULL;
CREATE TRIGGER items_set_updated_at
  BEFORE UPDATE ON items
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- TRANSACTIONS
CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category_id UUID NOT NULL,
  item_id UUID,
  amount_minor BIGINT NOT NULL CHECK (amount_minor <> 0),
  currency CHAR(3) NOT NULL,

  home_amount_minor BIGINT,
  home_currency CHAR(3),
  fx_rate_used NUMERIC(18,8),
  occurred_at TIMESTAMPTZ NOT NULL,
  note TEXT,
  reversed_of UUID REFERENCES transactions(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE transactions
  ADD CONSTRAINT transactions_category_fk
  FOREIGN KEY (user_id, category_id)
  REFERENCES categories (user_id, id)
  ON DELETE RESTRICT;

ALTER TABLE transactions
  ADD CONSTRAINT transactions_item_fk
  FOREIGN KEY (user_id, item_id)
  REFERENCES items (user_id, id)
  ON DELETE RESTRICT;

CREATE UNIQUE INDEX IF NOT EXISTS transactions_reversed_of_unique
  ON transactions (reversed_of) WHERE reversed_of IS NOT NULL;

CREATE INDEX IF NOT EXISTS transactions_user_occurred_idx
  ON transactions (user_id, occurred_at);
CREATE INDEX IF NOT EXISTS transactions_user_category_occurred_idx
  ON transactions (user_id, category_id, occurred_at);
CREATE INDEX IF NOT EXISTS transactions_user_item_occurred_idx
  ON transactions (user_id, item_id, occurred_at);

ALTER TABLE transactions
  ADD CONSTRAINT transactions_home_values_consistency CHECK (
    (home_amount_minor IS NULL AND home_currency IS NULL AND fx_rate_used IS NULL) OR
    (home_amount_minor IS NOT NULL AND home_currency IS NOT NULL AND fx_rate_used IS NOT NULL)
  );

