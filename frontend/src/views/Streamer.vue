<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { io, Socket } from 'socket.io-client'
import VideoPlayer from './VideoPlayer.vue'
import axios from 'axios'
import { config } from '@/config'

const isProd = true

const route = useRoute()
const streamerId = isProd ? 4 : 2

const rtcConfig: RTCConfiguration = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
  ],
}

const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)

const localStream = ref<MediaStream | null>(null)
// опционально — чтобы видеть, что прилетает обратно (для отладки)
const remoteStream = ref<MediaStream | null>(null)

const isStreaming = ref(false)
const isSocketConnected = ref(false)

const initSocket = (access_token: string) => {
  if (isProd) {
    socket.value = io(`${config.apiUrl}/streamers`, {
      auth: { token: access_token },
      autoConnect: true,
      transports: ['websocket'],
    })
  } else {
    socket.value = io('http://localhost:8000/streamers', {
      auth: { token: access_token },
      autoConnect: true,
      transports: ['websocket'],
    })
  }

  socket.value.on('connect', () => {
    isSocketConnected.value = true

    // заходим в "комнату" стримера
    socket.value?.emit('join_stream', {
      streamerId,
      role: 'streamer',
    })
  })

  socket.value.on('disconnect', () => {
    isSocketConnected.value = false
  })

  // ответ от Viewer
  socket.value.on('webrtc:answer', async (payload: { streamerId: number; sdp: RTCSessionDescriptionInit }) => {
    if (payload.streamerId !== streamerId) return
    if (!pc.value) return

    await pc.value.setRemoteDescription(new RTCSessionDescription(payload.sdp))
  })

  // ice-кандидаты от Viewer
  socket.value.on('webrtc:ice', async (payload: { streamerId: number; candidate: RTCIceCandidateInit }) => {
    if (payload.streamerId !== streamerId) return
    if (!pc.value) return
    try {
      await pc.value.addIceCandidate(new RTCIceCandidate(payload.candidate))
    } catch (e) {
      console.error('Error adding ICE candidate', e)
    }
  })
}

const getLocalMedia = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: {
        echoCancellation: { ideal: true },
        noiseSuppression: { ideal: true },
        autoGainControl: { ideal: true },
      },
    })
    localStream.value = stream
  } catch (e) {
    console.error('Error accessing media devices', e)
  }
}

const createPeerConnection = () => {
  pc.value = new RTCPeerConnection(rtcConfig)

  // отправка ICE-кандидатов на сервер
  pc.value.onicecandidate = (event) => {
    if (event.candidate) {
      socket.value?.emit('webrtc:ice', {
        streamerId,
        candidate: event.candidate.toJSON(),
        from: 'streamer',
      })
    }
  }

  pc.value.onconnectionstatechange = () => {
    console.log('[STREAMER] connection state:', pc.value?.connectionState)
  }

  // если стример тоже будет что-то получать (обычно не надо)
  pc.value.ontrack = (event) => {
    if (!remoteStream.value) {
      remoteStream.value = new MediaStream()
    }
    remoteStream.value.addTrack(event.track)
  }

  // добавляем свои треки
  if (localStream.value) {
    localStream.value.getTracks().forEach((track) => {
      pc.value?.addTrack(track, localStream.value as MediaStream)
    })
  }
}

const startStream = async () => {
  console.log('[STREAMER] startStream clicked')

  if (!socket.value || !isSocketConnected.value) {
    console.warn('[STREAMER] Socket not ready')
    return
  }
  if (!localStream.value) {
    console.log('[STREAMER] getLocalMedia...')
    await getLocalMedia()
  }

  console.log('[STREAMER] createPeerConnection')
  createPeerConnection()

  if (!pc.value) return

  console.log('[STREAMER] createOffer...')
  const offer = await pc.value.createOffer()
  console.log('[STREAMER] setLocalDescription...')
  await pc.value.setLocalDescription(offer)

  console.log('[STREAMER] emit webrtc_offer', { streamerId })
  socket.value.emit('webrtc:offer', {
    streamerId,
    sdp: offer,
  })

  isStreaming.value = true
}

const stopStream = () => {
  isStreaming.value = false

  pc.value?.getSenders().forEach((sender) => sender.track?.stop())
  pc.value?.close()
  pc.value = null

  localStream.value?.getTracks().forEach((t) => t.stop())
  localStream.value = null

  // можно послать событие на сервер, что стрим закончился
  socket.value?.emit('stop_stream', { streamerId })
}

onMounted(async () => {
  if (isProd) {
    const { data } = await axios.post('/api/v1/tokens/login', {
      username: "streamer_2",
      password: "test",
    })

    initSocket(data.access_token)
  } else {
    const { data } = await axios.post('http://localhost:8000/api/v1/tokens/login', {
      username: "stream",
      password: "test",
    })

    initSocket(data.access_token)
  }

  await getLocalMedia()
})

onBeforeUnmount(() => {
  stopStream()
  socket.value?.disconnect()
})
</script>

<template>
  <div>
    <h1>Streamer #{{ streamerId }}</h1>

    <div style="max-width: 600px;">
      <!-- Локальное видео стримера -->
      <VideoPlayer :src-object="localStream" play muted />
    </div>

    <div style="margin-top: 16px; display: flex; gap: 8px;">
      <button :disabled="!isSocketConnected || isStreaming" @click="startStream">
        Запустить стрим
      </button>
      <button :disabled="!isStreaming" @click="stopStream">
        Остановить стрим
      </button>
    </div>

    <!-- Опционально: показать remoteStream, если нужен возврат -->
    <!--
    <div v-if="remoteStream" style="max-width: 600px; margin-top: 24px;">
      <h3>Remote</h3>
      <VideoPlayer :src-object="remoteStream" />
    </div>
    -->
  </div>
</template>
