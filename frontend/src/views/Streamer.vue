<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import { io, type Socket } from 'socket.io-client'
import Cookies from 'js-cookie'
import { config } from '@/config'

const token = Cookies.get('access_token')

const rtcConfig: RTCConfiguration = {
  iceServers: [
    { urls: 'stun:nex2ilo.com:3478' },
    { urls: 'turn:nex2ilo.com:3478', username: 'kazgirls', credential: '9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN' },
    { urls: 'turns:nex2ilo.com:5349', username: 'kazgirls', credential: '9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN' },
  ],
  iceTransportPolicy: 'all',
}

/** ===== types ===== */
type PcKey = 's2v' | 'v2s'
type Signal<T> = { pcKey: PcKey; payload: T }
type OfferMsg = Signal<RTCSessionDescriptionInit>
type AnswerMsg = Signal<RTCSessionDescriptionInit>
type IceMsg = Signal<RTCIceCandidateInit>

type ServerToClientEvents = {
  'webrtc:offer': (msg: OfferMsg) => void
  'webrtc:answer': (msg: AnswerMsg) => void
  'webrtc:ice': (msg: IceMsg) => void
}
type ClientToServerEvents = {
  'webrtc:offer': (msg: OfferMsg) => void
  'webrtc:answer': (msg: AnswerMsg) => void
  'webrtc:ice': (msg: IceMsg) => void
}

/** ===== ui ===== */
const localVideo = ref<HTMLVideoElement | null>(null)   // камера стримера (превью)
const remoteVideo = ref<HTMLVideoElement | null>(null)  // экран от viewer

/** ===== state ===== */
const socket = shallowRef<Socket<ServerToClientEvents, ClientToServerEvents> | null>(null)

const pcS2V = shallowRef<RTCPeerConnection | null>(null) // Streamer -> Viewer (camera)
const pcV2S = shallowRef<RTCPeerConnection | null>(null) // Viewer -> Streamer (screen)

const localCameraStream = shallowRef<MediaStream | null>(null)
const remoteScreenStream = shallowRef<MediaStream | null>(null)

const logs = ref<string[]>([])
const safeJson = (v: unknown) => { try { return JSON.stringify(v) } catch { return String(v) } }
const log = (m: string, data?: unknown) => {
  const line = `[Streamer] ${new Date().toISOString()} ${m}${data ? ' ' + safeJson(data) : ''} ${window.location.href}`
  logs.value.unshift(line)
  console.log(line)
}

/** ===== helpers ===== */
function emitOffer(pcKey: PcKey, sdp: RTCSessionDescriptionInit) {
  socket.value?.emit('webrtc:offer', { pcKey, payload: sdp })
}
function emitAnswer(pcKey: PcKey, sdp: RTCSessionDescriptionInit) {
  socket.value?.emit('webrtc:answer', { pcKey, payload: sdp })
}
function emitIce(pcKey: PcKey, c: RTCIceCandidateInit) {
  socket.value?.emit('webrtc:ice', { pcKey, payload: c })
}
function pickPc(pcKey: PcKey) {
  return pcKey === 's2v' ? pcS2V.value : pcV2S.value
}

function attachRemoteScreen() {
  const el = remoteVideo.value
  const stream = remoteScreenStream.value
  if (!el || !stream) return
  el.srcObject = stream
  el.playsInline = true
  el.autoplay = true
  el.muted = true // чтобы autoplay на мобилках не блокировался
  el.play().then(() => log('remoteScreen play OK')).catch(e => log('remoteScreen play BLOCKED', String(e)))
}

/** ===== socket ===== */
function connectSocket() {
  if (socket.value) return
  log('connectSocket()')

  const s = io(`${config.url}/streamers`, {
    auth: { token },
    autoConnect: true,
    transports: ['websocket'],
  })
  socket.value = s

  s.on('connect', () => log(`socket connected id=${s.id}`))
  s.on('disconnect', (r) => log(`socket disconnected reason=${r}`))

  const pendingIce: RTCIceCandidateInit[] = []

  // viewer прислал offer (это будет v2s: viewer -> streamer)
  s.on('webrtc:offer', async (msg) => {
    log('<= webrtc:offer', { pcKey: msg.pcKey, type: msg.payload.type, sdpLen: msg.payload.sdp?.length })

    if (msg.pcKey !== 'v2s') {
      // offer для s2v должен делать только стример, viewer не шлёт s2v-offer
      return
    }

    if (!pcV2S.value) pcV2S.value = createPcReceiver('v2s')
    const conn = pcV2S.value!

    await conn.setRemoteDescription(msg.payload)
    log('pcV2S setRemoteDescription(offer) done')

    for (const c of pendingIce) {
      await conn.addIceCandidate(c)
    }
    pendingIce.length = 0

    const answer = await conn.createAnswer()
    await conn.setLocalDescription(answer)
    log('pcV2S setLocalDescription(answer) done')

    emitAnswer('v2s', conn.localDescription!)
    log('=> webrtc:answer (v2s)')
  })

  // viewer ответил на наш offer (это s2v)
  s.on('webrtc:answer', async (msg) => {
    log('<= webrtc:answer', { pcKey: msg.pcKey, type: msg.payload.type, sdpLen: msg.payload.sdp?.length })

    if (msg.pcKey !== 's2v') return
    const conn = pcS2V.value
    if (!conn) return log('pcS2V is null, ignore answer')

    await conn.setRemoteDescription(msg.payload)
    log('pcS2V setRemoteDescription(answer) done')

    for (const c of pendingIce) {
      await conn.addIceCandidate(c)
    }
    pendingIce.length = 0
  })

  // ICE для обоих направлений
  s.on('webrtc:ice', async (msg) => {
    const conn = pickPc(msg.pcKey)
    if (!conn) return

    if (!conn.remoteDescription) {
      pendingIce.push(msg.payload)
      return
    }

    await conn.addIceCandidate(msg.payload)
  })
}

