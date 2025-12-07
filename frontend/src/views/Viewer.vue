<template>
  <div class="page">
    <h1>Viewer</h1>
    <video
      ref="remoteVideo"
      autoplay
      playsinline
      muted
      style="width: 400px; background: #111"
    ></video>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { io, Socket } from 'socket.io-client'
import { useRoute } from 'vue-router'
import { config } from '@/config'

const route = useRoute()

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

const remoteVideo = ref<HTMLVideoElement | null>(null)
const socket = ref<Socket | null>(null)
const pc = ref<RTCPeerConnection | null>(null)
const remoteStream = ref<MediaStream | null>(null)

const streamerId = Number(route.params.id)


function initPeerConnection() {
  if (pc.value) {
    console.log('pc already exists')
    return
  }

  console.log('creating RTCPeerConnection with config', rtcConfig)
  pc.value = new RTCPeerConnection(rtcConfig)

  pc.value.ontrack = (event) => {
    console.log('[webrtc] ontrack', event.streams, event.track)

    const [stream] = event.streams
    if (!stream) {
      console.log('[webrtc] ontrack: no streams in event')
      return
    }

    if (!remoteVideo.value) {
      console.log('[webrtc] ontrack: no remoteVideo ref')
      return
    }

    remoteVideo.value.srcObject = stream
    console.log('[webrtc] srcObject set')
  }

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
  }
}

function initSocket() {
  if (socket.value) return

  console.log('init socket')

  socket.value = io(`${config.url}/streamers`, {
    autoConnect: true,
    query: { streamer_id: String(streamerId) },
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

    if (pc.value) {
      pc.value.close()
      pc.value = null
    }
  })

  socket.value.on('viewers:disconnected', (data) => {
    console.log('[socket] viewers:disconnected', data)
  })

  socket.value.on('streamers:connected', async (data) => {
    console.log('[socket] streamers:connected', data)

    // initPeerConnection()
    // const offer = await pc.value!.createOffer()
    // await pc.value!.setLocalDescription(offer)
    // socket.value?.emit('webrtc:offer', offer)
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
  })

  socket.value.on('webrtc:ice', async (data) => {
    console.log('[socket] webrtc:ice', data)

    if (!pc.value) {
      console.warn('no pc when remote ICE arrived')
      return
    }

    try {
      await pc.value.addIceCandidate(new RTCIceCandidate(data))
      console.log('addIceCandidate(remote) OK')
    } catch (e) {
      console.error('addIceCandidate(remote) error', e)
    }
  })
}

function cleanup() {
  console.log('[VIEWER] cleanup')

  if (pc.value) {
    console.log('[VIEWER] closing peer connection')
    pc.value.close()
    pc.value = null
  }

  if (socket.value) {
    console.log('[VIEWER] disconnecting socket')
    socket.value.disconnect()
    socket.value = null
  }

  if (remoteVideo.value) {
    remoteVideo.value.srcObject = null
  }
}

onBeforeUnmount(() => {
  console.log('[VIEWER] beforeUnmount cleanup')
  cleanup()
})

onMounted(() => {
  initSocket()
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
