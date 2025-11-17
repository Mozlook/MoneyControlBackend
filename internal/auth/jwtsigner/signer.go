package jwtsigner

import (
	"crypto/rsa"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

var _ AccessTokenSigner = (*RS256Signer)(nil)

type RS256Signer struct {
	key *rsa.PrivateKey
	iss string
	aud string
	kid string
	ttl time.Duration
}

func NewRS256Signer(key *rsa.PrivateKey, iss string, aud string, kid string, ttl time.Duration) (*RS256Signer, error) {
	if key == nil {
		return nil, fmt.Errorf("key not provided")
	}

	if iss == "" {
		return nil, fmt.Errorf("issuer not provided")
	}
	if aud == "" {
		return nil, fmt.Errorf("audience not provided")
	}
	if kid == "" {
		return nil, fmt.Errorf("kid not provided")
	}
	if ttl <= 0 {
		return nil, fmt.Errorf("ttl cannot be less than 0")
	}

	return &RS256Signer{key: key, iss: iss, aud: aud, kid: kid, ttl: ttl}, nil
}

type AccessTokenSigner interface {
	SignAccess(userID uuid.UUID, sessionID uuid.UUID, now time.Time) (token string, exp time.Time, err error)
}

func (s *RS256Signer) SignAccess(userID uuid.UUID, sessionID uuid.UUID, now time.Time) (token string, exp time.Time, err error) {
	nowUTC := now.UTC()
	exp = nowUTC.Add(s.ttl)

	claims := accessClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    s.iss,
			Subject:   userID.String(),
			Audience:  jwt.ClaimStrings{s.aud},
			IssuedAt:  jwt.NewNumericDate(nowUTC),
			ExpiresAt: jwt.NewNumericDate(exp),
			ID:        uuid.New().String(),
		},
		SessionID: sessionID.String(),
	}

	t := jwt.NewWithClaims(jwt.SigningMethodRS256, &claims)
	t.Header["kid"] = s.kid
	t.Header["typ"] = "JWT"

	signed, err := t.SignedString(s.key)
	if err != nil {
		return "", time.Time{}, err
	}
	return signed, exp, nil
}
