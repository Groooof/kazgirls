<template>
  <div class="page">
    <header>
      <h1>Viewer</h1>
      <div class="status">
        <span :class="['dot', socketConnected ? 'on' : 'off']"></span>
        {{ socketConnected ? 'Socket connected' : 'Socket disconnected' }}
        <span v-if="connectionNote"> · {{ connectionNote }}</span>
      </div>
    </header>

    <main>
      <div class="video-box">
        <video ref="remoteVideo" autoplay playsinline :muted="muted"></video>
        <div class="overlay">
          <div class="badge">Stream</div>
          <button class="mute" @click="toggleMute">{{ muted ? 'Unmute' : 'Mute' }}</button>
        </div>
      </div>

      <details class="debug">
        <summary>Debug info</summary>
        <pre>streamerId: {{ streamerId }}</pre>
        <pre>viewerKey: {{ viewerKey }}</pre>
        <pre>socketId: {{ socketId || '—' }}</pre>
        <pre>pc: {{ pcState }}</pre>
      </details>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'
import { io } from 'socket.io-client'
import { config } from '@/config.ts'

const NAMESPACE = '/streamers'
const ICE_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }]

/**
 * ====== UTILS ======
 */
function qs(name) { return new URLSearchParams(window.location.search).get(name) }
function getToken() {
  const fromQS = qs('token')
  if (fromQS) return fromQS
  try { return localStorage.getItem('token') } catch (_) { return null }
}
function getStableViewerKey() {
  try {
    const k = localStorage.getItem('viewerKey')
    if (k) return k
    const buf = new Uint8Array(16)
    crypto.getRandomValues(buf)
    const hex = [...buf].map(b => b.toString(16).padStart(2, '0')).join('')
    const newKey = `v-${hex}`
    localStorage.setItem('viewerKey', newKey)
    return newKey
  } catch (_) {
    // если localStorage недоступен — сгенерим volatile ключ
    const rnd = Math.random().toString(36).slice(2)
    return `v-${Date.now()}-${rnd}`
  }
}

/**
 * ====== STATE ======
 */
const streamerIdStr = qs('streamer_id')
if (!streamerIdStr) {
  console.warn('Viewer: ?streamer_id= is required for server-side session binding')
}
const streamerId = streamerIdStr ? Number(streamerIdStr) : null
const viewerKey = getStableViewerKey()

const remoteVideo = ref(null)
const muted = ref(true)
const socketConnected = ref(false)
const socketId = ref(null)
const connectionNote = ref('')

let socket = null
let pingTimer = null
let autoOfferTimer = null

// Perfect negotiation / PC
let pc = null
const pcState = computed(() => pc ? `${pc.connectionState} / ${pc.signalingState}` : 'no pc')

const ctx = {
  isPolite: true,                 // зритель — polite
  makingOffer: false,
  isSettingRemoteAnswerPending: false,
  ignoreOffer: false,
  pendingCandidates: []
}

function makeChannel() {
  return { streamerId: streamerId ?? null, viewerKey }
}

/**
 * ====== PEER CONNECTION ======
 */
function createPC() {
  if (pc) try { pc.close() } catch (_) {}
  pc = new RTCPeerConnection({ iceServers: ICE_SERVERS })

  // Зритель получает только удалённые медиапотоки
  pc.addTransceiver('video', { direction: 'recvonly' })
  pc.addTransceiver('audio', { direction: 'recvonly' })

  pc.addEventListener('track', (ev) => {
    // Будет стримерский медиа-трек
    const [stream] = ev.streams
    if (remoteVideo.value && stream) {
      remoteVideo.value.srcObject = stream
    }
  })

  pc.addEventListener('negotiationneeded', async () => {
    // Инициируем оффер (важно для сценария "зритель пришёл первым")
    await sendOfferSafe()
  })

  pc.addEventListener('icecandidate', ({ candidate }) => {
    if (!candidate) return
    socket?.emit('webrtc:ice', { channel: makeChannel(), candidate })
  })

  pc.addEventListener('iceconnectionstatechange', () => {
    const st = pc.iceConnectionState
    if (st === 'failed') {
      try { pc.restartIce() } catch (_) {}
      // Попросим новое согласование
      pc.dispatchEvent(new Event('negotiationneeded'))
    }
    if (st === 'connected') {
      connectionNote.value = 'Streaming'
    }
  })

  pc.addEventListener('connectionstatechange', () => {
    const st = pc.connectionState
    if (st === 'disconnected' || st === 'failed') {
      connectionNote.value = `Peer ${st}, will retry…`
      scheduleAutoOffer(800) // ускорим переподключение
    }
  })
}

