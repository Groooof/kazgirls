<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { io, Socket } from 'socket.io-client'
import VideoPlayer from './VideoPlayer.vue'
import { config } from '@/config'
import Cookies from 'js-cookie'
import { useRoute } from 'vue-router'

const token = Cookies.get('access_token')
const route = useRoute()
const streamerId = Number(route.params.id)

const rtcConfig: RTCConfiguration = {
   iceServers: [
    {
      urls:  "stun:stun.l.google.com:19302"
    },
    {
      urls: "turn:turn00.natpro.ru:3478",
      username: "test_09",
      credential: "test_09"
    }
  ]
}

const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)

const remoteStream = ref<MediaStream | null>(null)
const isSocketConnected = ref(false)
const hasStream = ref(false)

const playerRef = ref<InstanceType<typeof VideoPlayer> | null>(null)
const isPip = ref(false)

let isCleaningUp = false

// 👉 для кнопки "Подключиться"
const pendingOffer = ref<RTCSessionDescriptionInit | null>(null)
const isConnecting = ref(false)
const canConnect = computed(
  () => !!pendingOffer.value && isSocketConnected.value && !isConnecting.value,
)

const hadStreamEver = ref(false)

const createPeerConnection = () => {
  console.log('[VIEWER] createPeerConnection')
  const peer = new RTCPeerConnection(rtcConfig)
  pc.value = peer

  remoteStream.value = new MediaStream()
  hasStream.value = false

  peer.onicecandidate = (event) => {
    console.log('[VIEWER] onicecandidate', event.candidate)
    if (event.candidate) {
      socket.value?.emit('webrtc:ice', {
        streamerId,
        candidate: event.candidate.toJSON(),
        from: 'viewer',
      })
    }
  }

  peer.ontrack = (event) => {
    console.log('[VIEWER] ontrack', event.streams, event.track)
    if (!remoteStream.value) {
      remoteStream.value = new MediaStream()
    }
    remoteStream.value.addTrack(event.track)
    hasStream.value = true
    hadStreamEver.value = true

    playerRef.value?.play()
  }

  peer.onconnectionstatechange = () => {
    const state = peer.connectionState
    console.log('[VIEWER] connection state:', state)

    if (state === 'failed' || state === 'disconnected' || state === 'closed') {
      console.log('[VIEWER] cleaning up after connection state', state)

      cleanupConnection()
    }
  }
}

const cleanupConnection = () => {
  if (isCleaningUp) return
  isCleaningUp = true

  console.log('[VIEWER] cleanupConnection')

  try {
    pc.value?.getReceivers().forEach((receiver) => receiver.track?.stop())
    pc.value?.close()
  } catch (e) {
    console.warn('[VIEWER] error closing pc', e)
  }
  pc.value = null

  try {
    remoteStream.value?.getTracks().forEach((t) => t.stop())
  } catch (e) {
    console.warn('[VIEWER] error stopping remote tracks', e)
  }
  remoteStream.value = null
  hasStream.value = false

  isCleaningUp = false
}

// как и было — просто используем из connectToStream/автореконнекта
const handleOffer = async (offer: RTCSessionDescriptionInit) => {
  console.log('[VIEWER] handleOffer start')

  cleanupConnection()
  createPeerConnection()
  if (!pc.value) return

  await pc.value.setRemoteDescription(new RTCSessionDescription(offer))
  console.log('[VIEWER] setRemoteDescription done')

  const answer = await pc.value.createAnswer()
  console.log('[VIEWER] createAnswer done')

  await pc.value.setLocalDescription(answer)
  console.log('[VIEWER] setLocalDescription done')

  socket.value?.emit('webrtc:answer', {
    streamerId,
    sdp: answer,
  })
  console.log('[VIEWER] answer sent')
}

// 🔘 по кнопке
const connectToStream = async () => {
  if (!pendingOffer.value) return
  if (isConnecting.value) return

  isConnecting.value = true
  try {
    await handleOffer(pendingOffer.value)
    // после успешного первого коннекта — дальше будет auto
    // pendingOffer.value = null // можешь и так, чтобы кнопка пропала сразу
  } catch (e) {
    console.error('[VIEWER] connectToStream error', e)
  } finally {
    isConnecting.value = false
  }
}

