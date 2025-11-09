package models

import (
	"time"

	"github.com/google/uuid"
)

type Session struct {
	ID               uuid.UUID  `json:"id"`
	UserID           uuid.UUID  `json:"user_id"`
	RefreshTokenHash string     `json:"-"`
	CreatedAt        time.Time  `json:"created_at"`
	ExpiresAt        time.Time  `json:"expires_at"`
	RevokedAt        *time.Time `json:"revoked_at"`
	UserAgent        string     `json:"user_agent"`
	IP               string     `json:"ip"`
}
