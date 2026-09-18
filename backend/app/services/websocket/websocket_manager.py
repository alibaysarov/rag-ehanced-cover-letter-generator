from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        key = self.__get_key(user_id)
        self._connections[key] = ws

    async def send_text(self, user_id: str, text: str):
        print(user_id)
        key = self.__get_key(user_id)
        print("Conns ", self._connections)
        conn = self._connections.get(key)

        if conn is not None:
            await conn.send_text(text)

    async def disconnect(self, user_id: str, expected_ws: WebSocket | None = None):
        key = self.__get_key(user_id)
        if expected_ws is None or self._connections.get(key) is expected_ws:
            self._connections.pop(key, None)

    def __get_key(self, user_id: str):
        return f"user:{user_id}"
