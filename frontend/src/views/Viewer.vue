<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { io, Socket } from 'socket.io-client'
import VideoPlayer from './VideoPlayer.vue'
import axios from 'axios'
import { config } from '@/config'

const isProd = true
const streamerId = isProd ? 4 : 2

const rtcConfig: RTCConfiguration = {
  iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
}

const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)

const remoteStream = ref<MediaStream | null>(null)
const isSocketConnected = ref(false)
const hasStream = ref(false) // 👈 есть ли активный стрим

const playerRef = ref<InstanceType<typeof VideoPlayer> | null>(null)
const isPip = ref(false)

let isCleaningUp = false

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

  peer.ontrack = async (event) => {
    console.log('[VIEWER] ontrack', event.streams, event.track)
    if (!remoteStream.value) {
      remoteStream.value = new MediaStream()
    }
    remoteStream.value.addTrack(event.track)
    hasStream.value = true

    await nextTick()

    forcePlay()
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

const initSocket = (access_token: string) => {
  const url = isProd ? `${config.apiUrl}/streamers` : 'http://localhost:8000/streamers'

  socket.value = io(url, {
    auth: { token: access_token },
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

    socket.value?.emit('join_stream', {
      streamerId,
      role: 'viewer',
    })
  })

  socket.value.on('disconnect', (reason) => {
    console.log('[VIEWER] socket disconnected, reason =', reason)
    isSocketConnected.value = false
    cleanupConnection()
  })

  socket.value.on('connect_error', (err) => {
    console.error('[VIEWER] connect_error', err?.message || err)
  })

  socket.value.on('reconnect', (n) => {
    console.log('[VIEWER] reconnect success', n)
    isSocketConnected.value = true
    socket.value?.emit('join_stream', {
      streamerId,
      role: 'viewer',
    })
  })

  socket.value.on('webrtc:offer', async (payload: { streamerId: number; sdp: RTCSessionDescriptionInit }) => {
    console.log('[VIEWER] webrtc:offer received', payload)
    if (payload.streamerId !== streamerId) return
    await handleOffer(payload.sdp)
  })

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

  socket.value.on('stop_stream', (payload: { streamerId: number }) => {
    console.log('[VIEWER] stop_stream', payload)
    if (payload.streamerId !== streamerId) return
    cleanupConnection()
  })
}

const handleVisibilityChange = async () => {
  const player = playerRef.value
  if (!player) return

  const video = player.getVideoElement?.()
  if (!video || !remoteStream.value) return

  // На всякий случай — ждём, пока есть данные
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    return
  }

  const anyDoc = document as any

  // сворачивание / переход на другую вкладку
  if (document.visibilityState === 'hidden') {
    // Пытаемся включить PiP через Plyr (enterPip)
    try {
      await player.enterPip?.()
    } catch (e) {
      console.error('[VIEWER] enterPip error', e)
    }
    return
  }

  // возврат на вкладку — выходим из PiP
  if (document.visibilityState === 'visible') {
    try {
      await player.exitPip?.()
    } catch (e) {
      console.error('[VIEWER] exitPip error', e)
    }
  }
}

const forcePlay = async () => {
  const player = playerRef.value
  if (!player) return

  const video: HTMLVideoElement | null = player.getVideoElement?.() as any
  // @ts-ignore
  const plyrInstance = player.getPlyrInstance?.()

  if (!video) return

  try {
    await video.play()
    console.log('[VIEWER] forced native play() ok')
  } catch (e) {
    console.warn('[VIEWER] native play() failed', e)
  }

  if (plyrInstance && typeof plyrInstance.play === 'function') {
    try {
      await plyrInstance.play()
      console.log('[VIEWER] forced plyr.play() ok')
    } catch (e) {
      console.warn('[VIEWER] plyr.play() failed', e)
    }
  }
}

onMounted(async () => {
  if (isProd) {
    const { data } = await axios.post('/api/v1/tokens/login', {
      username: 'viewer_2',
      password: 'test',
    })
    initSocket(data.access_token)
  } else {
    const { data } = await axios.post('http://localhost:8000/api/v1/tokens/login', {
      username: 'girl',
      password: 'test',
    })
    initSocket(data.access_token)
  }

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
              Ждём, когда стример запустит стрим...
            </p>
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