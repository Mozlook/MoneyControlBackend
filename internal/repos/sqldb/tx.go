package sqldb

import (
	"context"
	"database/sql"
)

type SQLTx struct{ Tx *sql.Tx }

func (t *SQLTx) Commit(ctx context.Context) error {
	_ = ctx
	return t.Tx.Commit()
}

func (t *SQLTx) Rollback(ctx context.Context) error {
	_ = ctx
	if err := t.Tx.Rollback(); err != nil && err != sql.ErrTxDone {
		return err
	}
	return nil
}
