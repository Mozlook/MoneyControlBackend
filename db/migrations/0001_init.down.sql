-- drop in reverse dependency order
DROP INDEX IF EXISTS transactions_user_item_occurred_idx;
DROP INDEX IF EXISTS transactions_user_category_occurred_idx;
DROP INDEX IF EXISTS transactions_user_occurred_idx;
DROP INDEX IF EXISTS transactions_reversed_of_unique;
DROP TABLE IF EXISTS transactions;

DROP TRIGGER IF EXISTS items_set_updated_at ON items;
DROP INDEX IF EXISTS items_active_idx;
DROP INDEX IF EXISTS items_user_id_id_unique;
DROP INDEX IF EXISTS items_user_cat_name_unique;
ALTER TABLE IF EXISTS items DROP CONSTRAINT IF EXISTS items_category_belongs_to_user;
DROP TABLE IF EXISTS items;

DROP TRIGGER IF EXISTS categories_set_updated_at ON categories;
DROP INDEX IF EXISTS categories_active_idx;
DROP INDEX IF EXISTS categories_user_id_id_unique;
DROP INDEX IF EXISTS categories_user_name_unique;
DROP TABLE IF EXISTS categories;

DROP INDEX IF EXISTS oauth_identities_provider_subject_key;
DROP TABLE IF EXISTS oauth_identities;

DROP TABLE IF EXISTS users;

DROP FUNCTION IF EXISTS set_updated_at;
DROP TYPE IF EXISTS item_importance;
