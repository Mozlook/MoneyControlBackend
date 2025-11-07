package models

import (
	"time"

	"github.com/google/uuid"
)

type User struct {
	ID              uuid.UUID `json:"id"`
	Email           string    `json:"email"`
	Timezone        string    `json:"timezone"`
	HomeCurrency    string    `json:"home_currency"`
	PeriodAnchorDay int       `json:"period_anchor_day"`
	CreatedAt       time.Time `json:"created_at"`
}

type UserPassword struct {
	UserID    uuid.UUID `json:"-"`
	Hash      string    `json:"-"`
	CreatedAt time.Time `json:"-"`
}

type RegisterInput struct {
	Email           string
	PlainPassword   string
	Timezone        string
	HomeCurrency    string
	PeriodAnchorDay int
}
