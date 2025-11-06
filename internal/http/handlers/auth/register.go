package handlers

import (
	"database/sql"
	"net/http"

	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	"github.com/gin-gonic/gin"
)

type AuthHandlers struct {
	DB     *sql.DB
	PwdCfg appcfg.Argon2
}

func NewAuthHandlers(db *sql.DB, pwdCfg appcfg.Argon2) *AuthHandlers {
	return &AuthHandlers{DB: db, PwdCfg: pwdCfg}
}

func (h *AuthHandlers) Register() gin.HandlerFunc {
	return func(c *gin.Context) {
		// placeholder – implementacja w następnym kroku
		c.JSON(http.StatusNotImplemented, gin.H{"error": "not_implemented"})
	}
}
