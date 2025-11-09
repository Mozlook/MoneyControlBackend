package repos

import (
	"context"

	"github.com/Mozlook/MoneyControlBackend/pkg/models"
	"github.com/google/uuid"
)

type Repos interface {
	BeginTx(ctx context.Context) (Tx, error)
	Users(tx Tx) UsersRepo
	Passwords(tx Tx) PasswordsRepo
	Sessions(tx Tx) SessionsRepo
}

type Tx interface {
	Commit(ctx context.Context) error
	Rollback(ctx context.Context) error
}

type UsersRepo interface {
	Insert(ctx context.Context, u *models.User) error
	FindByEmail(ctx context.Context, email string) (models.User, error)
}

type PasswordsRepo interface {
	Insert(ctx context.Context, u *models.UserPassword) error
	GetHash(ctx context.Context, userID uuid.UUID) (string, error)
}

type SessionsRepo interface {
	Insert(ctx context.Context, s *models.Session) error
}
