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
	UserID          string `json:"user_id"`
	Email           string `json:"email"`
	Timezone        string `json:"timezone"`
	PeriodAnchorDay int    `json:"period_anchor_day"`
	HomeCurrency    string `json:"home_currency"`
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type LoginResponse struct {
	AccessToken      string    `json:"access_token"`
	ExpiresIn        int64     `json:"expires_in"`
	TokenType        string    `json:"token_type"`
	RefreshToken     string    `json:"refresh_token"`
	RefreshExpiresAt time.Time `json:"refresh_expires_at"`
}

type LoginInput struct {
	Email         string
	PlainPassword string
	UserAgent     string
	IP            string
}
