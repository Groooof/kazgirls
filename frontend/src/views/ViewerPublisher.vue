<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import { io, type Socket } from 'socket.io-client'
import Cookies from 'js-cookie'
import { config } from '@/config'
import { useRoute } from 'vue-router'

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
  'webrtc:answer': (sdp: AnswerMsg) => void
  'webrtc:ice': (candidate: IceMsg) => void
}
type ClientToServerEvents = {
  'webrtc:offer': (sdp: OfferMsg) => void
  'webrtc:ice': (candidate: IceMsg) => void
}

const route = useRoute()

const localVideo = ref<HTMLVideoElement | null>(null)
const streamerId = Number(route.params.id)

const socket = shallowRef<Socket<ServerToClientEvents, ClientToServerEvents> | null>(null)
const pc = shallowRef<RTCPeerConnection | null>(null)
const localStream = shallowRef<MediaStream | null>(null)

const logs = ref<string[]>([])
const log = (m: string, data?: unknown) => {
  const line = `[Viewer→Stream] ${new Date().toISOString()} ${m}${data ? ' ' + safeJson(data) : ''}`
  logs.value.unshift(line)
  console.log(line)
}
const safeJson = (v: unknown) => { try { return JSON.stringify(v) } catch { return String(v) } }

function connectSocket() {
  if (socket.value) return
  log('connectSocket()')

  const s = io(`${config.url}/streamers`, {
    auth: { token },
    autoConnect: true,
    query: { streamer_id: String(streamerId) },
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 500,
    reconnectionDelayMax: 5000,
  })
  socket.value = s

  s.on('connect', () => log(`socket connected id=${s.id}`))
  s.on('disconnect', (r) => log(`socket disconnected reason=${r}`))

  s.on('webrtc:answer', async (answer) => {
    log('<= webrtc:answer', { type: answer.type, sdpLen: answer.sdp?.length })
    const conn = pc.value
    if (!conn) return log('pc is null, ignore answer')
    await conn.setRemoteDescription(answer)
    log('setRemoteDescription(answer) done')
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

async function startPublish() {
  if (!socket.value) log('WARNING: socket not connected yet (connectSocket())')

  log('getUserMedia()')
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
  localStream.value = stream
  if (localVideo.value) localVideo.value.srcObject = stream
  log('local stream ready', { tracks: stream.getTracks().map(t => ({ kind: t.kind, id: t.id })) })

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

  for (const track of stream.getTracks()) {
    conn.addTrack(track, stream)
    log('addTrack()', { kind: track.kind, id: track.id })
  }

  log('createOffer()')
  const offer = await conn.createOffer()
  await conn.setLocalDescription(offer)
  log('setLocalDescription(offer) done', { type: conn.localDescription?.type, sdpLen: conn.localDescription?.sdp?.length })

  const payload: OfferMsg = conn.localDescription!
  log('=> webrtc:offer', { type: payload.type, sdpLen: payload.sdp?.length })
  socket.value?.emit('webrtc:offer', payload)
}

function stop() {
  log('stop()')

  if (pc.value) { pc.value.close(); pc.value = null; log('pc closed') }

  if (localStream.value) {
    localStream.value.getTracks().forEach(t => t.stop())
    localStream.value = null
    log('local tracks stopped')
  }
  if (localVideo.value) localVideo.value.srcObject = null

  if (socket.value) { socket.value.disconnect(); socket.value = null; log('socket disconnected') }
}

onMounted(connectSocket)
onBeforeUnmount(stop)
</script>

<template>
  <div style="display:grid; gap:12px; max-width: 980px;">
    <h2>Viewer publishes stream → Streamer receives</h2>

    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <button @click="connectSocket">Connect socket</button>
      <button @click="startPublish">Start Publish (send offer)</button>
      <button @click="stop">Stop</button>
    </div>

    <video ref="localVideo" autoplay playsinline muted style="width:420px; background:#111;"></video>

    <details open>
      <summary>Logs</summary>
      <pre style="white-space:pre-wrap; background:#0b0b0b; color:#ddd; padding:12px; border-radius:8px; max-height:320px; overflow:auto;">{{ logs.join('\n') }}</pre>
    </details>
  </div>
</template>
