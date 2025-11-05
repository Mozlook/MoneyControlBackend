package middleware

import (
	"database/sql"
	"strings"

	"github.com/Mozlook/MoneyControlBackend/internal/auth/jwtverifier"
	"github.com/gin-gonic/gin"
)

func RequireAuth(ver *jwtverifier.Verifier, db *sql.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		auth := c.GetHeader("Autorization")
		if auth == "" || !strings.HasPrefix(auth, "Bearer ") {
			c.Header("WWW-Authenticate", `Bearer error="invalid_token", error_description="missing or malformed Authorization header"`)
			c.AbortWithStatus(401)
			return
		}
		tokenStr := strings.TrimSpace(auth[len("Bearer "):])
		if tokenStr == "" {
			c.Header("WWW-Authenticate", `Bearer error="invalid_token", error_description="empty token"`)
			c.AbortWithStatus(401)
			return
		}

		claims, err := ver.Verify(tokenStr)
		if err != nil {
			c.Header("WWW-Authenticate", `Bearer error="invalid_token"`)
			c.AbortWithStatus(401)
			return
		}

		c.Set("user_id", claims.Subject)
		if claims.Email != "" {
			c.Set("user_email", claims.Email)
		}
		c.Next()
	}
}
