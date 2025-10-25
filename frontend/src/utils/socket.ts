import { io, Socket } from "socket.io-client";

const SERVER_URL = "http://localhost:8000/streamers";

export function createSocket(streamerId: string, token: string): Socket {
  const socket = io(SERVER_URL, {
    query: { streamer_id: streamerId },
    auth: { token },
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: Infinity,
  });

  socket.on("connect", () => console.log("✅ Connected to Socket.IO"));
  socket.on("disconnect", (reason) => console.log("❌ Disconnected:", reason));
  socket.on("reconnect", (attempt) => console.log("🔄 Reconnected after", attempt));

  return socket;
}
