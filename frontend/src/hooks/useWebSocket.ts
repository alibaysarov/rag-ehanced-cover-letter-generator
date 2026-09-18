import { API_BASE_URL } from '@/api/client';
import { TokenManager } from '@/features/auth';
import { useEffect, useRef } from 'react';

interface WsConfig<T> {
  messageHandler: (evt: MessageEvent<T>) => void;
  onOpen?: () => void;
}

function websocketUrl(token: string): string {
  const apiUrl = new URL(API_BASE_URL, window.location.origin);
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, '')}/auto-parse/ws`;
  apiUrl.search = `token=${encodeURIComponent(token)}`;
  return apiUrl.toString();
}

const useWebSocket = <T>({ messageHandler, onOpen }: WsConfig<T>) => {
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number | null>(null);
  const handlerRef = useRef(messageHandler);
  const openRef = useRef(onOpen);
  handlerRef.current = messageHandler;
  openRef.current = onOpen;

  useEffect(() => {
    const token = TokenManager.getAccessToken();
    if (!token) return;
    let disposed = false;
    let attempts = 0;

    const connect = () => {
      if (disposed) return;
      const socket = new WebSocket(websocketUrl(token));
      socketRef.current = socket;
      socket.onopen = () => {
        attempts = 0;
        openRef.current?.();
      };
      socket.onmessage = (event: MessageEvent<T>) => handlerRef.current(event);
      socket.onclose = (event) => {
        if (disposed || event.code === 1008 || event.code === 4001) return;
        retryRef.current = window.setTimeout(connect, Math.min(1000 * 2 ** attempts++, 15000));
      };
    };
    connect();

    return () => {
      disposed = true;
      if (retryRef.current !== null) window.clearTimeout(retryRef.current);
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) socket.close();
    };
  }, []);
};

export default useWebSocket;
