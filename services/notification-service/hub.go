
package main

import (
	"encoding/json"
	"log"
	"sync"
)


type Message struct {
	UserID    string                 `json:"user_id"`
	EventType string                 `json:"event_type"`
	Data      map[string]interface{} `json:"data"`
}


type Client struct {

	UserID string


	Send chan []byte


	Hub *Hub
}


type Hub struct {

	clients map[string]*Client


	mu sync.RWMutex


	Register chan *Client


	Unregister chan *Client


	Broadcast chan *Message
}


func NewHub() *Hub {
	return &Hub{
		clients:    make(map[string]*Client),
		Register:   make(chan *Client, 256),
		Unregister: make(chan *Client, 256),
		Broadcast:  make(chan *Message, 1024),
	}
}


func (h *Hub) Run() {
	for {

		select {

		case client := <-h.Register:

			h.mu.Lock()

			if existing, ok := h.clients[client.UserID]; ok {
				close(existing.Send)
				log.Printf("Replaced existing connection for user %s", client.UserID)
			}
			h.clients[client.UserID] = client
			h.mu.Unlock()
			log.Printf("User %s connected. Total connections: %d",
				client.UserID, len(h.clients))

		case client := <-h.Unregister:

			h.mu.Lock()
			if _, ok := h.clients[client.UserID]; ok {
				delete(h.clients, client.UserID)
				close(client.Send)
			}
			h.mu.Unlock()
			log.Printf("User %s disconnected. Total connections: %d",
				client.UserID, len(h.clients))

		case message := <-h.Broadcast:

			data, err := json.Marshal(message)
			if err != nil {
				log.Printf("Error marshaling message: %v", err)
				continue
			}

			h.mu.RLock()
			client, ok := h.clients[message.UserID]
			h.mu.RUnlock()

			if !ok {

				log.Printf("User %s not connected, message dropped", message.UserID)
				continue
			}


			select {
			case client.Send <- data:
				log.Printf("Message sent to user %s: %s",
					client.UserID, message.EventType)
			default:

				h.mu.Lock()
				delete(h.clients, client.UserID)
				close(client.Send)
				h.mu.Unlock()
				log.Printf("Client %s too slow, disconnected", client.UserID)
			}
		}
	}
}


func (h *Hub) SendToUser(userID, eventType string, data map[string]interface{}) {
	h.Broadcast <- &Message{
		UserID:    userID,
		EventType: eventType,
		Data:      data,
	}
}


func (h *Hub) ConnectedUsers() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}