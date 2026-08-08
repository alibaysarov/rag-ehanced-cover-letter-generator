import { TokenManager } from "@/features/auth";
import { useEffect, useRef } from "react";

interface WsConfig<T> {
    messageHandler: (evt: MessageEvent<T>) => void;
}

const setupWs = (): WebSocket => {
    const token = TokenManager.getAccessToken();
    const url = `ws://localhost:8000/api/v1/auto-parse/ws?token=${encodeURIComponent(token ?? "")}`;
    return new WebSocket(url);
};

const useWebSocket = <T>({ messageHandler }: WsConfig<T>) => {
    const socketRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        const socket = setupWs();
        socketRef.current = socket;

        socket.onmessage = (event: MessageEvent<T>) => {
            messageHandler(event);
        };

        socket.onopen = () => console.log("Connected!");
        socket.onerror = (error) => console.error("WebSocket Error:", error);
        socket.onclose = (event) => console.log("WebSocket closed:", event.code, event.reason);

        return () => {
            // Если сокет ещё не открылся — закрываем его "мягко",
            // без ошибки в консоли, и не даём "повиснуть" открытому соединению
            if (
                socket.readyState === WebSocket.CONNECTING ||
                socket.readyState === WebSocket.OPEN
            ) {
                socket.close();
            }
            if (socketRef.current === socket) {
                socketRef.current = null;
            }
        };
    }, []);
};

export default useWebSocket;