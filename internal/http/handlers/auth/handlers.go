package handlers

import (
	"database/sql"
	"time"

	"github.com/Mozlook/MoneyControlBackend/internal/auth/jwtsigner"
	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
)

type AuthHandlers struct {
	DB         *sql.DB
	PwdCfg     appcfg.Argon2
	JWTSigner  jwtsigner.AccessTokenSigner
	RefreshTTL time.Duration
}

func NewAuthHandlers(db *sql.DB, pwdCfg appcfg.Argon2) *AuthHandlers {
	return &AuthHandlers{DB: db, PwdCfg: pwdCfg}
}

func (h *AuthHandlers) WithJWT(signer jwtsigner.AccessTokenSigner, refreshTTL time.Duration) *AuthHandlers {
	h.JWTSigner = signer
	h.RefreshTTL = refreshTTL
	return h
}
