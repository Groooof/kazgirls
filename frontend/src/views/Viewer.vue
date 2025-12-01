<script setup lang="ts">
import axios from 'axios'
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import { io, Socket } from 'socket.io-client'
import VideoPlayer from './VideoPlayer.vue'
import { config } from '@/config'
import Cookies from 'js-cookie'
import { useRoute } from 'vue-router'

type Me = {
  id: number
  username: string
  is_streamer: boolean
  is_superuser: boolean
}

const token = Cookies.get('access_token')
const route = useRoute()
const streamerId = Number(route.params.id)

const viewerId = ref<number | null>(null)

const rtcConfig: RTCConfiguration = {
  iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
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

const loadMe = async () => {
  try {
    const { data } = await axios.get<Me>(
      `${config.url}${config.apiUrl}/tokens/me`,
      { withCredentials: true },
    )

    // мы сейчас в компоненте зрителя, но на всякий случай можно проверить
    if (!data.is_streamer) {
      viewerId.value = data.id

      socket.value?.emit('webrtc:offer', { streamerId, viewerId: viewerId.value ?? undefined, })
    } else {
      console.warn('[VIEWER] /tokens/me вернул стримера, viewerId не установлен')
    }
  } catch (e) {
    console.error('[VIEWER] loadMe error', e)
  }
}

/** ----- ЧАТ ----- */

interface ChatMessage {
  created: string
  from_streamer: boolean
  text: string
}

const chatMessagesEl = ref<HTMLElement | null>(null)

const scrollChatToBottom = async () => {
  await nextTick()
  const el = chatMessagesEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

const chatMessages = ref<ChatMessage[]>([])
const chatInput = ref('')
const isChatLoading = ref(false)
const isChatSending = ref(false)

const formatTime = (iso: string) => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  })
}

const loadChatHistory = async () => {
  // показываем чат только когда есть стрим и есть viewerId
  if (!hasStream.value || !viewerId.value) return

  isChatLoading.value = true
  try {
    const params = new URLSearchParams({
      streamer_id: String(streamerId),
      viewer_id: String(viewerId.value),
    })

    const { data } = await axios.get(
      `${config.url}${config.apiUrl}/messages`,
      {
        params,
        withCredentials: true,
      }
    )

    chatMessages.value = Array.isArray(data) ? data : []

    await scrollChatToBottom()
  } catch (e) {
    console.error('[VIEWER] loadChatHistory error', e)
  } finally {
    isChatLoading.value = false
  }
}

const sendChatMessage = async () => {
  const text = chatInput.value.trim()
  if (!text || !socket.value || !isSocketConnected.value || !hasStream.value) return

  isChatSending.value = true
  try {
    // локально добавляем своё сообщение
    const now = new Date().toISOString()
    const localMsg: ChatMessage = {
      created: now,
      from_streamer: false, // мы — зритель
      text,
    }
    chatMessages.value.push(localMsg)
    await scrollChatToBottom()

    // отправляем на сервер
    socket.value.emit('message', { text })
    chatInput.value = ''
  } catch (e) {
    console.error('[VIEWER] sendChatMessage error', e)
  } finally {
    isChatSending.value = false
  }
}