async function sendOfferSafe() {
  if (!pc) return
  try {
    ctx.makingOffer = true
    if (pc.signalingState !== 'stable') return
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    socket?.emit('webrtc:offer', {
      channel: makeChannel(),
      description: pc.localDescription
    })
  } catch (err) {
    console.error('[offer] error', err)
  } finally {
    ctx.makingOffer = false
  }
}

async function handleRemoteDescription(description) {
  if (!pc) return
  const readyForOffer = !ctx.makingOffer && (pc.signalingState === 'stable' || ctx.isSettingRemoteAnswerPending)
  const offerCollision = description.type === 'offer' && !readyForOffer

  ctx.ignoreOffer = !ctx.isPolite && offerCollision
  if (ctx.ignoreOffer) {
    console.warn('[viewer: impolite?] ignoring offer due to glare (should not happen)')
    return
  }

  ctx.isSettingRemoteAnswerPending = description.type === 'answer'
  try {
    await pc.setRemoteDescription(description)
  } catch (err) {
    if (description.type === 'offer') {
      try {
        await pc.setLocalDescription({ type: 'rollback' })
        await pc.setRemoteDescription(description)
      } catch (e) {
        console.error('[viewer] setRemoteDescription failed even after rollback', e)
        return
      }
    } else {
      console.error('[viewer] setRemoteDescription error', err)
      return
    }
  } finally {
    ctx.isSettingRemoteAnswerPending = false
  }

  // Применим отложенные ICE‑кандидаты
  if (ctx.pendingCandidates.length) {
    const q = ctx.pendingCandidates.slice()
    ctx.pendingCandidates.length = 0
    for (const c of q) {
      try { await pc.addIceCandidate(c) } catch (e) { console.warn('addIceCandidate (queued) failed', e) }
    }
  }

  if (description.type === 'offer') {
    try {
      const answer = await pc.createAnswer()
      await pc.setLocalDescription(answer)
      socket?.emit('webrtc:answer', {
        channel: makeChannel(),
        description: pc.localDescription
      })
    } catch (err) {
      console.error('[viewer] createAnswer error', err)
    }
  }
}

/**
 * ====== AUTO OFFER LOOP ======
 * Позволяет зрителю «достучаться» до стримера, даже если он придёт позже.
 * Плавный бэкофф до 5s; сбрасывается при успехе/дисконнекте.
 */
function scheduleAutoOffer(initialMs = 1200) {
  clearTimeout(autoOfferTimer)
  let delay = initialMs
  const loop = async () => {
    if (!socket || !socket.connected || !pc) { delay = 1200; autoOfferTimer = setTimeout(loop, delay); return }
    if (pc.connectionState === 'connected') { autoOfferTimer = setTimeout(loop, 2000); return }
    await sendOfferSafe()
    delay = Math.min(delay * 1.6, 5000)
    autoOfferTimer = setTimeout(loop, delay)
  }
  autoOfferTimer = setTimeout(loop, delay)
}

/**
 * ====== SOCKET ======
 */
