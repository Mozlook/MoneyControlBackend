package services

import (
	"context"
	"errors"
	"testing"
	"time"

	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	"github.com/Mozlook/MoneyControlBackend/internal/repos"
	"github.com/Mozlook/MoneyControlBackend/pkg/models"
	"github.com/google/uuid"
	"github.com/jackc/pgconn"
)

type callLog struct{ calls []string }

func (l *callLog) add(s string) { l.calls = append(l.calls, s) }

type stubRepos struct {
	log   *callLog
	tx    *stubTx
	users *stubUsersRepo
	pwds  *stubPasswordsRepo

	beginErr error
}

func (s *stubRepos) BeginTx(ctx context.Context) (repos.Tx, error) {
	if s.log != nil {
		s.log.add("BeginTx")
	}
	if s.beginErr != nil {
		return nil, s.beginErr
	}
	return s.tx, nil
}

func (s *stubRepos) Users(tx repos.Tx) repos.UsersRepo         { return s.users }
func (s *stubRepos) Passwords(tx repos.Tx) repos.PasswordsRepo { return s.pwds }

type stubTx struct {
	log        *callLog
	commitErr  error
	committed  bool
	rolledBack bool
}

func (t *stubTx) Commit(ctx context.Context) error {
	if t.log != nil {
		t.log.add("Commit")
	}
	t.committed = true
	return t.commitErr
}

func (t *stubTx) Rollback(ctx context.Context) error {
	if t.log != nil {
		t.log.add("Rollback")
	}
	t.rolledBack = true
	return nil
}

type stubUsersRepo struct {
	log    *callLog
	err    error
	last   *models.User
	called bool
}

func (r *stubUsersRepo) Insert(ctx context.Context, u *models.User) error {
	if r.log != nil {
		r.log.add("Users.Insert")
	}
	r.called = true
	r.last = u
	return r.err
}

type stubPasswordsRepo struct {
	log    *callLog
	err    error
	last   *models.UserPassword
	called bool
}

func (r *stubPasswordsRepo) Insert(ctx context.Context, up *models.UserPassword) error {
	if r.log != nil {
		r.log.add("Passwords.Insert")
	}
	r.called = true
	r.last = up
	return r.err
}

func TestRegister_HappyPath(t *testing.T) {
	oldHash := hashFunc
	hashFunc = func(plain string, _ appcfg.Argon2) (string, error) {
		return "$argon2id$testphc", nil
	}
	t.Cleanup(func() { hashFunc = oldHash })

	log := &callLog{}
	tx := &stubTx{log: log}
	users := &stubUsersRepo{log: log}
	pwds := &stubPasswordsRepo{log: log}
	r := &stubRepos{log: log, tx: tx, users: users, pwds: pwds}

	input := models.RegisterInput{
		Email:           "user@example.com",
		PlainPassword:   "StrongPass1!",
		Timezone:        "Europe/Warsaw",
		HomeCurrency:    "PLN",
		PeriodAnchorDay: 15,
	}

	user, err := Register(context.Background(), r, &appcfg.Argon2{}, input)
	if err != nil {
		t.Fatalf("Register returned error: %v", err)
	}

	if user.Email != input.Email || user.Timezone != input.Timezone || user.HomeCurrency != input.HomeCurrency || user.PeriodAnchorDay != input.PeriodAnchorDay {
		t.Fatalf("unexpected user fields: %+v", user)
	}
	if user.ID == uuid.Nil {
		t.Fatalf("user.ID not set")
	}
	if user.CreatedAt.IsZero() {
		t.Fatalf("user.CreatedAt is zero")
	}
	if time.Since(user.CreatedAt) > time.Minute {
		t.Fatalf("user.CreatedAt too old/new: %v", user.CreatedAt)
	}

	wantOrderPrefix := []string{"BeginTx", "Users.Insert", "Passwords.Insert", "Commit"}
	for i, w := range wantOrderPrefix {
		if i >= len(log.calls) || log.calls[i] != w {
			t.Fatalf("call order mismatch at %d: want %q, got %q; full=%v", i, w, safeIdx(log.calls, i), log.calls)
		}
	}
}

func TestRegister_EmailTaken_MapsToErrEmailTaken(t *testing.T) {
	oldHash := hashFunc
	hashFunc = func(plain string, _ appcfg.Argon2) (string, error) {
		return "$argon2id$testphc", nil
	}
	t.Cleanup(func() { hashFunc = oldHash })

	log := &callLog{}
	tx := &stubTx{log: log}
	dup := &pgconn.PgError{Code: "23505", ConstraintName: "users_email_key"}
	users := &stubUsersRepo{log: log, err: dup}
	pwds := &stubPasswordsRepo{log: log}
	r := &stubRepos{log: log, tx: tx, users: users, pwds: pwds}

	_, err := Register(context.Background(), r, &appcfg.Argon2{}, models.RegisterInput{
		Email:           "dup@example.com",
		PlainPassword:   "StrongPass1!",
		Timezone:        "Europe/Warsaw",
		HomeCurrency:    "PLN",
		PeriodAnchorDay: 10,
	})
	if !errors.Is(err, ErrEmailTaken) {
		t.Fatalf("want ErrEmailTaken, got %v", err)
	}

	if pwds.called {
		t.Fatalf("Passwords.Insert should NOT be called on duplicate email")
	}
	if tx.committed {
		t.Fatalf("Commit should NOT be called on duplicate email")
	}
	if !tx.rolledBack {
		t.Fatalf("Rollback should be called on duplicate email")
	}

	want := []string{"BeginTx", "Users.Insert", "Rollback"}
	if !equalCallsPrefix(log.calls, want) {
		t.Fatalf("call order mismatch, want prefix %v, got %v", want, log.calls)
	}
}

