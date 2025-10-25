<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import { io, Socket } from "socket.io-client";

const route = useRoute();
const streamerId = route.params.id as string;
const remoteVideo = ref<HTMLVideoElement | null>(null);

let socket: Socket;
let pc: RTCPeerConnection;

const iceServers = [{ urls: "stun:stun.l.google.com:19302" }];

function createPeer() {
  const peer = new RTCPeerConnection({ iceServers });

  peer.ontrack = (e) => {
    if (remoteVideo.value) remoteVideo.value.srcObject = e.streams[0];
  };

  peer.onicecandidate = ({ candidate }) => {
    if (candidate) socket.emit("webrtc:ice", { candidate });
  };

  peer.onconnectionstatechange = () => {
    console.log("RTC:", peer.connectionState);
  };

  return peer;
}

async function sendOffer() {
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  socket.emit("webrtc:offer", { sdp: offer });
}

function initSocket() {
  socket = io("http://localhost:8000/streamers", {
    query: { streamer_id: streamerId },
    auth: { token: "viewer_token" },
    reconnection: true,
    reconnectionDelay: 500,
    reconnectionAttempts: Infinity,
  });

  socket.on("connect", async () => {
    console.log("✅ Connected");
    pc = createPeer();
    await sendOffer();
  });

  socket.on("webrtc:offer", async (data) => {
    console.log("📩 Got offer, resetting peer before applying SDP");
    pc?.close()

    pc = createPeer(); // заново создать RTCPeerConnection
    await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    socket.emit("webrtc:answer", { sdp: answer });
  });

  socket.on("webrtc:answer", async (data) => {
    console.log("📩 Got answer from streamer");
    if (pc.signalingState === "have-local-offer") {
      await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
    }
  });

  socket.on("webrtc:ice", async (data) => {
    console.log("📩 Got ice");
    if (data.candidate) await pc.addIceCandidate(data.candidate);
  });
}

onMounted(() => {
  initSocket();
});

onBeforeUnmount(() => {
  socket?.disconnect();
  pc?.close();
});
</script>

<template>
  <div class="page viewer">
    <h1>👀 Viewer: {{ streamerId }}</h1>
    <video ref="remoteVideo" autoplay playsinline></video>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  align-items: center;
  video {
    width: 640px;
    height: 480px;
    background: #000;
    border-radius: 10px;
    border: 2px solid #333;
  }
}
</style>
