package handlers

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	"github.com/Mozlook/MoneyControlBackend/internal/repos"
	sqldb "github.com/Mozlook/MoneyControlBackend/internal/repos/sqldb"
	services "github.com/Mozlook/MoneyControlBackend/internal/services/auth"
	"github.com/Mozlook/MoneyControlBackend/pkg/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func setupRouterForTests(h *AuthHandlers) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.POST("/api/v1/auth/register", h.Register())
	return r
}

func TestRegister_MalformedJSON_Returns400(t *testing.T) {
	old := registerFunc
	registerFunc = func(ctx context.Context, r repos.Repos, cfg *appcfg.Argon2, in models.RegisterInput) (models.User, error) {
		return models.User{}, nil
	}
	t.Cleanup(func() { registerFunc = old })

	h := NewAuthHandlers(&sql.DB{}, appcfg.Argon2{})
	router := setupRouterForTests(h)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewBufferString("{bad json"))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("want 400, got %d body=%s", w.Code, w.Body.String())
	}
}

func TestRegister_InvalidEmail_Returns400(t *testing.T) {
	old := registerFunc
	registerFunc = func(ctx context.Context, r repos.Repos, cfg *appcfg.Argon2, in models.RegisterInput) (models.User, error) {
		return models.User{}, nil
	}
	t.Cleanup(func() { registerFunc = old })

	h := NewAuthHandlers(&sql.DB{}, appcfg.Argon2{})
	router := setupRouterForTests(h)

	body := map[string]any{
		"email":             "not-an-email",
		"password":          "VeryStrong1!",
		"timezone":          "Europe/Warsaw",
		"home_currency":     "PLN",
		"period_anchor_day": 15,
	}
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewBuffer(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("want 400, got %d body=%s", w.Code, w.Body.String())
	}
}

func TestRegister_EmailTaken_Returns409(t *testing.T) {
	old := registerFunc
	registerFunc = func(ctx context.Context, _ repos.Repos, _ *appcfg.Argon2, _ models.RegisterInput) (models.User, error) {
		return models.User{}, services.ErrEmailTaken
	}
	t.Cleanup(func() { registerFunc = old })

	h := NewAuthHandlers(&sql.DB{}, appcfg.Argon2{})
	router := setupRouterForTests(h)

	body := map[string]any{
		"email":             "user@example.com",
		"password":          "VeryStrong1!",
		"timezone":          "Europe/Warsaw",
		"home_currency":     "PLN",
		"period_anchor_day": 10,
	}
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewBuffer(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusConflict {
		t.Fatalf("want 409, got %d body=%s", w.Code, w.Body.String())
	}
}

func TestRegister_Success_Returns201AndLocation(t *testing.T) {
	uid := uuid.New()

	old := registerFunc
	registerFunc = func(ctx context.Context, _ repos.Repos, _ *appcfg.Argon2, in models.RegisterInput) (models.User, error) {
		return models.User{
			ID:              uid,
			Email:           in.Email,
			Timezone:        in.Timezone,
			HomeCurrency:    in.HomeCurrency,
			PeriodAnchorDay: in.PeriodAnchorDay,
		}, nil
	}
	t.Cleanup(func() { registerFunc = old })

	h := NewAuthHandlers(&sql.DB{}, appcfg.Argon2{})
	router := setupRouterForTests(h)

	body := map[string]any{
		"email":             "User@Example.com",
		"password":          "VeryStrong1!",
		"timezone":          "Europe/Warsaw",
		"home_currency":     "PLN",
		"period_anchor_day": 20,
	}
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewBuffer(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("want 201, got %d body=%s", w.Code, w.Body.String())
	}
	loc := w.Header().Get("Location")
	wantLoc := fmt.Sprintf("/api/v1/users/%s", uid.String())
	if loc != wantLoc {
		t.Fatalf("Location header mismatch: want %q, got %q", wantLoc, loc)
	}

	var resp models.RegisterResponse
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("invalid JSON body: %v", err)
	}
	if resp.UserID != uid.String() || resp.Email == "" || resp.Timezone == "" || resp.HomeCurrency == "" {
		t.Fatalf("unexpected response payload: %+v", resp)
	}
}

var (
	_ = sqldb.NewSQLRepos
	_ repos.Repos
)
