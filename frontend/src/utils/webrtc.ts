import type { Socket } from "socket.io-client";

/**
 * Создаёт peer connection с perfect negotiation.
 * @param socket Socket.IO соединение
 * @param polite true для зрителя, false для стримера
 * @param onTrack колбэк получения медиапотока
 */
export function createPerfectPeer(
  socket: Socket,
  polite: boolean,
  onTrack: (ev: RTCTrackEvent) => void
): RTCPeerConnection {
  const pc = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  });

  let makingOffer = false;
  let ignoreOffer = false;

  pc.onicecandidate = ({ candidate }) => {
    if (candidate) socket.emit("webrtc:ice", { candidate });
  };

  pc.ontrack = onTrack;

  // инициируем negotiation (создаём offer)
  pc.onnegotiationneeded = async () => {
    try {
      makingOffer = true;
      await pc.setLocalDescription();
      socket.emit("webrtc:offer", { sdp: pc.localDescription });
    } catch (err) {
      console.error("Negotiation failed", err);
    } finally {
      makingOffer = false;
    }
  };

  // --- обработка сообщений из сокета ---
  socket.on("webrtc:offer", async ({ sdp }) => {
    const offerCollision =
      sdp.type === "offer" && (makingOffer || pc.signalingState !== "stable");
    ignoreOffer = !polite && offerCollision;
    if (ignoreOffer) return;

    try {
      await pc.setRemoteDescription(sdp);
      if (sdp.type === "offer") {
        await pc.setLocalDescription(await pc.createAnswer());
        socket.emit("webrtc:answer", { sdp: pc.localDescription });
      }
    } catch (err) {
      console.error("Error handling offer", err);
    }
  });

  socket.on("webrtc:answer", async ({ sdp }) => {
    try {
      if (pc.signalingState === "have-local-offer")
        await pc.setRemoteDescription(sdp);
    } catch (err) {
      console.error("Error applying answer", err);
    }
  });

  socket.on("webrtc:ice", async ({ candidate }) => {
    if (candidate) {
      try {
        await pc.addIceCandidate(candidate);
      } catch (err) {
        if (!ignoreOffer) console.error("Failed add ICE", err);
      }
    }
  });

  return pc;
}
