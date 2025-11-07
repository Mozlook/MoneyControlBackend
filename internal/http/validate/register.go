package validate

import (
	"errors"
	"fmt"
	"net/mail"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

var (
	ErrEmptyEmail          = errors.New("empty email")
	ErrInvalidEmail        = errors.New("invalid email format")
	ErrEmptyPassword       = errors.New("empty password")
	ErrTooShortPassword    = errors.New("password too short")
	ErrTooLongPassword     = errors.New("password too long")
	ErrEmptyTimezone       = errors.New("empty timezone")
	ErrUnknownTimezone     = errors.New("unknown timezone")
	ErrBadAnchorDay        = errors.New("anchor day must be between 1 and 31")
	ErrEmptyCurrencyCode   = errors.New("empty currency code")
	ErrInvalidCurrencyCode = errors.New("invalid currency code")
)

var reCurrency = regexp.MustCompile(`^[A-Z]{3}$`)

func ValidateEmail(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", ErrEmptyEmail
	}
	addr, err := mail.ParseAddress(raw)
	if err != nil {
		return "", fmt.Errorf("%w: %v", ErrInvalidEmail, err)
	}

	email := strings.ToLower(addr.Address)

	return email, nil
}

func ValidatePassword(raw string) error {
	trimmedRaw := strings.TrimSpace(raw)
	if trimmedRaw == "" {
		return ErrEmptyPassword
	}

	passwordLen := utf8.RuneCountInString(raw)
	if passwordLen < 8 {
		return ErrTooShortPassword
	}

	if passwordLen > 32 {
		return ErrTooLongPassword
	}

	return nil
}

func ValidateTimezone(raw string) (string, error) {
	trimmedRaw := strings.TrimSpace(raw)
	if trimmedRaw == "" {
		return "", ErrEmptyTimezone
	}

	_, err := time.LoadLocation(trimmedRaw)
	if err != nil {
		return "", ErrUnknownTimezone
	}
	return trimmedRaw, nil
}

func ValidatePeriodAnchorDay(raw int) error {
	if raw < 1 || raw > 31 {
		return ErrBadAnchorDay
	}

	return nil
}

func ValidateHomeCurrency(raw string) (string, error) {
	trimmedRaw := strings.TrimSpace(raw)
	if trimmedRaw == "" {
		return "", ErrEmptyCurrencyCode
	}
	upper := strings.ToUpper(trimmedRaw)

	if !reCurrency.MatchString(upper) {
		return "", ErrInvalidCurrencyCode
	}
	return upper, nil
}
