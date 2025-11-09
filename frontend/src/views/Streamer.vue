<template>
  <div class="page">
    <header>
      <h1>Streamer</h1>
      <div class="status">
        <span :class="['dot', socketConnected ? 'on' : 'off']"></span>
        {{ socketConnected ? 'Socket connected' : 'Socket disconnected' }}
        <span v-if="connectionNote"> · {{ connectionNote }}</span>
      </div>
    </header>

    <main>
      <div class="video-box">
        <video ref="localVideo" autoplay playsinline muted></video>
        <div class="overlay">
          <div class="badge">Your camera</div>
        </div>
      </div>

      <div class="controls">
        <button @click="startCamera" :disabled="mediaActive">Start camera</button>
        <button @click="stopCamera" :disabled="!mediaActive">Stop camera</button>
        <button @click="toggleMic" :disabled="!mediaActive">
          {{ micEnabled ? 'Mute mic' : 'Unmute mic' }}
        </button>
        <button @click="restartAllIce">Restart ICE (all viewers)</button>
      </div>

      <details class="debug">
        <summary>Debug info</summary>
        <pre>explicitStreamerId: {{ explicitStreamerId ?? 'none' }}</pre>
        <pre>learnedStreamerId: {{ learnedStreamerId ?? 'none' }}</pre>
        <pre>viewers: {{ Array.from(peers.keys()) }}</pre>
        <pre>socketId: {{ socketId || '—' }}</pre>
      </details>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { io } from 'socket.io-client'

/**
 * ====== CONFIG ======
 * Задайте адрес сигналинга при необходимости (по умолчанию — текущий origin).
 * Если сервер сокетов на другом домене/порте, укажите его явно.
 */
const SIGNALING_URL = 'http://localhost:8000'
const NAMESPACE = '/streamers'
const ICE_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }]

/**
 * ====== UTILS ======
 */
function qs(name) {
  const m = new URLSearchParams(window.location.search).get(name)
  return m ?? null
}
function getToken() {
  const fromQS = qs('token')
  if (fromQS) return fromQS
  try { return localStorage.getItem('token') } catch (_) { return null }
}

/**
 * ====== STATE ======
 */
const localVideo = ref(null)
const socketConnected = ref(false)
const socketId = ref(null)
const connectionNote = ref('')
const mediaActive = ref(false)
const micEnabled = ref(true)

// Если в адресе указан ?streamer_id=..., будем по нему фильтровать
const explicitStreamerId = qs('streamer_id') ? Number(qs('streamer_id')) : null
// Если id стримера не задан явно, выведем его из первого валидного сигнала зрителя
const learnedStreamerId = ref(null)

// Медиапоток
let localStream = null

// Сокет
let socket = null
let pingTimer = null

// Карта viewerKey -> peerCtx
const peers = new Map()

/**
 * ====== PEER CTX / PERFECT NEGOTIATION ======
 */
function createPeerCtx(viewerKey, channel) {
  const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS })

  // Perfect negotiation flags
  const ctx = {
    pc,
    channel,                 // { streamerId, viewerKey }
    isPolite: false,         // стример — "impolite"
    makingOffer: false,
    isSettingRemoteAnswerPending: false,
    ignoreOffer: false,
    pendingCandidates: []
  }

  // Добавляем локальные треки (если камера уже включена)
  if (localStream) {
    localStream.getTracks().forEach(track => pc.addTrack(track, localStream))
  }

  pc.addEventListener('negotiationneeded', async () => {
    try {
      ctx.makingOffer = true
      // Если не стабилен — не лезем с новым offer (минимизация гларинга)
      if (pc.signalingState !== 'stable') {
        return
      }
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      emitSignal('webrtc:offer', {
        channel: ctx.channel,
        description: pc.localDescription
      })
    } catch (err) {
      console.error('[negotiationneeded] error', err)
    } finally {
      ctx.makingOffer = false
    }
  })

  pc.addEventListener('icecandidate', ({ candidate }) => {
    if (!candidate) return
    emitSignal('webrtc:ice', { channel: ctx.channel, candidate })
  })

  pc.addEventListener('iceconnectionstatechange', () => {
    const st = pc.iceConnectionState
    if (st === 'failed') {
      // Мягкий рестарт ICE
      try {
        pc.restartIce()
      } catch (_) {}
      // Триггерим переговорку
      pc.dispatchEvent(new Event('negotiationneeded'))
    }
  })

  pc.addEventListener('connectionstatechange', () => {
    const st = pc.connectionState
    if (st === 'connected') connectionNote.value = `Viewer ${viewerKey} connected`
    if (st === 'disconnected' || st === 'failed') connectionNote.value = `Viewer ${viewerKey} ${st}`
    if (st === 'closed') connectionNote.value = `Viewer ${viewerKey} closed`
  })

  return ctx
}

