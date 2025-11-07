package sqldb

import (
	"context"
	"database/sql"

	"github.com/Mozlook/MoneyControlBackend/pkg/models"
)

type SQLPasswordsRepo struct {
	Tx *sql.Tx
}

func (r *SQLPasswordsRepo) Insert(ctx context.Context, up *models.UserPassword) error {
	_, err := r.Tx.ExecContext(ctx, "INSERT INTO user_passwords (user_id, password_hash) VALUES ($1, $2)", up.UserID, up.Hash)
	return err
}
