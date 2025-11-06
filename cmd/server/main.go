package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"

	"github.com/Mozlook/MoneyControlBackend/internal/auth/jwtverifier"
	appcfg "github.com/Mozlook/MoneyControlBackend/internal/config"
	dbx "github.com/Mozlook/MoneyControlBackend/internal/db"
	"github.com/Mozlook/MoneyControlBackend/internal/http/middleware"
)

var (
	version   = "dev"
	startedAt = time.Now()
)

func main() {
	_ = godotenv.Load()
	cfg := appcfg.Load()

	ks, err := jwtverifier.LoadKeys(cfg.Auth.Keys)
	if err != nil {
		log.Fatalf("Error loading keys: %s", err)
	}

	ver, err := jwtverifier.New(cfg.Auth, ks)
	if err != nil {
		log.Fatalf("Error creating verifier: %s", err)
	}

	if cfg.App.Env == "prod" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Init DB
	sqlDB, err := dbx.Open(cfg.DB)
	if err != nil {
		log.Fatalf("db connect: %v", err)
	}
	defer sqlDB.Close()

	r := gin.New()
	r.Use(gin.Logger(), gin.Recovery())

	health := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":    "ok",
			"app_env":   cfg.App.Env,
			"version":   version,
			"startedAt": startedAt.Format(time.RFC3339),
			"uptimeSec": int(time.Since(startedAt).Seconds()),
		})
	}

	// Liveness (process alive)
	r.GET("/healthz", health)

	// Readiness (deps ready: DB ping)
	r.GET("/readyz", func(c *gin.Context) {
		ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
		defer cancel()
		if err := sqlDB.PingContext(ctx); err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"status": "not ready",
				"reason": err.Error(),
			})
			return
		}
		health(c)
	})

	// Routing
	api := r.Group("/api/v1")
	api.Use(middleware.RequireAuth(ver, sqlDB))

	port := cfg.App.Port
	srv := &http.Server{
		Addr:    ":" + port,
		Handler: r,
	}

	go func() {
		log.Printf("server starting on :%s (env=%s)", port, cfg.App.Env)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %v", err)
		}
	}()

	// Graceful shutdown
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	log.Println("server shutting down...")
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("forced shutdown: %v", err)
	}
	log.Println("server stopped")
}
