<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { io, Socket } from 'socket.io-client'
import VideoPlayer from './VideoPlayer.vue'
import { config } from '@/config'
import Cookies from 'js-cookie'

const token = Cookies.get('access_token')
const route = useRoute()
const streamerId = Number(route.params.id)

const rtcConfig: RTCConfiguration = {
  iceServers: [
    {
      urls: 'turn:openrelay.metered.ca:80',
      username: 'openrelayproject',
      credentials: 'openrelayproject'
    }
  ]
}

const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)

const localStream = ref<MediaStream | null>(null)
// опционально — чтобы видеть, что прилетает обратно (для отладки)
const remoteStream = ref<MediaStream | null>(null)

const isStreaming = ref(false)
const isSocketConnected = ref(false)

const initSocket = () => {
  socket.value = io(`${config.url}/streamers`, {
    auth: { token },
    autoConnect: true,
    transports: ['websocket'],
  })

  socket.value.on('connect', () => {
    isSocketConnected.value = true

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

  // 🔥 ВАЖНО: отличаем запрос (без sdp) от обычного оффера (со sdp)
  socket.value.on(
    'webrtc:offer',
    async (payload: { streamerId: number; sdp?: RTCSessionDescriptionInit }) => {
      console.log('[STREAMER] webrtc:offer received', payload)

      if (payload.streamerId !== streamerId) return

      // если есть sdp — это либо наш же broadcast, либо вообще не "запрос" от viewer → игнорим
      if (payload.sdp) {
        return
      }

      if (!pc.value) {
        console.warn('[STREAMER] got offer-request but no pc (stream not started)')
        return
      }

      try {
        // создаём новый оффер с перезапуском ICE для нового зрителя
        const newOffer = await pc.value.createOffer({ iceRestart: true } as RTCOfferOptions)
        await pc.value.setLocalDescription(newOffer)

        socket.value?.emit('webrtc:offer', {
          streamerId,
          sdp: newOffer,
        })
        console.log('[STREAMER] sent refreshed offer to viewer')
      } catch (e) {
        console.error('[STREAMER] error handling offer-request', e)
      }
    },
  )
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
  initSocket()

  await getLocalMedia()
})

onBeforeUnmount(() => {
  stopStream()
  socket.value?.disconnect()
})
</script>

<template>
  <div class="streamer-page">
    <div class="streamer-card">
      <header class="streamer-header">
        <div>
          <h1 class="streamer-title">Панель стримера #{{ streamerId }}</h1>
          <p class="streamer-subtitle">
            {{
              !isSocketConnected
                ? 'Подключаемся к серверу...'
                : isStreaming
                  ? 'Стрим в эфире'
                  : 'Стрим остановлен'
            }}
          </p>
        </div>

        <div class="status-chip" :class="isSocketConnected ? 'status-chip--ok' : 'status-chip--bad'">
          <span class="status-dot" :class="isSocketConnected ? 'status-dot--ok' : 'status-dot--bad'"></span>
          <span>{{ isSocketConnected ? 'Онлайн' : 'Офлайн' }}</span>
        </div>
      </header>

      <div class="streamer-body">
        <div class="video-wrapper">
          <VideoPlayer :src-object="localStream" :muted="true" />

          <div v-if="!localStream" class="video-overlay">
            <p class="video-overlay-text">Включите камеру, чтобы начать стрим</p>
          </div>
        </div>

        <div class="controls-row">
          <button
            class="btn btn--primary"
            :disabled="!isSocketConnected || isStreaming"
            @click="startStream"
          >
            ▶ Запустить стрим
          </button>

          <button
            class="btn btn--danger"
            :disabled="!isStreaming"
            @click="stopStream"
          >
            Остановить стрим
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.streamer-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: #020617;
  padding: 24px 16px;
  box-sizing: border-box;
}

.streamer-card {
  width: 100%;
  max-width: 960px;
  background: #020617;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  padding: 16px 20px 20px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.9);
  box-sizing: border-box;
}

.streamer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.streamer-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #e5e7eb;
}

.streamer-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #9ca3af;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.status-chip--ok {
  background: rgba(22, 163, 74, 0.16);
  color: #bbf7d0;
}

.status-chip--bad {
  background: rgba(220, 38, 38, 0.18);
  color: #fecaca;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.status-dot--ok {
  background: #22c55e;
}

.status-dot--bad {
  background: #ef4444;
}

.streamer-body {
  margin-top: 8px;
}

.video-wrapper {
  position: relative;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: #020617;
  border: 1px solid rgba(15, 23, 42, 0.9);
}

.video-wrapper :deep(video) {
  display: block;
  width: 100%;
  height: auto;
  max-height: 70vh;
  background: #020617;
}

.video-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top, rgba(15, 23, 42, 0.4), #020617);
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-overlay-text {
  margin: 0;
  font-size: 14px;
  color: #e5e7eb;
}

.controls-row {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn {
  border: none;
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: transform 0.08s ease, box-shadow 0.08s ease, opacity 0.1s ease;
}

.btn:disabled {
  opacity: 0.45;
  cursor: default;
  box-shadow: none;
  transform: none;
}

.btn--primary {
  background: linear-gradient(135deg, #22c55e, #0ea5e9);
  color: #f9fafb;
  box-shadow: 0 12px 30px rgba(34, 197, 94, 0.35);
}

.btn--primary:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 40px rgba(34, 197, 94, 0.45);
}

.btn--danger {
  background: linear-gradient(135deg, #ef4444, #f97316);
  color: #f9fafb;
  box-shadow: 0 12px 30px rgba(239, 68, 68, 0.35);
}

.btn--danger:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 40px rgba(239, 68, 68, 0.45);
}
</style>