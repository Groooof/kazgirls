<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import { io, type Socket } from 'socket.io-client'
import Cookies from 'js-cookie'
import { config } from '@/config'
import { useRoute } from 'vue-router'
import { getToken } from './token'

import { registerPlugin } from '@capacitor/core'

const ScreenShare = registerPlugin('ScreenShare')

// const token = Cookies.get('access_token')
const route = useRoute()
const streamerId = Number(route.params.id) // если сервер использует query для роутинга

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
const remoteVideo = ref<HTMLVideoElement | null>(null)  // камера стримера (s2v)
const localVideo = ref<HTMLVideoElement | null>(null)   // превью экрана viewer (v2s)

/** ===== state ===== */
const socket = shallowRef<Socket<ServerToClientEvents, ClientToServerEvents> | null>(null)

const pcS2V = shallowRef<RTCPeerConnection | null>(null) // Streamer -> Viewer (receive camera)
const pcV2S = shallowRef<RTCPeerConnection | null>(null) // Viewer -> Streamer (send screen)

const remoteCameraStream = shallowRef<MediaStream | null>(null)
const localScreenStream = shallowRef<MediaStream | null>(null)

const logs = ref<string[]>([])
const safeJson = (v: unknown) => { try { return JSON.stringify(v) } catch { return String(v) } }
const log = (m: string, data?: unknown) => {
  const line = `[Viewer] ${new Date().toISOString()} ${m}${data ? ' ' + safeJson(data) : ''}`
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

function attachRemoteCamera() {
  const el = remoteVideo.value
  const stream = remoteCameraStream.value
  if (!el || !stream) return
  el.srcObject = stream
  el.playsInline = true
  el.autoplay = true
  el.muted = true
  el.play().then(() => log('remote camera play OK')).catch(e => log('remote camera play BLOCKED', String(e)))
}

function attachLocalScreenPreview() {
  const el = localVideo.value
  const stream = localScreenStream.value
  if (!el || !stream) return
  el.srcObject = stream
  el.playsInline = true
  el.autoplay = true
  el.muted = true
  el.play().catch(() => {})
}

const tok = ref()

/** ===== socket ===== */
const connectSocket = async() => {
  if (socket.value) return
  log('connectSocket()')

  tok.value = await getToken()

  const s = io(`${config.url}/streamers`, {
    auth: { token: tok.value },
    autoConnect: true,
    query: { streamer_id: String(streamerId) }, // оставь если сервер так роутит
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 10,
    timeout: 10000,
  })
  socket.value = s

  log('route', { href: window.location.href, params: route.params, streamerId })
  log(tok.value)

  s.on('connect', () => log(`socket connected id=${s.id}`))
  s.on('disconnect', (r) => log(`socket disconnected reason=${r}`))

  // streamer прислал offer на s2v
  s.on('webrtc:offer', async (msg) => {
    log('<= webrtc:offer', { pcKey: msg.pcKey, type: msg.payload.type, sdpLen: msg.payload.sdp?.length })

    if (msg.pcKey !== 's2v') {
      // offer v2s должен слать только viewer (мы сами), поэтому игнор
      return
    }

    if (!pcS2V.value) pcS2V.value = createPcReceiver('s2v')
    const conn = pcS2V.value!

    await conn.setRemoteDescription(msg.payload)
    log('pcS2V setRemoteDescription(offer) done')

    const answer = await conn.createAnswer()
    await conn.setLocalDescription(answer)
    log('pcS2V setLocalDescription(answer) done')

    emitAnswer('s2v', conn.localDescription!)
    log('=> webrtc:answer (s2v)')
  })

  // streamer ответил на наш screen-offer (v2s)
  s.on('webrtc:answer', async (msg) => {
    if (msg.pcKey !== 'v2s') return
    await ScreenShare.setRemoteDescription({ sdp: msg.payload.sdp })
    
    // const conn = pcV2S.value
    // if (!conn) return log('pcV2S is null, ignore answer')

    // await conn.setRemoteDescription(msg.payload)
    log('pcV2S setRemoteDescription(answer) done')
  })

  // ICE для обоих направлений
  s.on('webrtc:ice', async (msg) => {
    if (msg.pcKey !== 'v2s') return
    await ScreenShare.addIceCandidate(msg.payload)
    
    // const conn = pickPc(msg.pcKey)
    // if (!conn) return log(`pc for ${msg.pcKey} is null, ignore ice`)

    // try {
    //   await conn.addIceCandidate(msg.payload)
    //   log(`addIceCandidate(remote) done pcKey=${msg.pcKey}`)
    // } catch (e) {
    //   log(`addIceCandidate(remote) ERROR pcKey=${msg.pcKey}`, String(e))
    // }
  })
}

/** ===== webrtc ===== */
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

    if (ev.streams[0]) {
      remoteCameraStream.value = ev.streams[0]
    } else {
      if (!remoteCameraStream.value) remoteCameraStream.value = new MediaStream()
      remoteCameraStream.value.addTrack(ev.track)
    }
    attachRemoteCamera()
  }

  conn.addTransceiver('video', { direction: 'recvonly' })
  conn.addTransceiver('audio', { direction: 'recvonly' })
  log(`[pc-${pcKey}] addTransceiver(recvonly)`)

  return conn
}

