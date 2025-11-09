package sqldb

import (
	"context"
	"database/sql"

	"github.com/Mozlook/MoneyControlBackend/pkg/models"
)

type SQLSessionsRepo struct {
	Tx *sql.Tx
}

func (r *SQLSessionsRepo) Insert(ctx context.Context, s *models.Session) error {
	_, err := r.Tx.ExecContext(ctx, "INSERT INTO sessions (id, user_id, refresh_token_hash, expires_at, user_agent,ip) VALUES ($1,$2,$3,$4,$5,$6)", s.ID, s.UserID, s.RefreshTokenHash, s.ExpiresAt, s.ExpiresAt, s.UserAgent, s.IP)
	return err
}
