<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { io, Socket } from 'socket.io-client'
import VideoPlayer from './VideoPlayer.vue'
import axios from 'axios'
import { config } from '@/config'

const isProd = true

const route = useRoute()
const streamerId = isProd ? 4 : 2

const rtcConfig: RTCConfiguration = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
  ],
}

const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)

const remoteStream = ref<MediaStream | null>(null)
const isSocketConnected = ref(false)

const playerRef = ref<InstanceType<typeof VideoPlayer> | null>(null)
const isPip = ref(false)

const initSocket = (access_token: string) => {
  if (isProd) {
    socket.value = io(`${config.apiUrl}/streamers`, {
      auth: { token: access_token },
      autoConnect: true,
      query: { streamer_id: String(streamerId) },
      transports: ['websocket', 'polling'],
    })
  } else {
    socket.value = io('http://localhost:8000/streamers', {
      auth: { token: access_token },
      autoConnect: true,
      query: { streamer_id: String(streamerId) },
      transports: ['websocket', 'polling'],
    })
  }

  socket.value.on('connect', () => {
    console.log('[VIEWER] socket connected')
    isSocketConnected.value = true

    socket.value?.emit('join_stream', {
      streamerId,
      role: 'viewer',
    })
  })

  socket.value.on('disconnect', () => {
    console.log('[VIEWER] socket disconnected')
    isSocketConnected.value = false
  })

  socket.value.on('webrtc:offer', async (payload: { streamerId: number; sdp: RTCSessionDescriptionInit }) => {
    console.log('[VIEWER] webrtc_offer received', payload)
    if (payload.streamerId !== streamerId) return
    await handleOffer(payload.sdp)
  })

  socket.value.on('webrtc:ice', async (payload: { streamerId: number; candidate: RTCIceCandidateInit }) => {
    console.log('[VIEWER] webrtc_ice_candidate received', payload)
    if (payload.streamerId !== streamerId) return
    if (!pc.value) return
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

const createPeerConnection = () => {
  console.log('[VIEWER] createPeerConnection')
  pc.value = new RTCPeerConnection(rtcConfig)

  remoteStream.value = new MediaStream()

  pc.value.onicecandidate = (event) => {
    console.log('[VIEWER] onicecandidate', event.candidate)
    if (event.candidate) {
      socket.value?.emit('webrtc:ice', {
        streamerId,
        candidate: event.candidate.toJSON(),
        from: 'viewer',
      })
    }
  }

  pc.value.ontrack = (event) => {
    console.log('[VIEWER] ontrack', event.streams, event.track)
    remoteStream.value!.addTrack(event.track)
  }

  pc.value.onconnectionstatechange = () => {
    const state = pc.value?.connectionState
    console.log('[VIEWER] connection state:', state)
    if (state === 'disconnected' || state === 'failed' || state === 'closed') {
      console.log('[VIEWER] cleaning up after disconnect')
      cleanupConnection()
    }
  }
}

const handleOffer = async (offer: RTCSessionDescriptionInit) => {
  console.log('[VIEWER] handleOffer start', offer)

  // всегда создаём новый PC, старый — под нож
  if (pc.value) {
    try {
      pc.value.getReceivers().forEach(r => r.track?.stop())
      pc.value.close()
    } catch (e) {
      console.warn('[VIEWER] error closing old pc', e)
    }
  }
  pc.value = null
  remoteStream.value = null

  createPeerConnection()
  if (!pc.value) return

  await pc.value.setRemoteDescription(new RTCSessionDescription(offer))
  console.log('[VIEWER] setRemoteDescription done')

  const answer = await pc.value.createAnswer()
  console.log('[VIEWER] createAnswer done', answer)

  await pc.value.setLocalDescription(answer)
  console.log('[VIEWER] setLocalDescription done')

  socket.value?.emit('webrtc:answer', {
    streamerId,
    sdp: answer,
  })
  console.log('[VIEWER] answer sent')
}

const cleanupConnection = () => {
  pc.value?.getReceivers().forEach((receiver) => receiver.track?.stop())
  pc.value?.close()
  pc.value = null

  remoteStream.value?.getTracks().forEach((t) => t.stop())
  remoteStream.value = null
}

const handleVisibilityChange = async () => {
  const player = playerRef.value
  const video = player?.getVideoElement?.()

  if (!video) return
  if (!remoteStream.value) return // нет стрима — нет PiP

  // Не пытаемся включать PiP, пока видео даже не начало играть
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    return
  }

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
    if (hasStandardPiP) {
      await enterStandardPiP()
    } else if (hasWebkitPiP) {
      enterWebkitPiP()
    } else {
      // Нет поддержки PiP — просто ничего не делаем
      console.log('[VIEWER] PiP not supported on this device')
    }
  }

  const exitPiP = async () => {
    if (hasStandardPiP) {
      await exitStandardPiP()
    } else if (hasWebkitPiP) {
      exitWebkitPiP()
    }
  }

  if (document.visibilityState === 'hidden') {
    // Пытаемся войти в PiP при сворачивании/уходе
    await enterPiP()
  } else if (document.visibilityState === 'visible') {
    // При возврате на вкладку — выходим
    await exitPiP()
  }
}

const test = ref('')

onMounted(async() => {
  if (isProd) {
    const { data } = await axios.post('/api/v1/tokens/login', {
      username: "viewer_2",
      password: "test",
    })

    initSocket(data.access_token)
  } else {
    try {
      const { data } = await axios.post('http://localhost:8000/api/v1/tokens/login', {
        username: "girl",
        password: "test",
      })

      initSocket(data.access_token)
    } catch (err) {
      test.value = JSON.stringify(err)
    }
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  cleanupConnection()
  socket.value?.disconnect()

  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div>
    <h1>Viewer for streamer #{{ streamerId }}</h1>

    <p v-if="!isSocketConnected">
      Подключение к сокету...
    </p>

    <div style="max-width: 600px;">
      <VideoPlayer ref="playerRef" :src-object="remoteStream" />
    </div>

    <p>
      Ждём, когда стример запустит стрим...
    </p>

    {{ test }}
  </div>
</template>