/** ===== actions ===== */
// 2) Viewer -> Streamer: screen share
async function startScreenToStreamer() {
  if (!socket.value) log('WARNING: socket not connected yet (connectSocket())')

  // В браузере: getDisplayMedia. На мобилке может быть ограничено.
  log('startScreenToStreamer(): getDisplayMedia')
  const screenStream = await navigator.mediaDevices.getDisplayMedia({
    video: true,
    audio: true, // может не поддерживаться/не даваться
  })

  localScreenStream.value = screenStream
  attachLocalScreenPreview()

  const conn = createPcSender('v2s')
  pcV2S.value = conn

  for (const track of screenStream.getTracks()) {
    conn.addTrack(track, screenStream)
    log('[pc-v2s] addTrack', { kind: track.kind, id: track.id })
  }

  const offer = await conn.createOffer()
  await conn.setLocalDescription(offer)
  log('[pc-v2s] setLocalDescription(offer) done')

  emitOffer('v2s', conn.localDescription!)
  log('=> webrtc:offer (v2s)')
}

function stopAll() {
  log('stopAll()')

  if (pcS2V.value) { pcS2V.value.close(); pcS2V.value = null; log('pcS2V closed') }
  if (pcV2S.value) { pcV2S.value.close(); pcV2S.value = null; log('pcV2S closed') }

  remoteCameraStream.value = null
  if (remoteVideo.value) remoteVideo.value.srcObject = null

  if (localScreenStream.value) {
    localScreenStream.value.getTracks().forEach(t => t.stop())
    localScreenStream.value = null
    log('screen tracks stopped')
  }
  if (localVideo.value) localVideo.value.srcObject = null

  if (socket.value) { socket.value.disconnect(); socket.value = null; log('socket disconnected') }
}

onMounted(async() => {
  await connectSocket()
})
onBeforeUnmount(stopAll)

async function startScreenToStreamerV2() {
  try {
    // Чистим старые листенеры, если нажимаем кнопку второй раз без перезагрузки
    await ScreenShare.removeAllListeners() 
    
    ScreenShare.addListener('onIceCandidate', (c) => {
      emitIce('v2s', c)
    })

    log('Calling ScreenShare.start()...')
    const offer = await ScreenShare.start()
    log('ScreenShare.start() success', offer)
    
    emitOffer('v2s', offer)
  } catch (e) {
    log('ScreenShare ERROR:', e)
    alert('Ошибка запуска стрима: ' + JSON.stringify(e))
  }
}
</script>

<template>
  <div style="display:grid; gap:12px; max-width: 980px;">
    <h2>Viewer ТЕЕЕСТ</h2>

    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <button @click="connectSocket">Connect socket</button>
      <button @click="startScreenToStreamerV2">Start screen → streamer (v2s)</button>
      <button @click="stopAll">Stop</button>
    </div>

    <div style="display:flex; gap:16px; flex-wrap:wrap;">
      <div>
        <div style="margin-bottom:6px;">Remote camera from streamer (s2v)</div>
        <video ref="remoteVideo" autoplay playsinline muted style="width:520px; background:#111;"></video>
      </div>

      <div>
        <div style="margin-bottom:6px;">Local screen preview (v2s)</div>
        <video ref="localVideo" autoplay playsinline muted style="width:320px; background:#111;"></video>
      </div>
    </div>

    <details open>
      <summary>Logs</summary>
      <pre style="white-space:pre-wrap; background:#0b0b0b; color:#ddd; padding:12px; border-radius:8px; max-height:320px; overflow:auto;">{{ logs.join('\n') }}</pre>
    </details>
  </div>
</template>