/** ===== webrtc: create PC ===== */
function commonPcLogs(conn: RTCPeerConnection, name: string) {
  conn.onicegatheringstatechange = () => log(`[${name}] iceGatheringState=${conn.iceGatheringState}`)
  conn.oniceconnectionstatechange = () => log(`[${name}] iceConnectionState=${conn.iceConnectionState}`)
  conn.onconnectionstatechange = () => log(`[${name}] connectionState=${conn.connectionState}`)
  conn.onsignalingstatechange = () => log(`[${name}] signalingState=${conn.signalingState}`)
}

function createPcSender(pcKey: PcKey): RTCPeerConnection {
  const conn = new RTCPeerConnection(rtcConfig)
  commonPcLogs(conn, `pc-${pcKey}`)

  conn.onicecandidate = (e) => {
    if (!e.candidate) return log(`[pc-${pcKey}] onicecandidate: null`)
    emitIce(pcKey, e.candidate.toJSON())
    log(`[pc-${pcKey}] => ice`)
  }

  return conn
}

function createPcReceiver(pcKey: PcKey): RTCPeerConnection {
  const conn = new RTCPeerConnection(rtcConfig)
  commonPcLogs(conn, `pc-${pcKey}`)

  conn.onicecandidate = (e) => {
    if (!e.candidate) return log(`[pc-${pcKey}] onicecandidate: null`)
    emitIce(pcKey, e.candidate.toJSON())
    log(`[pc-${pcKey}] => ice`)
  }

  conn.ontrack = (ev) => {
    log(`[pc-${pcKey}] ontrack`, { kind: ev.track.kind, id: ev.track.id, streams: ev.streams.map(s => s.id) })

    // viewer шлёт screen — он придёт сюда (видео+аудио может не быть)
    if (ev.streams[0]) {
      remoteScreenStream.value = ev.streams[0]
    } else {
      if (!remoteScreenStream.value) remoteScreenStream.value = new MediaStream()
      remoteScreenStream.value.addTrack(ev.track)
    }
    attachRemoteScreen()
  }

  // receiver ждёт входящие
  conn.addTransceiver('video', { direction: 'recvonly' })
  conn.addTransceiver('audio', { direction: 'recvonly' })
  log(`[pc-${pcKey}] addTransceiver(recvonly)`)

  return conn
}

/** ===== actions ===== */
// 1) Streamer -> Viewer: camera
async function startCameraToViewer() {
  if (!socket.value) log('WARNING: socket not connected yet (connectSocket())')

  log('startCameraToViewer(): getUserMedia')
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
  localCameraStream.value = stream

  if (localVideo.value) localVideo.value.srcObject = stream
  log('camera stream ready', { tracks: stream.getTracks().map(t => ({ kind: t.kind, id: t.id })) })

  const conn = createPcSender('s2v')
  pcS2V.value = conn

  for (const track of stream.getTracks()) {
    conn.addTrack(track, stream)
    log('[pc-s2v] addTrack', { kind: track.kind, id: track.id })
  }

  const offer = await conn.createOffer()
  await conn.setLocalDescription(offer)
  log('[pc-s2v] setLocalDescription(offer) done')

  emitOffer('s2v', conn.localDescription!)
  log('=> webrtc:offer (s2v)')
}

function stopAll() {
  log('stopAll()')

  if (pcS2V.value) { pcS2V.value.close(); pcS2V.value = null; log('pcS2V closed') }
  if (pcV2S.value) { pcV2S.value.close(); pcV2S.value = null; log('pcV2S closed') }

  if (localCameraStream.value) {
    localCameraStream.value.getTracks().forEach(t => t.stop())
    localCameraStream.value = null
    log('camera tracks stopped')
  }
  if (localVideo.value) localVideo.value.srcObject = null

  remoteScreenStream.value = null
  if (remoteVideo.value) remoteVideo.value.srcObject = null

  if (socket.value) { socket.value.disconnect(); socket.value = null; log('socket disconnected') }
}

onMounted(connectSocket)
onBeforeUnmount(stopAll)
</script>

<template>
  <div style="display:grid; gap:12px; max-width: 980px;">
    <h2>Streamer</h2>

    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <button @click="connectSocket">Connect socket</button>
      <button @click="startCameraToViewer">Start camera → viewer (s2v)</button>
      <button @click="stopAll">Stop</button>
    </div>

    <div style="display:flex; gap:16px; flex-wrap:wrap;">
      <div>
        <div style="margin-bottom:6px;">Local camera (preview)</div>
        <video ref="localVideo" autoplay playsinline muted style="width:320px; background:#111;"></video>
      </div>

      <div>
        <div style="margin-bottom:6px;">Remote screen from viewer (v2s)</div>
        <video ref="remoteVideo" autoplay playsinline muted style="width:520px; background:#111;"></video>
      </div>
    </div>

    <details open>
      <summary>Logs</summary>
      <pre style="white-space:pre-wrap; background:#0b0b0b; color:#ddd; padding:12px; border-radius:8px; max-height:320px; overflow:auto;">{{ logs.join('\n') }}</pre>
    </details>
  </div>
</template>
