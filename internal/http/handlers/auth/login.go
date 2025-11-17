package handlers

import (
	"errors"
	"net/http"
	"time"

	"github.com/Mozlook/MoneyControlBackend/internal/http/validate"
	"github.com/Mozlook/MoneyControlBackend/internal/repos/sqldb"
	services "github.com/Mozlook/MoneyControlBackend/internal/services/auth"
	"github.com/Mozlook/MoneyControlBackend/pkg/models"
	"github.com/gin-gonic/gin"
)

var loginFunc = services.Login

func (h *AuthHandlers) Login() gin.HandlerFunc {
	return func(c *gin.Context) {
		if h.JWTSigner == nil || h.RefreshTTL <= 0 {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "auth_not_configured"})
			return
		}

		var requestData models.LoginRequest
		err := c.ShouldBindJSON(&requestData)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}

		normalizedEmail, err := validate.ValidateEmail(requestData.Email)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		err = validate.ValidatePassword(requestData.Password)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid_credentials"})
			return
		}

		loginInput := models.LoginInput{
			Email:         normalizedEmail,
			PlainPassword: requestData.Password,
			UserAgent:     c.Request.UserAgent(),
			IP:            c.ClientIP(),
		}
		store, err := sqldb.NewSQLRepos(h.DB)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "internal"})
			return
		}
		resp, err := loginFunc(c.Request.Context(), store, h.JWTSigner, loginInput, time.Now().UTC(), h.RefreshTTL)
		if err != nil {
			if errors.Is(err, services.ErrInvalidCredentials) {
				c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid_credentials"})
				return
			} else {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal"})
				return
			}
		}
		c.JSON(http.StatusOK, resp)
	}
}
