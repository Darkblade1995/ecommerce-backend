
package main

import (
	"log"
	"time"

	"github.com/gorilla/websocket"
)

const (
	
	writeWait = 10 * time.Second


	pongWait = 60 * time.Second


	pingPeriod = (pongWait * 9) / 10 // 54 segundos


	maxMessageSize = 512
)


func (c *Client) readPump(conn *websocket.Conn) {

	defer func() {
		c.Hub.Unregister <- c
		conn.Close()
	}()

	
	conn.SetReadLimit(maxMessageSize)

	
	conn.SetReadDeadline(time.Now().Add(pongWait))

	
	conn.SetPongHandler(func(string) error {
		conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	
	for {

		_, _, err := conn.ReadMessage()
		if err != nil {

			if websocket.IsUnexpectedCloseError(
				err,
				websocket.CloseGoingAway,   
				websocket.CloseAbnormalClosure,
			) {
				log.Printf("WebSocket error for user %s: %v", c.UserID, err)
			}

			break
		}
	}
}


func (c *Client) writePump(conn *websocket.Conn) {

	ticker := time.NewTicker(pingPeriod)

	defer func() {
		ticker.Stop()
		conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.Send:

			conn.SetWriteDeadline(time.Now().Add(writeWait))

			if !ok {

				conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}


			w.Write(message)


			n := len(c.Send)
			for i := 0; i < n; i++ {
				w.Write([]byte("\n"))
				w.Write(<-c.Send)
			}


			if err := w.Close(); err != nil {
				return
			}

		case <-ticker.C:

			conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {

				return
			}
		}
	}
}