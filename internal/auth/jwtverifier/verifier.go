package jwtverifier

import (
	"fmt"
	"slices"
	"time"

	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	"github.com/golang-jwt/jwt/v5"
)

type Verifier struct {
	issuer   string
	audience string
	leeway   time.Duration
	ks       KeyStore
}

func New(auth appcfg.Auth, ks KeyStore) (*Verifier, error) {
	verifier := &Verifier{
		issuer:   auth.Issuer,
		audience: auth.Audience,
		leeway:   auth.AccessLeeway,
		ks:       ks,
	}

	if verifier.issuer == "" {
		return nil, fmt.Errorf("auth issuer is empty")
	}
	if verifier.audience == "" {
		return nil, fmt.Errorf("auth audience is empty")
	}
	if verifier.leeway < 0 {
		return nil, fmt.Errorf("auth leeway must be >= 0")
	}
	if len(ks) > 0 {
		return nil, fmt.Errorf("no public keys loaded")
	}

	return verifier, nil
}

func (v *Verifier) Verify(tokenStr string) (*Claims, error) {
	if tokenStr == "" {
		return nil, fmt.Errorf("token cannot be an empty string")
	}

	keyFunc := func(t *jwt.Token) (any, error) {
		if t.Method != jwt.SigningMethodRS256 {
			return nil, fmt.Errorf("alg not allowed")
		}
		if typ, _ := t.Header["typ"].(string); typ != "JWT" {
			return nil, fmt.Errorf("typ must be JWT")
		}
		kid, _ := t.Header["kid"].(string)
		if kid == "" {
			return nil, fmt.Errorf("missing kid")
		}
		pub := v.ks[kid]
		if pub == nil {
			return nil, fmt.Errorf("unknown kid: %s", kid)
		}
		return pub, nil
	}

	claims := &Claims{}
	token, err := jwt.ParseWithClaims(tokenStr, claims, keyFunc)
	if err != nil || !token.Valid {
		return nil, fmt.Errorf("Invalud token: %w", err)
	}

	now := time.Now()
	leeway := v.leeway

	if claims.Issuer != v.issuer {
		return nil, fmt.Errorf("issuer mismatch: got %q, want %q", claims.Issuer, v.issuer)
	}

	if !slices.Contains([]string(claims.Audience), v.audience) {
		return nil, fmt.Errorf("audience mismatch")
	}

	if claims.ExpiresAt == nil || now.After(claims.ExpiresAt.Time.Add(leeway)) {
		return nil, fmt.Errorf("token expired")
	}

	if claims.NotBefore != nil && now.Add(leeway).Before(claims.NotBefore.Time) {
		return nil, fmt.Errorf("token not valid yet")
	}

	if claims.IssuedAt != nil && claims.IssuedAt.Time.After(now.Add(leeway)) {
		return nil, fmt.Errorf("issued-at is in the future")
	}

	if claims.Subject == "" {
		return nil, fmt.Errorf("subject (sub) is empty")
	}

	return claims, nil
}