function attachSocketHandlers() {
  socket.on('connect', () => {
    socketConnected.value = true
    socketId.value = socket.id
    connectionNote.value = 'Connected to signaling'
    // На всякий случай сразу инициируем оффер
    scheduleAutoOffer(600)
  })
  socket.on('disconnect', () => {
    socketConnected.value = false
    socketId.value = null
    scheduleAutoOffer(800)
  })
  socket.on('connect_error', (err) => {
    connectionNote.value = `Connect error: ${err?.message || err}`
  })
  socket.on('connect:ok', () => {
    // server ack
  })

  // ---- Signaling ----
  socket.on('webrtc:offer', async (data) => {
    const { channel, description } = data || {}
    if (!channel || !description) return
    // Принимаем только своё (по viewerKey и streamerId)
    if (channel.viewerKey !== viewerKey) return
    if (streamerId != null && channel.streamerId !== streamerId) return
    await handleRemoteDescription(description)
  })

  socket.on('webrtc:answer', async (data) => {
    const { channel, description } = data || {}
    if (!channel || !description) return
    if (channel.viewerKey !== viewerKey) return
    if (streamerId != null && channel.streamerId !== streamerId) return
    await handleRemoteDescription(description)
  })

  socket.on('webrtc:ice', async (data) => {
    const { channel, candidate } = data || {}
    if (!channel || !candidate) return
    if (channel.viewerKey !== viewerKey) return
    if (streamerId != null && channel.streamerId !== streamerId) return
    if (!pc) return

    if (!pc.remoteDescription) {
      ctx.pendingCandidates.push(candidate)
    } else {
      try { await pc.addIceCandidate(candidate) }
      catch (err) { if (!ctx.ignoreOffer) console.warn('addIceCandidate error', err) }
    }
  })
}

/**
 * ====== UI ======
 */
function toggleMute() {
  const v = remoteVideo.value
  if (!v) return
  muted.value = !muted.value
  v.muted = muted.value
}

/**
 * ====== LIFECYCLE ======
 */
onMounted(() => {
  createPC()

  socket = io(`${config.apiUrl}${NAMESPACE}`, {
    auth: { token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiaWF0IjoxNzYyNzExNzM2LCJleHAiOjE3NjUzMDM3MzZ9.18L6f6NKovBucGQTFJHoN80GMwUPbQl1JybgqjQEUIk' },
    // зрителю обязательно указать streamer_id (сервер этого ждёт)
    query: streamerId != null ? { streamer_id: String(streamerId) } : {},
    autoConnect: true,
    transports: ['websocket', 'polling']
  })
  attachSocketHandlers()

  // Пингуем бэк для слежения за онлайном
  pingTimer = setInterval(() => {
    try { socket.emit('ping', {}) } catch (_) {}
  }, 10_000)

  // На случай, если negotiationneeded не сработает — включим автоцикл
  scheduleAutoOffer(800)
})

onBeforeUnmount(() => {
  clearTimeout(autoOfferTimer)
  clearInterval(pingTimer)
  try { socket?.disconnect() } catch (_) {}
  try { pc?.close() } catch (_) {}
})

</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; padding: 20px; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
header { display: flex; align-items: baseline; gap: 16px; }
.status { color: #666; font-size: 14px; }
.dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; background:#bbb; vertical-align:middle; }
.dot.on { background:#2ecc71; }
.dot.off { background:#e74c3c; }
.video-box { position: relative; width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 8px; overflow: hidden; }
video { width: 100%; height: 100%; object-fit: cover; background:#000; }
.overlay { position: absolute; inset: 0; display:flex; justify-content: space-between; align-items: flex-start; pointer-events: none; }
.badge { margin: 12px; background: rgba(0,0,0,.6); color: #fff; padding: 6px 10px; border-radius: 6px; font-size: 12px; }
.mute { pointer-events: all; margin: 12px; padding:8px 12px; border-radius:8px; border:1px solid #ddd; background:#fff; cursor:pointer; }
.debug { margin-top: 16px; }
pre { background:#f8f8f8; padding:10px; border-radius:8px; overflow:auto; }
</style>