/** ----- /ЧАТ ----- */

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

    // как только реально есть поток — грузим историю чата
    loadChatHistory()
  }

  peer.onconnectionstatechange = () => {
    const state = peer.connectionState
    console.log('[VIEWER] connection state:', state)

    if (state === 'failed' || state === 'disconnected' || state === 'closed') {
      console.log('[VIEWER] cleaning up after connection state', state)

      cleanupConnection()
      // pendingOffer НЕ трогаем — новый оффер прилетит при переподключении
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

  // при потере стрима можно очистить чат
  chatMessages.value = []
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

  setInterval(() => {
    try { socket.emit('ping', {}) } catch (_) {}
  }, 20000)

  socket.value?.emit('webrtc:offer', { streamerId, viewerId: viewerId.value ?? undefined, })

  socket.value.on('connect', () => {
    console.log('[VIEWER] socket connected', socket.value?.id)
    isSocketConnected.value = true

    console.log(viewerId.value)
    // 🔥 просим актуальный оффер, если стрим уже идёт
    socket.value?.emit('webrtc:offer', { streamerId, viewerId: viewerId.value ?? undefined, })
  })

  socket.value.on('reconnect', (n) => {
    console.log('[VIEWER] reconnect success', n)
    isSocketConnected.value = true

    socket.value?.emit('webrtc:offer', { streamerId, viewerId: viewerId.value ?? undefined, })
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

      // это может быть наш "запрос" без sdp — игнорим
      if (!payload.sdp) {
        return
      }

      const offer = payload.sdp

      // 🔥 обычное поведение: пользователь сам решает, когда жать "Подключиться"
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

  // 🔔 сообщения чата
  socket.value.on('message', async(msg: ChatMessage) => {
    if (!msg || typeof msg.text !== 'string') return
    chatMessages.value.push(msg)
    await scrollChatToBottom()
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
  await loadMe()
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

        <!-- ЧАТ: показываем только когда есть поток -->
        <div v-if="hasStream && viewerId" class="chat-wrapper">
          <h2 class="chat-title">Чат</h2>

          <div class="chat-box">
            <div ref="chatMessagesEl" class="chat-messages">
              <p v-if="isChatLoading && !chatMessages.length" class="chat-empty">
                Загружаем сообщения...
              </p>
              <p v-else-if="!isChatLoading && !chatMessages.length" class="chat-empty">
                Пока нет сообщений
              </p>

              <div
                v-for="(msg, idx) in chatMessages"
                :key="idx"
                class="chat-message"
                :class="msg.from_streamer ? 'chat-message--other' : 'chat-message--self'"
              >
                <div class="chat-meta">
                  <span class="chat-author">
                    {{ msg.from_streamer ? 'Стример' : 'Вы' }}
                  </span>
                  <span class="chat-time">{{ formatTime(msg.created) }}</span>
                </div>
                <div class="chat-text">
                  {{ msg.text }}
                </div>
              </div>
            </div>

            <form class="chat-input-row" @submit.prevent="sendChatMessage">
              <input
                v-model="chatInput"
                class="chat-input"
                type="text"
                placeholder="Напишите сообщение..."
              >
              <button
                class="chat-send-btn"
                type="submit"
                :disabled="
                  !chatInput.trim() ||
                  !isSocketConnected ||
                  !hasStream ||
                  isChatSending
                "
              >
                {{ isChatSending ? 'Отправляем...' : 'Отправить' }}
              </button>
            </form>
          </div>
        </div>
        <!-- /ЧАТ -->
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

/* ---- ЧАТ ---- */

.chat-wrapper {
  margin-top: 18px;
}

.chat-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 500;
  color: #e5e7eb;
}

.chat-box {
  border-radius: 12px;
  border: 1px solid rgba(30, 64, 175, 0.7);
  background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.16), #020617);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chat-messages {
  max-height: 220px;
  overflow-y: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-empty {
  margin: 4px 0;
  font-size: 13px;
  color: #9ca3af;
}

.chat-message {
  max-width: 80%;
  padding: 6px 8px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.35;
}

.chat-message--self {
  margin-left: auto;
  background: linear-gradient(135deg, #22c55e, #0ea5e9);
  color: #f9fafb;
}

.chat-message--other {
  margin-right: auto;
  background: rgba(15, 23, 42, 0.96);
  color: #e5e7eb;
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.chat-meta {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 2px;
  opacity: 0.9;
}

.chat-author {
  font-weight: 500;
}

.chat-time {
  font-size: 11px;
  opacity: 0.75;
}

.chat-text {
  word-wrap: break-word;
  white-space: pre-wrap;
}

.chat-input-row {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.chat-input {
  flex: 1;
  border-radius: 999px;
  border: 1px solid rgba(75, 85, 99, 0.8);
  background: #020617;
  color: #e5e7eb;
  padding: 7px 10px;
  font-size: 13px;
  outline: none;
}

.chat-input::placeholder {
  color: #6b7280;
}

.chat-input:focus {
  border-color: #38bdf8;
}

.chat-send-btn {
  border: none;
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 500;
  background: linear-gradient(135deg, #22c55e, #0ea5e9);
  color: #f9fafb;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 8px 18px rgba(34, 197, 94, 0.4);
  transition: transform 0.08s ease, box-shadow 0.08s ease, opacity 0.1s ease;
}

.chat-send-btn:disabled {
  opacity: 0.45;
  cursor: default;
  box-shadow: none;
  transform: none;
}

.chat-send-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(34, 197, 94, 0.6);
}

/* ---- /ЧАТ ---- */
</style>
