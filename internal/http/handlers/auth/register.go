package handlers

import (
	"database/sql"
	"net/http"

	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	"github.com/Mozlook/MoneyControlBackend/internal/http/validate"
	"github.com/Mozlook/MoneyControlBackend/pkg/models"
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
		var requestData models.RegisterRequest
		err := c.ShouldBindJSON(&requestData)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}

		if normalizedEmail, err := validate.ValidateEmail(requestData.Email); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		if err = validate.ValidatePassword(requestData.Password); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		if normalizedTimezone, err := validate.ValidateTimezone(requestData.Timezone); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		if normalizedHomeCurrency, err := validate.ValidateHomeCurrency(requestData.HomeCurrency); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		if err = validate.ValidatePeriodAnchorDay(requestData.PeriodAnchorDay); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"Location": "jeszcze nie mam"})
	}
}
