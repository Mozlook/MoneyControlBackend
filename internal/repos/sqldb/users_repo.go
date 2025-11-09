package sqldb

import (
	"context"
	"database/sql"

	"github.com/Mozlook/MoneyControlBackend/pkg/models"
)

type SQLUsersRepo struct {
	Tx *sql.Tx
}

func (r *SQLUsersRepo) Insert(ctx context.Context, u *models.User) error {
	_, err := r.Tx.ExecContext(ctx, "INSERT INTO users (id, email, timezone, period_anchor_day, home_currency) VALUES ($1, $2, $3, $4, $5)", u.ID, u.Email, u.Timezone, u.PeriodAnchorDay, u.HomeCurrency)
	return err
}

func (r *SQLUsersRepo) FindByEmail(ctx context.Context, email string) (models.User, error) {
	var user models.User
	row := r.Tx.QueryRowContext(ctx, "SELECT id, email, timezone, period_anchor_day, home_currency, created_at FROM users WHERE email = $1", email)

	if err := row.Scan(&user.ID, &user.Email, &user.Timezone, &user.PeriodAnchorDay, &user.HomeCurrency, &user.CreatedAt); err != nil {
		return models.User{}, err
	}

	return user, nil
}
