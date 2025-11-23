<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
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

const playerRef = ref<InstanceType<typeof VideoPlayer> | null>(null)
const isPip = ref(false)

// простой флаг, чтобы не дергать cleanup одновременно из разных мест
let isCleaningUp = false

const createPeerConnection = () => {
  console.log('[VIEWER] createPeerConnection')
  const peer = new RTCPeerConnection(rtcConfig)
  pc.value = peer

  remoteStream.value = new MediaStream()

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

    // если трек закончился — можно подчиститься
    event.track.onended = () => {
      console.log('[VIEWER] track ended', event.track.kind)
    }
  }

  peer.onconnectionstatechange = () => {
    const state = peer.connectionState
    console.log('[VIEWER] connection state:', state)

    if (state === 'failed' || state === 'disconnected' || state === 'closed') {
      console.log('[VIEWER] cleaning up after connection state', state)
      cleanupConnection()
      // дальше просто ждём нового offer от стримера
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

  isCleaningUp = false
}

// обработка offer от стримера — ВСЕГДА начинаем с чистого PC
const handleOffer = async (offer: RTCSessionDescriptionInit) => {
  console.log('[VIEWER] handleOffer start')

  // убиваем старый PC/стрим
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

  // максимально живучий клиент socket.io
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
    // чистим текущее WebRTC-состояние, но оставляем socket —
    // socket.io сам попытается переподключиться
    cleanupConnection()
  })

  socket.value.on('connect_error', (err) => {
    console.error('[VIEWER] connect_error', err?.message || err)
  })

  socket.value.on('reconnect_attempt', (n) => {
    console.log('[VIEWER] reconnect_attempt', n)
  })

  socket.value.on('reconnect', (n) => {
    console.log('[VIEWER] reconnect success', n)
    isSocketConnected.value = true
    socket.value?.emit('join_stream', {
      streamerId,
      role: 'viewer',
    })
  })

  socket.value.on('reconnect_error', (err) => {
    console.error('[VIEWER] reconnect_error', err?.message || err)
  })

  socket.value.on('reconnect_failed', () => {
    console.error('[VIEWER] reconnect_failed')
  })

  // === WebRTC signaling ===

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

// PiP можно пока не трогаем — оставляем твою логику как есть
const handleVisibilityChange = async () => {
  const player = playerRef.value
  const video = player?.getVideoElement?.()

  if (!video) return
  if (!remoteStream.value) return

  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return

  const docAny = document as any
  const videoAny = video as any

  const hasStandardPiP =
    'pictureInPictureEnabled' in document &&
    typeof videoAny.requestPictureInPicture === 'function'

  const hasWebkitPiP =
    typeof videoAny.webkitSupportsPresentationMode === 'function' &&
    videoAny.webkitSupportsPresentationMode('picture-in-picture')

  const enterStandardPiP = async () => {
    if (!hasStandardPiP || !docAny.pictureInPictureEnabled) return
    if (docAny.pictureInPictureElement && docAny.pictureInPictureElement !== video) return
    if (docAny.pictureInPictureElement === video) return
    try {
      await videoAny.requestPictureInPicture()
      console.log('[VIEWER] entered PiP (standard)')
    } catch (e) {
      console.error('[VIEWER] requestPictureInPicture error', e)
    }
  }

  const exitStandardPiP = async () => {
    if (docAny.pictureInPictureElement === video) {
      try {
        await docAny.exitPictureInPicture()
        console.log('[VIEWER] exit PiP (standard)')
      } catch (e) {
        console.error('[VIEWER] exitPictureInPicture error', e)
      }
    }
  }

  const enterWebkitPiP = () => {
    try {
      videoAny.webkitSetPresentationMode('picture-in-picture')
      console.log('[VIEWER] entered PiP (webkit)')
    } catch (e) {
      console.error('[VIEWER] webkitSetPresentationMode(pip) error', e)
    }
  }

  const exitWebkitPiP = () => {
    try {
      if (videoAny.webkitPresentationMode === 'picture-in-picture') {
        videoAny.webkitSetPresentationMode('inline')
        console.log('[VIEWER] exit PiP (webkit)')
      }
    } catch (e) {
      console.error('[VIEWER] webkitSetPresentationMode(inline) error', e)
    }
  }

  const enterPiP = async () => {
    if (hasStandardPiP) await enterStandardPiP()
    else if (hasWebkitPiP) enterWebkitPiP()
  }

  const exitPiP = async () => {
    if (hasStandardPiP) await exitStandardPiP()
    else if (hasWebkitPiP) exitWebkitPiP()
  }

  if (document.visibilityState === 'hidden') {
    await enterPiP()
  } else if (document.visibilityState === 'visible') {
    await exitPiP()
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
  <div>
    <h1>Viewer for streamer #{{ streamerId }}</h1>

    <p v-if="!isSocketConnected">
      Подключение к сокету...
    </p>

    <div style="max-width: 600px;">
      <VideoPlayer ref="playerRef" :src-object="remoteStream" @get-pip-mode="val => isPip = val" />
    </div>

    <p>
      Ждём, когда стример запустит стрим...
    </p>
  </div>
</template>
