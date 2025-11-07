package repos

import (
	"context"

	"github.com/Mozlook/MoneyControlBackend/pkg/models"
)

type Repos interface {
	BeginTx(ctx context.Context) (Tx, error)
	Users(tx Tx) UsersRepo
	Passwords(tx Tx) PasswordsRepo
}

type Tx interface {
	Commit(ctx context.Context) error
	Rollback(ctx context.Context) error
}

type UsersRepo interface {
	Insert(ctx context.Context, u *models.User) error
}

type PasswordsRepo interface {
	Insert(ctx context.Context, u *models.UserPassword) error
}