async function handleRemoteDescription(ctx, description) {
  const pc = ctx.pc
  const readyForOffer = !ctx.makingOffer && (pc.signalingState === 'stable' || ctx.isSettingRemoteAnswerPending)
  const offerCollision = description.type === 'offer' && !readyForOffer

  ctx.ignoreOffer = !ctx.isPolite && offerCollision
  if (ctx.ignoreOffer) {
    console.warn('[impolite] ignoring incoming offer due to glare')
    return
  }

  ctx.isSettingRemoteAnswerPending = description.type === 'answer'
  try {
    await pc.setRemoteDescription(description)
  } catch (err) {
    // Политный peer сделал бы rollback; здесь стример impolite, но обработаем на всякий случай
    if (description.type === 'offer') {
      try {
        await pc.setLocalDescription({ type: 'rollback' })
        await pc.setRemoteDescription(description)
      } catch (e) {
        console.error('[setRemoteDescription] failed even after rollback', e)
        return
      }
    } else {
      console.error('[setRemoteDescription] error', err)
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
      emitSignal('webrtc:answer', {
        channel: ctx.channel,
        description: pc.localDescription
      })
    } catch (err) {
      console.error('[createAnswer] error', err)
    }
  }
}

/**
 * ====== SOCKET SIGNALING ======
 */
function emitSignal(event, payload) {
  // Сервер ретранслирует всем в namespace; клиенты фильтруют по channel
  socket?.emit(event, payload)
}

function channelMatchesForStreamer(ch) {
  // Если задан явный streamer_id — пропускаем только его
  if (explicitStreamerId != null) return ch?.streamerId === explicitStreamerId
  // Иначе, если уже "выучили" свой id — тоже фильтруем
  if (learnedStreamerId.value != null) return ch?.streamerId === learnedStreamerId.value
  // Иначе принимаем первый валидный сигнал и запоминаем id
  if (typeof ch?.streamerId === 'number') {
    learnedStreamerId.value = ch.streamerId
    return true
  }
  return true // в одностримерной среде
}

function getOrCreatePeer(viewerKey, streamerIdFromSignal) {
  let ctx = peers.get(viewerKey)
  if (!ctx) {
    const channel = { streamerId: streamerIdFromSignal ?? explicitStreamerId ?? learnedStreamerId.value ?? null, viewerKey }
    ctx = createPeerCtx(viewerKey, channel)
    peers.set(viewerKey, ctx)
    // Если позже включим камеру — добросим треки в этот PC
    if (localStream) {
      localStream.getTracks().forEach(track => ctx.pc.addTrack(track, localStream))
    }
  } else {
    // Обновим streamerId, если ранее не знали
    if (ctx.channel.streamerId == null && streamerIdFromSignal != null) {
      ctx.channel.streamerId = streamerIdFromSignal
    }
  }
  return ctx
}

