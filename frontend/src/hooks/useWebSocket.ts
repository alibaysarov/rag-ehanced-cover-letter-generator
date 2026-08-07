import { TokenManager } from "@/features/auth";
import { useEffect, useRef } from "react";



interface WsConfig {
    messageHandler: (evt :MessageEvent<any>) => void
}


const setupWs = (): WebSocket => {
    const url = "ws://localhost:8000/api/v1/auto-parse/ws"
    const token = TokenManager.getAccessToken();
    const headers = ["Authorization", `Bearer ${token}`]
    return new WebSocket(url, headers);
}


const useWebSocket = ({ messageHandler }: WsConfig) => {
    const socketRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // 1. Establish the WebSocket connection
        
        socketRef.current = setupWs();

        // 2. Listen for messages from the server
        socketRef.current.onmessage = (event:MessageEvent<any>) => {
            messageHandler(event);
        };

        // 3. Optional: Handle connection errors or openings
        socketRef.current.onopen = () => console.log('Connected!');
        socketRef.current.onerror = (error) => console.error('WebSocket Error:', error);

        // 4. Clean up and close the connection when the component unmounts
        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
        };
    }, []);
}

export default useWebSocket;