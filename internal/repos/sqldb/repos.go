package sqldb

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/Mozlook/MoneyControlBackend/internal/repos"
)

type SQLRepos struct {
	DB *sql.DB
}

func NewSQLRepos(db *sql.DB) (repos.Repos, error) {
	if db == nil {
		return nil, fmt.Errorf("NewSQLRepos: nil *sql.DB")
	}
	return &SQLRepos{DB: db}, nil
}

func (r *SQLRepos) BeginTx(ctx context.Context) (repos.Tx, error) {
	tx, err := r.DB.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})
	if err != nil {
		return nil, err
	}
	return &SQLTx{Tx: tx}, nil
}

func (r *SQLRepos) Users(tx repos.Tx) repos.UsersRepo {
	sqlTxWrapper, ok := tx.(*SQLTx)
	if !ok {
		panic("sqldb.Users: tx is not *sqldb.SQLTx")
	}

	return &SQLUsersRepo{Tx: sqlTxWrapper.Tx}
}

func (r *SQLRepos) Passwords(tx repos.Tx) repos.PasswordsRepo {
	sqlTxWrapper, ok := tx.(*SQLTx)
	if !ok {
		panic("sqldb.Passwords: tx is not *sqldb.SQLTx")
	}
	return &SQLPasswordsRepo{Tx: sqlTxWrapper.Tx}
}

func (r *SQLRepos) Sessions(tx repos.Tx) repos.SessionsRepo {
	sqlTxWrapper, ok := tx.(*SQLTx)
	if !ok {
		panic("sqldb.SessionRepo: tx is not *sqldb.SQLTx")
	}
	return &SQLSessionsRepo{Tx: sqlTxWrapper.Tx}
}
