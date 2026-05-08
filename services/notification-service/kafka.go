package main

import (
	"context"
	"encoding/json"
	"log"
	"time"

	kafka "github.com/segmentio/kafka-go"
)


type KafkaEvent struct {
	EventType string                 `json:"event_type"`
	Timestamp string                 `json:"timestamp"`
	Service   string                 `json:"service"`
	Data      map[string]interface{} `json:"data"`
}


type KafkaConsumer struct {
	reader *kafka.Reader
	hub    *Hub
	config *Config
}


func NewKafkaConsumer(cfg *Config, hub *Hub) *KafkaConsumer {
	reader := kafka.NewReader(kafka.ReaderConfig{

		Brokers: []string{cfg.KafkaBroker},


		Topic: cfg.KafkaTopicOrders,


		GroupID: cfg.KafkaGroupID,


		MinBytes: 10e3, // 10KB
		MaxBytes: 10e6, // 10MB


		MaxWait: time.Second,


		StartOffset: kafka.LastOffset,
	})

	return &KafkaConsumer{
		reader: reader,
		hub:    hub,
		config: cfg,
	}
}


func (kc *KafkaConsumer) Start(ctx context.Context) {
	log.Printf("Kafka consumer started, listening to topic: %s", kc.config.KafkaTopicOrders)

	for {

		msg, err := kc.reader.ReadMessage(ctx)
		if err != nil {

			if ctx.Err() != nil {
				log.Println("Kafka consumer stopped: context cancelled")
				return
			}

			log.Printf("Kafka read error: %v", err)
			continue
		}


		go kc.processMessage(msg.Value)
	}
}


func (kc *KafkaConsumer) Stop() {
	if err := kc.reader.Close(); err != nil {
		log.Printf("Error closing Kafka reader: %v", err)
	}
	log.Println("Kafka reader closed")
}


func (kc *KafkaConsumer) processMessage(data []byte) {

	var event KafkaEvent
	if err := json.Unmarshal(data, &event); err != nil {
		log.Printf("Error parsing Kafka message: %v", err)
		return
	}

	log.Printf("Processing event: %s", event.EventType)


	switch event.EventType {
	case "ORDER_CREATED":
		kc.handleOrderCreated(event)
	case "ORDER_STATUS_UPDATED":
		kc.handleOrderStatusUpdated(event)
	case "ORDER_CANCELLED":
		kc.handleOrderCancelled(event)
	default:

		log.Printf("Unknown event type: %s", event.EventType)
	}
}


func (kc *KafkaConsumer) handleOrderCreated(event KafkaEvent) {

	userID, ok := event.Data["user_id"].(string)
	if !ok || userID == "" {
		log.Printf("ORDER_CREATED: missing user_id in event data")
		return
	}

	orderID, _ := event.Data["order_id"].(string)
	total, _ := event.Data["total"].(float64)


	kc.hub.SendToUser(userID, "ORDER_CREATED", map[string]interface{}{
		"message":  "Tu orden ha sido creada exitosamente",
		"order_id": orderID,
		"total":    total,
	})
}


func (kc *KafkaConsumer) handleOrderStatusUpdated(event KafkaEvent) {
	userID, ok := event.Data["user_id"].(string)
	if !ok || userID == "" {
		return
	}

	orderID, _ := event.Data["order_id"].(string)
	newStatus, _ := event.Data["new_status"].(string)


	messages := map[string]string{
		"confirmed":  "Tu orden ha sido confirmada",
		"processing": "Tu orden está siendo preparada",
		"shipped":    "Tu orden ha sido enviada",
		"delivered":  "Tu orden ha sido entregada",
		"failed":     "Hubo un problema con tu orden",
	}

	message, exists := messages[newStatus]
	if !exists {
		message = "El estado de tu orden ha cambiado"
	}

	kc.hub.SendToUser(userID, "ORDER_STATUS_UPDATED", map[string]interface{}{
		"message":    message,
		"order_id":   orderID,
		"new_status": newStatus,
	})
}


func (kc *KafkaConsumer) handleOrderCancelled(event KafkaEvent) {
	userID, ok := event.Data["user_id"].(string)
	if !ok || userID == "" {
		return
	}

	orderID, _ := event.Data["order_id"].(string)
	reason, _ := event.Data["reason"].(string)

	kc.hub.SendToUser(userID, "ORDER_CANCELLED", map[string]interface{}{
		"message":  "Tu orden ha sido cancelada",
		"order_id": orderID,
		"reason":   reason,
	})
}