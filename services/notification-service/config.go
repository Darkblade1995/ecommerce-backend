
package main

import "os"


type Config struct {
	
	Port string

	
	KafkaBroker        string
	KafkaTopicOrders   string
	KafkaTopicPayments string
	KafkaGroupID       string

	
	AppName string
}


func LoadConfig() *Config {
	return &Config{
		Port:               getEnv("PORT", "8004"),
		KafkaBroker:        getEnv("KAFKA_BROKER", "localhost:9092"),
		KafkaTopicOrders:   getEnv("KAFKA_TOPIC_ORDERS", "orders"),
		KafkaTopicPayments: getEnv("KAFKA_TOPIC_PAYMENTS", "payments"),
		KafkaGroupID:       getEnv("KAFKA_GROUP_ID", "notification-service-group"),
		AppName:            getEnv("APP_NAME", "notification-service"),
	}
}


func getEnv(key, defaultValue string) string {
	
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}