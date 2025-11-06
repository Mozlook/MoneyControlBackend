package password

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"fmt"
	"strconv"
	"strings"

	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	"golang.org/x/crypto/argon2"
)

func Hash(plain string, cfg appcfg.Argon2) (string, error) {
	if plain == "" {
		return "", fmt.Errorf("password is empty")
	}

	if cfg.SaltLen <= 0 || cfg.KeyLen <= 0 || cfg.Time <= 0 || cfg.MemoryKiB <= 0 || cfg.Threads <= 0 {
		return "", fmt.Errorf("invalid Argon2 params")
	}

	salt := make([]byte, cfg.SaltLen)
	_, err := rand.Read(salt)
	if err != nil {
		return "", fmt.Errorf("salt generation: %w", err)
	}

	hash := argon2.IDKey(
		[]byte(plain),
		salt,
		uint32(cfg.Time),
		uint32(cfg.MemoryKiB),
		uint8(cfg.Threads),
		uint32(cfg.KeyLen),
	)

	saltB64 := base64.RawStdEncoding.EncodeToString(salt)
	hashB64 := base64.RawStdEncoding.EncodeToString(hash)

	phc := fmt.Sprintf("$argon2id$v=19$m=%d,t=%d,p=%d$%s$%s",
		cfg.MemoryKiB, cfg.Time, cfg.Threads, saltB64, hashB64,
	)
	return phc, nil
}

func Verify(plain, phc string) (bool, error) {
	if plain == "" || phc == "" {
		return false, fmt.Errorf("empty input")
	}

	parts := strings.Split(phc, "$")
	// parts: ["", "argon2id", "v=19", "m=...,t=...,p=...", "<saltB64>", "<hashB64>"]
	if len(parts) != 6 || parts[1] != "argon2id" {
		return false, fmt.Errorf("unsupported or malformed PHC")
	}
	if parts[2] != "v=19" {
		return false, fmt.Errorf("unsupported version: %s", parts[2])
	}

	// Parse m, t, p
	m, t, p, err := parseParams(parts[3])
	if err != nil {
		return false, fmt.Errorf("bad params: %w", err)
	}
	if m <= 0 || t <= 0 || p <= 0 {
		return false, fmt.Errorf("non-positive param(s)")
	}

	// Decode salt and expected hash (base64 raw, no padding)
	salt, err := base64.RawStdEncoding.DecodeString(parts[4])
	if err != nil {
		return false, fmt.Errorf("bad salt base64: %w", err)
	}
	expected, err := base64.RawStdEncoding.DecodeString(parts[5])
	if err != nil {
		return false, fmt.Errorf("bad hash base64: %w", err)
	}
	if len(salt) < 16 || len(expected) == 0 {
		return false, fmt.Errorf("invalid salt/hash length")
	}

	// Recompute using PHC parameters and salt. Key length must match expected length.
	derived := argon2.IDKey(
		[]byte(plain),
		salt,
		uint32(t),
		uint32(m),
		uint8(p),
		uint32(len(expected)),
	)

	// Constant-time compare
	if len(derived) != len(expected) {
		return false, nil
	}
	ok := subtle.ConstantTimeCompare(derived, expected) == 1
	return ok, nil
}

// parseParams parses "m=<KiB>,t=<time>,p=<threads>" into integers.
func parseParams(s string) (m, t, p int, err error) {
	kv := strings.Split(s, ",")
	if len(kv) < 3 {
		return 0, 0, 0, fmt.Errorf("want m,t,p; got %q", s)
	}
	var gotM, gotT, gotP bool
	for _, part := range kv {
		pair := strings.SplitN(part, "=", 2)
		if len(pair) != 2 {
			return 0, 0, 0, fmt.Errorf("bad kv: %q", part)
		}
		key := strings.TrimSpace(pair[0])
		val := strings.TrimSpace(pair[1])
		n, convErr := strconv.Atoi(val)
		if convErr != nil {
			return 0, 0, 0, fmt.Errorf("bad int for %s: %w", key, convErr)
		}
		switch key {
		case "m":
			m, gotM = n, true
		case "t":
			t, gotT = n, true
		case "p":
			p, gotP = n, true
		}
	}
	if !gotM || !gotT || !gotP {
		return 0, 0, 0, fmt.Errorf("missing m/t/p")
	}
	return m, t, p, nil
}