function attachSocketHandlers() {
  socket.on('connect', () => {
    socketConnected.value = true
    socketId.value = socket.id
    connectionNote.value = 'Connected to signaling'
  })
  socket.on('disconnect', () => {
    socketConnected.value = false
    socketId.value = null
  })
  socket.on('connect_error', (err) => {
    connectionNote.value = `Connect error: ${err?.message || err}`
  })
  socket.on('connect:ok', () => {
    // server-side ack, можно дергать ping
  })

  // ---- Signaling ----
  socket.on('webrtc:offer', async (data) => {
    try {
      const { channel, description } = data || {}
      if (!channel || !description || !channel.viewerKey) return
      if (!channelMatchesForStreamer(channel)) return

      const ctx = getOrCreatePeer(channel.viewerKey, channel.streamerId)
      await handleRemoteDescription(ctx, description)
    } catch (e) {
      console.error('handle offer error', e)
    }
  })

  socket.on('webrtc:answer', async (data) => {
    try {
      const { channel, description } = data || {}
      if (!channel || !description || !channel.viewerKey) return
      if (!channelMatchesForStreamer(channel)) return

      const ctx = getOrCreatePeer(channel.viewerKey, channel.streamerId)
      await handleRemoteDescription(ctx, description)
    } catch (e) {
      console.error('handle answer error', e)
    }
  })

  socket.on('webrtc:ice', async (data) => {
    try {
      const { channel, candidate } = data || {}
      if (!channel || !candidate || !channel.viewerKey) return
      if (!channelMatchesForStreamer(channel)) return

      const ctx = getOrCreatePeer(channel.viewerKey, channel.streamerId)
      const pc = ctx.pc
      // Если remoteDescription ещё не установлено — отложим
      if (!pc.remoteDescription) {
        ctx.pendingCandidates.push(candidate)
      } else {
        try {
          await pc.addIceCandidate(candidate)
        } catch (err) {
          // Если игнорируем оффер из-за гларинга — игнорим и candidate
          if (!ctx.ignoreOffer) console.warn('addIceCandidate error', err)
        }
      }
    } catch (e) {
      console.error('handle ice error', e)
    }
  })
}

/**
 * ====== CAMERA / CONTROLS ======
 */
async function startCamera() {
  try {
    if (mediaActive.value) return
    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    localVideo.value.srcObject = localStream
    mediaActive.value = true
    micEnabled.value = true
    // Раздать треки уже созданным PC (если кто-то постучался раньше нас)
    for (const ctx of peers.values()) {
      localStream.getTracks().forEach(track => ctx.pc.addTrack(track, localStream))
    }
  } catch (err) {
    connectionNote.value = `Cannot start camera: ${err?.message || err}`
  }
}
function stopCamera() {
  if (!localStream) return
  localStream.getTracks().forEach(t => t.stop())
  localStream = null
  mediaActive.value = false
  micEnabled.value = false
  if (localVideo.value) localVideo.value.srcObject = null
}
function toggleMic() {
  if (!localStream) return
  const at = localStream.getAudioTracks()
  at.forEach(t => (t.enabled = !t.enabled))
  micEnabled.value = at.every(t => t.enabled)
}
function restartAllIce() {
  for (const ctx of peers.values()) {
    try { ctx.pc.restartIce(); } catch (_) {}
    ctx.pc.dispatchEvent(new Event('negotiationneeded'))
  }
}

/**
 * ====== LIFECYCLE ======
 */
onMounted(async () => {
  // 1) Подключаемся к серверу
  socket = io(`${SIGNALING_URL}${NAMESPACE}`, {
    auth: { token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiaWF0IjoxNzYyNzExNjg4LCJleHAiOjE3NjUzMDM2ODh9._oX0nQazoczBHDvIGvH06UpfSlYH4o653GZROAfSMcg' },
    autoConnect: true,
    transports: ['websocket']
  })
  attachSocketHandlers()

  // 2) Периодический ping (держим присутствие на бэке)
  pingTimer = setInterval(() => {
    try { socket.emit('ping', {}) } catch (_) {}
  }, 10_000)

  // 3) Сразу пытаемся включить камеру
  await startCamera()
})

onBeforeUnmount(() => {
  clearInterval(pingTimer)
  for (const ctx of peers.values()) {
    try { ctx.pc.close() } catch (_) {}
  }
  peers.clear()
  stopCamera()
  try { socket?.disconnect() } catch (_) {}
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
.overlay { position: absolute; inset: 0; pointer-events: none; }
.badge { position: absolute; left: 12px; top: 12px; background: rgba(0,0,0,.6); color: #fff; padding: 6px 10px; border-radius: 6px; font-size: 12px; }
.controls { display:flex; gap:12px; margin-top: 16px; flex-wrap: wrap; }
button { padding:8px 12px; border-radius:8px; border:1px solid #ddd; background:#fff; cursor:pointer; }
button:disabled { opacity:.5; cursor:default; }
.debug { margin-top: 16px; }
pre { background:#f8f8f8; padding:10px; border-radius:8px; overflow:auto; }
</style>
