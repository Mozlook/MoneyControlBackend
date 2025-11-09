package services

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgconn"

	"github.com/Mozlook/MoneyControlBackend/internal/auth/password"
	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	"github.com/Mozlook/MoneyControlBackend/internal/repos"
	"github.com/Mozlook/MoneyControlBackend/pkg/models"
)

var (
	ErrEmailTaken = errors.New("email_taken")
	hashFunc      = password.Hash
)

func Register(ctx context.Context, repos repos.Repos, argon2Cfg *appcfg.Argon2, input models.RegisterInput) (models.User, error) {
	phc, err := hashFunc(input.PlainPassword, *argon2Cfg)
	if err != nil {
		return models.User{}, err
	}

	now := time.Now().UTC()

	user := models.User{
		ID:              uuid.New(),
		Email:           input.Email,
		Timezone:        input.Timezone,
		HomeCurrency:    input.HomeCurrency,
		PeriodAnchorDay: input.PeriodAnchorDay,
		CreatedAt:       now,
	}

	userPwd := models.UserPassword{
		UserID:    user.ID,
		Hash:      phc,
		CreatedAt: now,
	}

	tx, err := repos.BeginTx(ctx)
	if err != nil {
		return models.User{}, err
	}
	defer tx.Rollback(ctx)

	if err := repos.Users(tx).Insert(ctx, &user); err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == "23505" {
			return models.User{}, ErrEmailTaken
		}
		return models.User{}, err
	}

	if err := repos.Passwords(tx).Insert(ctx, &userPwd); err != nil {
		return models.User{}, err
	}

	if err := tx.Commit(ctx); err != nil {
		return models.User{}, err
	}

	return user, nil
}
