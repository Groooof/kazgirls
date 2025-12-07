<template>
  <div class="page">
    <h1>Streamer</h1>

    <video
      ref="localVideo"
      autoplay
      playsinline
      muted
      style="width: 400px; background: #111"
    ></video>

    <div style="margin-top: 16px;">
      <button @click="startStreaming" :disabled="isStreaming">Start streaming</button>
      <button @click="stopStreaming" :disabled="!isStreaming">Stop</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { io, Socket } from 'socket.io-client'
import { config } from '@/config'

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
}

const localVideo = ref<HTMLVideoElement | null>(null)
const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)
const localStream = ref<MediaStream | null>(null)
const isStreaming = ref(false)
const pendingIceCandidates: RTCIceCandidateInit[] = []

function initPeerConnection() {
  if (pc.value) {
    console.log('pc already exists')
    return
  }

  console.log('creating RTCPeerConnection with config', rtcConfig)
  pc.value = new RTCPeerConnection(rtcConfig)

  pc.value.onicecandidate = (data) => {
    console.log('[webrtc] onicecandidate', data)
    if (data.candidate) {
      socket.value?.emit('webrtc:ice', data.candidate)
    }
  }

  pc.value.onicegatheringstatechange = () => {
    console.log('[webrtc] onicegatheringstatechange', pc.value?.iceGatheringState)
  }

  pc.value.onconnectionstatechange = () => {
    console.log('[webrtc] onconnectionstatechange', pc.value?.connectionState)
  }

  pc.value.oniceconnectionstatechange = () => {
    console.log('[webrtc] oniceconnectionstatechange', pc.value?.iceConnectionState)
  }

  pc.value.onsignalingstatechange = () => {
    console.log('[webrtc] onsignalingstatechange', pc.value?.signalingState)
  }

  pc.value.onnegotiationneeded = async () => {
    console.log('[webrtc] onnegotiationneeded')
    initPeerConnection()
    const offer = await pc.value!.createOffer()
    await pc.value!.setLocalDescription(offer)
    socket.value?.emit('webrtc:offer', offer)
  }
}

function initSocket() {
  if (socket.value) return

  console.log('init socket')

  socket.value = io(`${config.url}/streamers`, {
    autoConnect: true,
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 500,
    reconnectionDelayMax: 5000,
  })

  socket.value.on('connect', () => {
    console.log('[socket] connected', socket.value?.id)
  })

  socket.value.on('disconnect', (reason) => {
    console.log('[socket] disconnected', reason)
  })

  socket.value.on('connect_error', (data) => {
    console.log('[socket] connect_error', data)
  })

  socket.value.on('streamers:disconnected', (data) => {
    console.log('[socket] streamers:disconnected', data)
  })

  socket.value.on('viewers:disconnected', (data) => {
    console.log('[socket] viewers:disconnected', data)

    if (pc.value) {
      pc.value.close()
      pc.value = null
    }
  })

  socket.value.on('viewers:connected', async (data) => {
    console.log('[socket] viewers:connected', data)

    initPeerConnection()
    const stream = localStream.value
    if (stream) {
      stream.getTracks().forEach((track) => {
        pc.value?.addTrack(track, stream)
      })
    }

    const offer = await pc.value!.createOffer()
    await pc.value!.setLocalDescription(offer)
    socket.value?.emit('webrtc:offer', offer)
  })

  socket.value.on('webrtc:offer', async (data) => {
    console.log('[socket] webrtc:offer', data)

    initPeerConnection()
    if (!pc.value) {
      console.warn('no pc when answer arrived')
      return
    }

    try {
      await pc.value.setRemoteDescription(new RTCSessionDescription(data))
      console.log('setRemoteDescription(offer) OK')

      console.log('creating answer')
      const answer = await pc.value.createAnswer()
      console.log('created answer', answer)

      await pc.value.setLocalDescription(answer)
      console.log('setLocalDescription(answer) OK')

      console.log('sending answer via socket')
      socket.value?.emit('webrtc:answer', answer)
    } catch (e) {
      console.error(' error handling offer', e)
    }
  })

  socket.value.on('webrtc:answer', async (data) => {
    console.log('[socket] webrtc:answer', data)

    if (!pc.value) {
      console.warn('no pc when answer arrived')
      return
    }

    try {
      await pc.value.setRemoteDescription(new RTCSessionDescription(data))
      console.log('setRemoteDescription(answer) OK')
    } catch (e) {
      console.error('setRemoteDescription(answer) error', e)
    }

    for (const c of pendingIceCandidates) {
      try {
        await pc.value.addIceCandidate(new RTCIceCandidate(c))
        console.log('addIceCandidate(from queue) OK', c)
      } catch (e) {
        console.warn('addIceCandidate(from queue) error, ignore', e, c)
      }
    }
    pendingIceCandidates.length = 0
  })

  socket.value.on('webrtc:ice', async (data) => {
    console.log('[socket] webrtc:ice', data)

    if (!pc.value) {
      console.warn('no pc when remote ICE arrived')
      return
    }

    if (!pc.value.remoteDescription) {
      console.log('[webrtc] no remoteDescription yet, queue candidate')
      pendingIceCandidates.push(data)
      return
    }

    const ice = new RTCIceCandidate(data)
    await pc.value.addIceCandidate(ice)
  })
}

async function startStreaming() {
  if (isStreaming.value) return

  try {
    console.log('getUserMedia start')
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    })
    console.log('got local stream', stream)

    localStream.value = stream
    if (localVideo.value) {
      localVideo.value.srcObject = stream
    }

    initPeerConnection()
    const offer = await pc.value!.createOffer()
    await pc.value!.setLocalDescription(offer)
    socket.value?.emit('webrtc:offer', offer)

    stream.getTracks().forEach((track) => {
      pc.value?.addTrack(track, stream)
    })

    isStreaming.value = true
  } catch (e) {
    console.error('startStreaming error', e)
    stopStreaming()
  }
}

function stopStreaming() {
  console.log('stopStreaming')

  isStreaming.value = false

  if (localStream.value) {
    localStream.value.getTracks().forEach((t) => {
      t.stop()
    })
    localStream.value = null
  }
}

onMounted(() => {
  initSocket()
})

onBeforeUnmount(() => {
  console.log('beforeUnmount cleanup')
  stopStreaming()
  if (socket.value) {
    socket.value.disconnect()
    socket.value = null
  }
  if (pc.value) {
    pc.value.close()
    pc.value = null
  }
})
</script>

<style scoped>
.page {
  padding: 16px;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
button {
  margin-right: 8px;
}
</style>
