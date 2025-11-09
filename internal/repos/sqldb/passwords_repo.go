package sqldb

import (
	"context"
	"database/sql"

	"github.com/Mozlook/MoneyControlBackend/internal/repos"
	"github.com/Mozlook/MoneyControlBackend/pkg/models"
	"github.com/google/uuid"
)

var _ repos.PasswordsRepo = (*SQLPasswordsRepo)(nil)

type SQLPasswordsRepo struct {
	Tx *sql.Tx
}

func (r *SQLPasswordsRepo) Insert(ctx context.Context, up *models.UserPassword) error {
	_, err := r.Tx.ExecContext(ctx, "INSERT INTO user_passwords (user_id, password_hash) VALUES ($1, $2)", up.UserID, up.Hash)
	return err
}

func (r *SQLPasswordsRepo) GetHash(ctx context.Context, userID uuid.UUID) (string, error) {
	var hash string

	row := r.Tx.QueryRowContext(ctx, "SELECT password_hash FROM user_passwords WHERE user_id = $1", &userID)

	if err := row.Scan(hash); err != nil {
		return "", err
	}
	return hash, nil
}
