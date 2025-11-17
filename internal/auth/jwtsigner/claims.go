package jwtsigner

import "github.com/golang-jwt/jwt/v5"

type accessClaims struct {
	jwt.RegisteredClaims
	SessionID string `json:"sid"`
}
