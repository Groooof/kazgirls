<script setup lang="ts">
import axios from 'axios'
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { io, Socket } from 'socket.io-client'
import VideoPlayer from './VideoPlayer.vue'
import { config } from '@/config'
import Cookies from 'js-cookie'

const token = Cookies.get('access_token')

const route = useRoute()
const streamerId = Number(route.params.id)
const viewerId = ref<number | null>(null)

const rtcConfig: RTCConfiguration = {
  iceServers: [
    { urls: 'stun:nex2ilo.com:3478' },
    {
      urls: 'turn:nex2ilo.com:3478',
      username: 'kazgirls',
      credential: '9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN',
    },
    {
      urls: 'turns:nex2ilo.com:5349',
      username: 'kazgirls',
      credential: '9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN',
    },
  ],
  iceTransportPolicy: 'all',
};

const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)

const localStream = ref<MediaStream | null>(null)
// опционально — чтобы видеть, что прилетает обратно (для отладки)
const remoteStream = ref<MediaStream | null>(null)

const isStreaming = ref(false)
const isSocketConnected = ref(false)

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
  // история нужна только когда стрим идёт и мы знаем viewerId
  if (!viewerId.value) return

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
      },
    )

    chatMessages.value = Array.isArray(data) ? data : []

    await scrollChatToBottom()
  } catch (e) {
    console.error('[STREAMER] loadChatHistory error', e)
  } finally {
    isChatLoading.value = false
  }
}

const sendChatMessage = async () => {
  const text = chatInput.value.trim()
  if (!text || !socket.value || !isSocketConnected.value || !isStreaming.value) return

  isChatSending.value = true
  try {
    // локально добавляем сообщение стримера
    const now = new Date().toISOString()
    const localMsg: ChatMessage = {
      created: now,
      from_streamer: true,
      text,
    }
    chatMessages.value.push(localMsg)
    await scrollChatToBottom()

    socket.value.emit('message', { text })
    chatInput.value = ''
  } catch (e) {
    console.error('[STREAMER] sendChatMessage error', e)
  } finally {
    isChatSending.value = false
  }
}

/** ----- /ЧАТ ----- */

const initSocket = () => {
  socket.value = io(`${config.url}/streamers`, {
    auth: { token },
    autoConnect: true,
    transports: ['websocket'],
  })

  setInterval(() => {
    try { socket.value?.emit('ping', {}) } catch (_) {}
  }, 20000)

  socket.value.on('connect', () => {
    isSocketConnected.value = true
  })

  socket.value.on('disconnect', () => {
    isSocketConnected.value = false
  })

  // ответ от Viewer
  socket.value.on(
    'webrtc:answer',
    async (payload: { streamerId: number; sdp: RTCSessionDescriptionInit }) => {
      if (payload.streamerId !== streamerId) return
      if (!pc.value) return

      await pc.value.setRemoteDescription(new RTCSessionDescription(payload.sdp))

      // 🔥 зритель нажал "Подключиться к стриму" → прилетел answer
      // viewerId к этому моменту мы уже получили из webrtc:offer (без sdp)
      if (viewerId.value) {
        loadChatHistory()
      }
    },
  )


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
    async (payload: { streamerId: number; sdp?: RTCSessionDescriptionInit; viewerId?: number }) => {
      console.log('[STREAMER] webrtc:offer received', payload)

      if (payload.streamerId !== streamerId) return

      // если есть sdp — это либо наш же broadcast, либо не "запрос" от viewer → игнорим
      if (payload.sdp) {
        return
      }

      console.log(payload)

      // 👇 здесь как раз "запрос" от зрителя (без sdp)
      if (payload.viewerId) {
        console.log(payload.viewerId)
        viewerId.value = payload.viewerId
        console.log('[STREAMER] viewerId установлен =', viewerId.value)

        loadChatHistory()
      }

      if (!pc.value) {
        console.warn('[STREAMER] got offer-request but no pc (stream not started)')
        return
      }

      try {
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

  // 🔔 сообщения чата
  socket.value.on('message', async(msg: ChatMessage) => {
    if (!msg || typeof msg.text !== 'string') return
    chatMessages.value.push(msg)
    await scrollChatToBottom()
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

  // при остановке стрима зачистим чат (опционально)
  chatMessages.value = []
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

        <!-- ЧАТ: показываем только когда стрим запущен -->
        <div v-if="isStreaming" class="chat-wrapper">
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
                :class="msg.from_streamer ? 'chat-message--self' : 'chat-message--other'"
              >
                <div class="chat-meta">
                  <span class="chat-author">
                    {{ msg.from_streamer ? 'Вы' : 'Зритель' }}
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
                  !isStreaming ||
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
  border: 1px solid rgba(15, 23, 42, 0.9);
}

.video-wrapper :deep(video) {
  display: block;
  width: 100%;
  height: auto;
  max-height: 70vh;
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