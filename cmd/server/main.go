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
)

var (
	version   = "dev"
	startedAt = time.Now()
)

func env(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func main() {
	appEnv := env("APP_ENV", "dev")
	port := env("APP_PORT", "8080")

	if appEnv == "prod" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.New()
	r.Use(gin.Logger(), gin.Recovery())

	health := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":    "ok",
			"app_env":   appEnv,
			"version":   version,
			"startedAt": startedAt.Format(time.RFC3339),
			"uptimeSec": int(time.Since(startedAt).Seconds()),
		})
	}

	r.GET("/healthz", health)
	r.GET("/readyz", func(c *gin.Context) {
		// TODO: add real readiness checks (e.g., DB ping) before returning 200
		health(c)
	})

	srv := &http.Server{
		Addr:    ":" + port,
		Handler: r,
	}

	go func() {
		log.Printf("server starting on :%s (env=%s)", port, appEnv)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %v", err)
		}
	}()

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
