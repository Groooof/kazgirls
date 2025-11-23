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
    if (!remoteStream.value) {
      remoteStream.value = new MediaStream()
    }
    remoteStream.value.addTrack(event.track)

    console.log('REMOTE_STREAM: ', remoteStream.value)
  }

  pc.value.onconnectionstatechange = () => {
    console.log('[VIEWER] connection state:', pc.value?.connectionState)
  }
}

const handleOffer = async (offer: RTCSessionDescriptionInit) => {
  console.log('[VIEWER] handleOffer start', offer)
  if (!pc.value) {
    createPeerConnection()
  }
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

  // @ts-ignore
  const currentPipElement = document.pictureInPictureElement

  // Свернули вкладку / ушли на другую
  if (document.visibilityState === 'hidden') {
    // Уже в PiP или браузер не умеет — ничего не делаем
    // @ts-ignore
    if (currentPipElement || !document.pictureInPictureEnabled) return

    try {
      // @ts-ignore
      await video.requestPictureInPicture()
    } catch (e) {
      console.error('[VIEWER] request PiP error', e)
    }
    return
  }

  // Вернулись на вкладку
  if (document.visibilityState === 'visible') {
    // @ts-ignore
    if (currentPipElement === video) {
      try {
        // @ts-ignore
        await document.exitPictureInPicture()
      } catch (e) {
        console.error('[VIEWER] exit PiP error', e)
      }
    }
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
