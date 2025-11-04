package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// App-level config
type App struct {
	Env          string
	Port         string
	TZ           string
	HomeCurrency string
}

// Database config
type DB struct {
	DSN             string
	MaxOpenConns    int
	MaxIdleConns    int
	ConnMaxLifetime time.Duration
}

// Global config root
type Config struct {
	App App
	DB  DB
}

// Load reads all configuration from environment variables (once, centrally).
func Load() Config {
	// Prefer DATABASE_URL. If empty, build DSN from components.
	dsn := get("DATABASE_URL", "")
	if dsn == "" {
		host := get("DB_HOST", "localhost")
		port := get("DB_PORT", "5432")
		user := get("DB_USER", "moneycontrol")
		pass := get("DB_PASSWORD", "moneycontrol")
		name := get("DB_NAME", "moneycontrol")
		dsn = fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=disable", user, pass, host, port, name)
	}

	return Config{
		App: App{
			Env:          get("APP_ENV", "dev"),
			Port:         get("APP_PORT", "8080"),
			TZ:           get("TZ", "Europe/Warsaw"),
			HomeCurrency: get("HOME_CURRENCY", "PLN"),
		},
		DB: DB{
			DSN:             dsn,
			MaxOpenConns:    getInt("DB_MAX_OPEN", 10),
			MaxIdleConns:    getInt("DB_MAX_IDLE", 5),
			ConnMaxLifetime: getDuration("DB_CONN_MAX_LIFETIME", 30*time.Minute),
		},
	}
}

// --- helpers ---

func get(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func getInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func getDuration(key string, def time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return def
}
