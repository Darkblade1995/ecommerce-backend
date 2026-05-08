
package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	"github.com/gorilla/websocket"
)


var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {

		return true
	},
}


func handleWebSocket(hub *Hub, w http.ResponseWriter, r *http.Request) {

	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		http.Error(w, "user_id is required", http.StatusBadRequest)
		return
	}

	
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	
	client := &Client{
		UserID: userID,

		Send: make(chan []byte, 256),
		Hub:  hub,
	}


	hub.Register <- client

	log.Printf("WebSocket connected: user=%s addr=%s",
		userID, conn.RemoteAddr())


	go client.writePump(conn)


	client.readPump(conn)
}


func handleHealth(hub *Hub, w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":             "healthy",
		"service":            "notification-service",
		"connected_users":    hub.ConnectedUsers(),
	})
}

func main() {

	cfg := LoadConfig()

	log.Printf("Starting %s on port %s", cfg.AppName, cfg.Port)


	hub := NewHub()
	go hub.Run()


	ctx, cancel := context.WithCancel(context.Background())


	consumer := NewKafkaConsumer(cfg, hub)
	go consumer.Start(ctx)


	router := mux.NewRouter()


	router.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		handleWebSocket(hub, w, r)
	})


	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		handleHealth(hub, w, r)
	})


	server := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: router,

		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout: 120 * time.Second,
	}


	go func() {
		log.Printf("Server listening on :%s", cfg.Port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server error: %v", err)
		}
	}()


	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	<-quit 

	log.Println("Shutdown signal received, gracefully shutting down...")

	
	cancel()


	consumer.Stop()


	shutdownCtx, shutdownCancel := context.WithTimeout(
		context.Background(),
		30*time.Second,
	)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("Server forced to shutdown: %v", err)
	}

	log.Println("notification-service stopped")
}