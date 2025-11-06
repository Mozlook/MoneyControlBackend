package models

import "time"

type RegisterRequest struct {
	Email           string `json:"email"`
	Password        string `json:"password"`
	Timezone        string `json:"timezone"`
	PeriodAnchorDay int    `json:"period_anchor_day"`
	HomeCurrency    string `json:"home_currency"`
}

type RegisterResponse struct {
	UserID          string    `json:"user_id"`
	Email           string    `json:"email"`
	Timezone        string    `json:"timezone"`
	PeriodAnchorDay int       `json:"period_anchor_day"`
	HomeCurrency    string    `json:"home_currency"`
	CreatedAt       time.Time `json:"created_at"`
}
