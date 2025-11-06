package password

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"

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

	// 3) PHC: base64 (bez paddingu) i złożenie stringa
	saltB64 := base64.RawStdEncoding.EncodeToString(salt)
	hashB64 := base64.RawStdEncoding.EncodeToString(hash)

	phc := fmt.Sprintf("$argon2id$v=19$m=%d,t=%d,p=%d$%s$%s",
		cfg.MemoryKiB, cfg.Time, cfg.Threads, saltB64, hashB64,
	)
	return phc, nil
}
