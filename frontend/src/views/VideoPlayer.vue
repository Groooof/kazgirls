<script lang="ts" setup>
import Plyr from 'plyr'
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'

export type AppVideoPlayerAspectRatio = '16:9' | '4:3'

export interface AppVideoPlayerProps {
  url?: string
  poster?: string
  aspectRatio?: AppVideoPlayerAspectRatio
  srcObject?: MediaStream | null
  muted?: boolean
}

export interface AppVideoPlayerEmit {
  (e: 'get-pip-mode', value: boolean): void
}

const props = withDefaults(defineProps<AppVideoPlayerProps>(), {
  poster: '',
  aspectRatio: '16:9',
  srcObject: null,
  muted: false,
})

const emit = defineEmits<AppVideoPlayerEmit>()

const videoPlayerRef = ref<HTMLVideoElement | null>(null)
const videoPlayerInstance = ref<Plyr | null>(null)

// если srcObject (WebRTC) — это стрим
const isStream = computed(() => !!props.srcObject)

const videoPlayerOptions: Plyr.Options = {
  ratio: props.aspectRatio,
  // ВАЖНО: добавляем pip в контролы, чтобы Plyr не отключал свой функционал
  controls: ['play', 'volume', 'pip', 'fullscreen'],
  pip: true,
}

const initPlayer = () => {
  if (!videoPlayerRef.value) return

  // Инициализируем Plyr ВСЕГДА (и для url, и для stream),
  // но srcObject будем навешивать сами.
  const instance = new Plyr(videoPlayerRef.value, videoPlayerOptions)
  videoPlayerInstance.value = instance

  // события PiP от Plyr (они просто прокидывают нативные)
  instance.on('enterpictureinpicture', () => {
    emit('get-pip-mode', true)
  })

  instance.on('leavepictureinpicture', () => {
    emit('get-pip-mode', false)
  })
}

// навешиваем srcObject (это НЕ ломает Plyr — он использует тот же <video>)
watch(
  () => props.srcObject,
  (newStream) => {
    const el = videoPlayerRef.value
    if (!el) return

    if (!newStream) {
      ;(el as any).srcObject = null
      return
    }

    ;(el as any).srcObject = newStream
    el.muted = props.muted

    el
      .play()
      .then(() => console.log('[VideoPlayer] play ok'))
      .catch((err) => console.error('[VideoPlayer] play error', err))
  },
  { immediate: true },
)

onMounted(() => {
  initPlayer()
})

onBeforeUnmount(() => {
  if (videoPlayerInstance.value) {
    videoPlayerInstance.value.destroy()
    videoPlayerInstance.value = null
  }
})

// 👉 Экспортируем и video, и plyr-инстанс наружу
const enterPip = async () => {
  const inst: any = videoPlayerInstance.value
  const video = videoPlayerRef.value as any

  // сначала пробуем через Plyr (togglePictureInPicture)
  if (inst && typeof inst.togglePictureInPicture === 'function') {
    try {
      await inst.togglePictureInPicture()
    } catch (e) {
      console.error('[VideoPlayer] plyr togglePictureInPicture error', e)
    }
    return
  }

  // fallback — напрямую через video
  if (video && typeof video.requestPictureInPicture === 'function') {
    try {
      await video.requestPictureInPicture()
    } catch (e) {
      console.error('[VideoPlayer] native requestPiP error', e)
    }
  }
}

const exitPip = async () => {
  const video = videoPlayerRef.value as any
  const docAny = document as any

  if (docAny.pictureInPictureElement === video) {
    try {
      await docAny.exitPictureInPicture()
    } catch (e) {
      console.error('[VideoPlayer] exit PiP error', e)
    }
  }
}

defineExpose({
  getVideoElement: () => videoPlayerRef.value,
  getPlyrInstance: () => videoPlayerInstance.value,
  enterPip,
  exitPip,
})
</script>

<template>
  <div>
    <video
      ref="videoPlayerRef"
      :src="!srcObject ? url : undefined"
      :data-poster="poster"
      playsinline
      controls
      autoplay
      :muted="muted"
    ></video>
  </div>
</template>
