<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount, watch } from 'vue'
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

type OfferMsg = RTCSessionDescriptionInit
type AnswerMsg = RTCSessionDescriptionInit
type IceMsg = RTCIceCandidateInit

type ServerToClientEvents = {
  'webrtc:offer': (sdp: OfferMsg) => void
  'webrtc:ice': (candidate: IceMsg) => void
}
type ClientToServerEvents = {
  'webrtc:answer': (sdp: AnswerMsg) => void
  'webrtc:ice': (candidate: IceMsg) => void
}

const remoteVideo = ref<HTMLVideoElement | null>(null)

const socket = shallowRef<Socket<ServerToClientEvents, ClientToServerEvents> | null>(null)
const pc = shallowRef<RTCPeerConnection | null>(null)
const remoteStream = shallowRef<MediaStream | null>(null)

const logs = ref<string[]>([])
const log = (m: string, data?: unknown) => {
  const line = `[Streamer←Viewer] ${new Date().toISOString()} ${m}${data ? ' ' + safeJson(data) : ''}`
  logs.value.unshift(line)
  console.log(line)
}
const safeJson = (v: unknown) => { try { return JSON.stringify(v) } catch { return String(v) } }

function attachRemote() {
  const el = remoteVideo.value
  const stream = remoteStream.value
  if (!el || !stream) return

  el.srcObject = stream
  el.playsInline = true
  el.autoplay = true

  // На мобильных autoplay часто блокируется из-за аудио — стартуем muted
  el.muted = true

  el.play()
    .then(() => log('remoteVideo.play() OK'))
    .catch((e) => log('remoteVideo.play() BLOCKED', String(e)))
}

watch(remoteVideo, attachRemote)

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

  s.on('webrtc:offer', async (offer) => {
    log('<= webrtc:offer', { type: offer.type, sdpLen: offer.sdp?.length })

    if (!pc.value) createPeerConnection()
    const conn = pc.value
    if (!conn) return log('pc is null (unexpected)')

    await conn.setRemoteDescription(offer)
    log('setRemoteDescription(offer) done')

    const answer = await conn.createAnswer()
    await conn.setLocalDescription(answer)
    log('setLocalDescription(answer) done')

    const payload: AnswerMsg = conn.localDescription!
    log('=> webrtc:answer', { type: payload.type, sdpLen: payload.sdp?.length })
    socket.value?.emit('webrtc:answer', payload)
  })

  s.on('webrtc:ice', async (candidate) => {
    log('<= webrtc:ice', candidate)
    const conn = pc.value
    if (!conn) return log('pc is null, ignore ice')
    try {
      await conn.addIceCandidate(candidate)
      log('addIceCandidate(remote) done')
    } catch (e) {
      log('addIceCandidate(remote) ERROR', String(e))
    }
  })
}

function createPeerConnection() {
  log('create RTCPeerConnection', rtcConfig)
  const conn = new RTCPeerConnection(rtcConfig)
  pc.value = conn

  conn.onicegatheringstatechange = () => log(`iceGatheringState=${conn.iceGatheringState}`)
  conn.oniceconnectionstatechange = () => log(`iceConnectionState=${conn.iceConnectionState}`)
  conn.onconnectionstatechange = () => log(`connectionState=${conn.connectionState}`)
  conn.onsignalingstatechange = () => log(`signalingState=${conn.signalingState}`)

  conn.onicecandidate = (e) => {
    if (!e.candidate) return log('onicecandidate: null (gathering complete)')
    const msg: IceMsg = e.candidate.toJSON()
    log('=> webrtc:ice', msg)
    socket.value?.emit('webrtc:ice', msg)
  }

  conn.ontrack = (event) => {
    log('ontrack()', { kind: event.track.kind, id: event.track.id, streams: event.streams.map(s => s.id) })

    if (event.streams[0]) {
      remoteStream.value = event.streams[0]
    } else {
      if (!remoteStream.value) remoteStream.value = new MediaStream()
      remoteStream.value.addTrack(event.track)
    }

    attachRemote()
  }

  // Мы получатель: ожидаем входящие дорожки
  conn.addTransceiver('video', { direction: 'recvonly' })
  conn.addTransceiver('audio', { direction: 'recvonly' })
  log('addTransceiver(recvonly) for audio/video')
}

function stop() {
  log('stop()')
  if (pc.value) { pc.value.close(); pc.value = null; log('pc closed') }
  remoteStream.value = null
  if (remoteVideo.value) remoteVideo.value.srcObject = null
  if (socket.value) { socket.value.disconnect(); socket.value = null; log('socket disconnected') }
}

function unmute() {
  const el = remoteVideo.value
  if (!el) return
  el.muted = false
  el.play().catch(e => log('play after unmute failed', String(e)))
}

onMounted(connectSocket)
onBeforeUnmount(stop)
</script>

<template>
  <div style="display:grid; gap:12px; max-width: 980px;">
    <h2>Streamer receives stream ← Viewer publishes</h2>

    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <button @click="connectSocket">Connect socket</button>
      <button @click="unmute">Unmute</button>
      <button @click="stop">Stop</button>
    </div>

    <video ref="remoteVideo" autoplay playsinline muted style="width:720px; background:#111;"></video>

    <details open>
      <summary>Logs</summary>
      <pre style="white-space:pre-wrap; background:#0b0b0b; color:#ddd; padding:12px; border-radius:8px; max-height:320px; overflow:auto;">{{ logs.join('\n') }}</pre>
    </details>
  </div>
</template>