func TestRegister_PasswordsInsertError_RollsBack(t *testing.T) {
	oldHash := hashFunc
	hashFunc = func(plain string, _ appcfg.Argon2) (string, error) {
		return "$argon2id$testphc", nil
	}
	t.Cleanup(func() { hashFunc = oldHash })

	log := &callLog{}
	tx := &stubTx{log: log}
	users := &stubUsersRepo{log: log}
	pwds := &stubPasswordsRepo{log: log, err: errors.New("boom")}
	r := &stubRepos{log: log, tx: tx, users: users, pwds: pwds}

	_, err := Register(context.Background(), r, &appcfg.Argon2{}, models.RegisterInput{
		Email:           "ok@example.com",
		PlainPassword:   "StrongPass1!",
		Timezone:        "Europe/Warsaw",
		HomeCurrency:    "PLN",
		PeriodAnchorDay: 9,
	})
	if err == nil {
		t.Fatalf("want error from Passwords.Insert, got nil")
	}
	if tx.committed {
		t.Fatalf("Commit should NOT be called on Passwords.Insert error")
	}
	if !tx.rolledBack {
		t.Fatalf("Rollback should be called on Passwords.Insert error")
	}

	want := []string{"BeginTx", "Users.Insert", "Passwords.Insert", "Rollback"}
	if !equalCallsPrefix(log.calls, want) {
		t.Fatalf("call order mismatch, want prefix %v, got %v", want, log.calls)
	}
}

func TestRegister_BeginTxError_BubblesUp(t *testing.T) {
	oldHash := hashFunc
	hashFunc = func(plain string, _ appcfg.Argon2) (string, error) {
		return "$argon2id$testphc", nil
	}
	t.Cleanup(func() { hashFunc = oldHash })

	log := &callLog{}
	tx := &stubTx{log: log}
	users := &stubUsersRepo{log: log}
	pwds := &stubPasswordsRepo{log: log}
	r := &stubRepos{log: log, tx: tx, users: users, pwds: pwds, beginErr: errors.New("no-conn")}

	_, err := Register(context.Background(), r, &appcfg.Argon2{}, models.RegisterInput{
		Email:           "a@b.c",
		PlainPassword:   "StrongPass1!",
		Timezone:        "Europe/Warsaw",
		HomeCurrency:    "PLN",
		PeriodAnchorDay: 1,
	})
	if err == nil {
		t.Fatalf("want BeginTx error, got nil")
	}
	if len(log.calls) != 1 || log.calls[0] != "BeginTx" {
		t.Fatalf("unexpected calls: %v", log.calls)
	}
}

func TestRegister_CommitError_BubblesUp(t *testing.T) {
	oldHash := hashFunc
	hashFunc = func(plain string, _ appcfg.Argon2) (string, error) {
		return "$argon2id$testphc", nil
	}
	t.Cleanup(func() { hashFunc = oldHash })

	log := &callLog{}
	tx := &stubTx{log: log, commitErr: errors.New("commit-fail")}
	users := &stubUsersRepo{log: log}
	pwds := &stubPasswordsRepo{log: log}
	r := &stubRepos{log: log, tx: tx, users: users, pwds: pwds}

	_, err := Register(context.Background(), r, &appcfg.Argon2{}, models.RegisterInput{
		Email:           "a@b.c",
		PlainPassword:   "StrongPass1!",
		Timezone:        "Europe/Warsaw",
		HomeCurrency:    "PLN",
		PeriodAnchorDay: 2,
	})
	if err == nil {
		t.Fatalf("want commit error, got nil")
	}

	wantPrefix := []string{"BeginTx", "Users.Insert", "Passwords.Insert", "Commit"}
	if !equalCallsPrefix(log.calls, wantPrefix) {
		t.Fatalf("call order mismatch, want prefix %v, got %v", wantPrefix, log.calls)
	}
}

func equalCallsPrefix(got, want []string) bool {
	if len(got) < len(want) {
		return false
	}
	for i := range want {
		if got[i] != want[i] {
			return false
		}
	}
	return true
}

func safeIdx(a []string, i int) string {
	if i < 0 || i >= len(a) {
		return "<out-of-range>"
	}
	return a[i]
}
