package handlers

import (
	"errors"
	"fmt"
	"net/http"

	"github.com/Mozlook/MoneyControlBackend/internal/http/validate"
	"github.com/Mozlook/MoneyControlBackend/internal/repos/sqldb"
	services "github.com/Mozlook/MoneyControlBackend/internal/services/auth"
	"github.com/Mozlook/MoneyControlBackend/pkg/models"
	"github.com/gin-gonic/gin"
)

var registerFunc = services.Register

func (h *AuthHandlers) Register() gin.HandlerFunc {
	return func(c *gin.Context) {
		var requestData models.RegisterRequest
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
		if err = validate.ValidatePassword(requestData.Password); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		normalizedTimezone, err := validate.ValidateTimezone(requestData.Timezone)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		normalizedHomeCurrency, err := validate.ValidateHomeCurrency(requestData.HomeCurrency)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}
		if err = validate.ValidatePeriodAnchorDay(requestData.PeriodAnchorDay); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "validation error"})
			return
		}

		registerInput := models.RegisterInput{
			Email:           normalizedEmail,
			PlainPassword:   requestData.Password,
			Timezone:        normalizedTimezone,
			HomeCurrency:    normalizedHomeCurrency,
			PeriodAnchorDay: requestData.PeriodAnchorDay,
		}

		store, err := sqldb.NewSQLRepos(h.DB)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "internal"})
			return
		}
		user, err := registerFunc(c.Request.Context(), store, &h.PwdCfg, registerInput)
		if err != nil {
			if errors.Is(err, services.ErrEmailTaken) {
				c.JSON(http.StatusConflict, gin.H{"code": "email_taken", "message": "Email already registered"})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{"error": "internal"})
			return
		}
		c.Header("Location", fmt.Sprintf("/api/v1/users/%s", user.ID.String()))
		resp := models.RegisterResponse{
			UserID:          user.ID.String(),
			Email:           user.Email,
			Timezone:        user.Timezone,
			PeriodAnchorDay: user.PeriodAnchorDay,
			HomeCurrency:    user.HomeCurrency,
		}
		c.JSON(http.StatusCreated, resp)
	}
}