const initSocket = () => {
  socket.value = io(`${config.url}/streamers`, {
    auth: { token },
    autoConnect: true,
    query: { streamer_id: String(streamerId) },
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 500,
    reconnectionDelayMax: 5000,
  })

  socket.value.on('connect', () => {
    console.log('[VIEWER] socket connected', socket.value?.id)
    isSocketConnected.value = true

    // join_stream серверу не нужен — просто оставим если вдруг логируется, но можно убрать
    // socket.value?.emit('join_stream', { streamerId, role: 'viewer' })

    // 🔥 просим актуальный оффер, если стрим уже идёт
    socket.value?.emit('webrtc:offer', { streamerId })
  })

  socket.value.on('reconnect', (n) => {
    console.log('[VIEWER] reconnect success', n)
    isSocketConnected.value = true

    // socket.value?.emit('join_stream', { streamerId, role: 'viewer' })
    socket.value?.emit('webrtc:offer', { streamerId })
  })

  socket.value.on('disconnect', (reason) => {
    console.log('[VIEWER] socket disconnected, reason =', reason)
    isSocketConnected.value = false

    cleanupConnection()
  })

  socket.value.on('connect_error', (err) => {
    console.error('[VIEWER] connect_error', err?.message || err)
  })

  // 🔥 webrtc:offer — два случая:
  // 1) обычное поведение: сохранили offer, показали кнопку
  // 2) автореконнект: сразу вызываем handleOffer, без кнопки
  socket.value.on(
    'webrtc:offer',
    async (payload: { streamerId: number; sdp?: RTCSessionDescriptionInit }) => {
      console.log('[VIEWER] webrtc:offer received', payload)
      if (payload.streamerId !== streamerId) return

      // Это может быть наш "запрос" без SDP — игнорим
      if (!payload.sdp) {
        return
      }

      const offer = payload.sdp

      // 🔥 Если мы уже когда-то видели стрим на этой вкладке,
      // считаем, что это переподключение → пробуем подключиться АВТОМАТИЧЕСКИ
      if (hadStreamEver.value) {
        console.log('[VIEWER] auto connect on existing tab (hadStreamEver = true)')

        if (isConnecting.value) return
        isConnecting.value = true

        try {
          await handleOffer(offer)
          // успешный автоконнект — кнопку не показываем
          pendingOffer.value = null
        } catch (e) {
          console.error('[VIEWER] auto connect error, falling back to manual button', e)
          // если вдруг не получилось — даём пользователю кнопку
          pendingOffer.value = offer
        } finally {
          isConnecting.value = false
        }

        return
      }

      // 👉 Иначе — первый раз на этой вкладке: работаем как раньше через кнопку
      pendingOffer.value = offer
      hasStream.value = false
    },
  )

  socket.value.on('webrtc:ice', async (payload: { streamerId: number; candidate: RTCIceCandidateInit }) => {
    console.log('[VIEWER] webrtc:ice received', payload)
    if (payload.streamerId !== streamerId) return
    if (!pc.value) {
      console.warn('[VIEWER] got ICE but no pc, ignoring')
      return
    }
    try {
      await pc.value.addIceCandidate(new RTCIceCandidate(payload.candidate))
    } catch (e) {
      console.error('Error adding ICE candidate (viewer)', e)
    }
  })

  // ⚠️ stop_stream действительно нет — ничего не слушаем
}

const handleVisibilityChange = async () => {
  const player = playerRef.value
  if (!player) return

  const video = player.getVideoElement?.()
  if (!video || !remoteStream.value) return

  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    return
  }

  if (document.visibilityState === 'hidden') {
    try {
      await player.enterPip?.()
    } catch (e) {
      console.error('[VIEWER] enterPip error', e)
    }
    return
  }

  if (document.visibilityState === 'visible') {
    try {
      await player.exitPip?.()
    } catch (e) {
      console.error('[VIEWER] exitPip error', e)
    }
  }
}

onMounted(async () => {
  initSocket()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  cleanupConnection()
  socket.value?.disconnect()
})
</script>

<template>
  <div class="viewer-page">
    <div class="viewer-card">
      <header class="viewer-header">
        <div>
          <h1 class="viewer-title">Стример #{{ streamerId }}</h1>
          <p class="viewer-subtitle">
            {{
              !isSocketConnected
                ? 'Подключаемся к серверу...'
                : hasStream
                  ? 'Стрим в эфире'
                  : pendingOffer
                    ? 'Стрим доступен — нажмите «Подключиться»'
                    : 'Ждём, когда стример запустит стрим'
            }}
          </p>
        </div>

        <div class="status-chip" :class="isSocketConnected ? 'status-chip--ok' : 'status-chip--bad'">
          <span class="status-dot" :class="isSocketConnected ? 'status-dot--ok' : 'status-dot--bad'"></span>
          <span>{{ isSocketConnected ? 'Онлайн' : 'Офлайн' }}</span>
        </div>
      </header>

      <div class="viewer-body">
        <div class="video-wrapper">
          <VideoPlayer
            ref="playerRef"
            :src-object="remoteStream"
            :muted="false"
            @get-pip-mode="val => (isPip.value = val)"
          />

          <div v-if="!hasStream" class="video-overlay">
            <div class="spinner"></div>

            <p class="video-overlay-text">
              <span v-if="!pendingOffer">
                Ждём, когда стример запустит стрим...
              </span>
              <span v-else>
                Стрим доступен — нажмите «Подключиться»
              </span>
            </p>

            <button
              v-if="pendingOffer"
              class="connect-btn"
              :disabled="!canConnect"
              @click="connectToStream"
            >
              <span v-if="isConnecting">Подключаемся...</span>
              <span v-else>Подключиться к стриму</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.viewer-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: #0f172a;
  padding: 24px 16px;
  box-sizing: border-box;
}

.viewer-card {
  width: 100%;
  max-width: 960px;
  background: #0b1120;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  padding: 16px 20px 20px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.9);
  box-sizing: border-box;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.viewer-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #e5e7eb;
}

.viewer-subtitle {
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

.connect-btn {
  margin-top: 8px;
  border: none;
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  background: linear-gradient(135deg, #22c55e, #0ea5e9);
  color: #f9fafb;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 10px 24px rgba(34, 197, 94, 0.45);
  transition: transform 0.12s ease, box-shadow 0.12s ease, opacity 0.1s ease;
}

.connect-btn:disabled {
  opacity: 0.55;
  cursor: default;
  box-shadow: none;
  transform: none;
}

.connect-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 32px rgba(34, 197, 94, 0.7);
}

.viewer-body {
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.video-overlay-text {
  margin: 0;
  font-size: 14px;
  color: #e5e7eb;
}

.spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 3px solid rgba(148, 163, 184, 0.5);
  border-top-color: #38bdf8;
  animation: spinner 0.8s linear infinite;
}

@keyframes spinner {
  to {
    transform: rotate(360deg);
  }
}
</style>