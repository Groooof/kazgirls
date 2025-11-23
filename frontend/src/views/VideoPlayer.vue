<script lang="ts" setup>
import Plyr from 'plyr'
import { onMounted, ref, useTemplateRef, watch, nextTick } from 'vue'

export type TimeCodeData = Plyr.MarkersPoints

export type AppVideoPlayerAspectRatio = '16:9' | '4:3'

export interface AppVideoPlayerProps {
  url?: string
  poster?: string
  aspectRatio?: AppVideoPlayerAspectRatio
  srcObject?: MediaStream | null
  muted?: boolean
  play?: boolean
}

export interface AppVideoPlayerEmit {
  (e: 'get-pip-mode', value: boolean): void
}

const props = withDefaults(defineProps<AppVideoPlayerProps>(), {
  poster: '',
  markerPoints: () => [],
  aspectRatio: '16:9',
  srcObject: null,
  muted: false,
  play: false,
})

const emit = defineEmits<AppVideoPlayerEmit>()

const videoPlayerRef = useTemplateRef<HTMLVideoElement>('videoPlayerRef')
const videoPlayerInstance = ref()

const getVideoPlayerControls = () => {
  const controls: string[] = []

  if (props.play) {
    controls.push('play')
  }

  controls.push('volume')
  controls.push('fullscreen')
  controls.push('pip')

  return controls
}
  

const videoPlayerOptions: Plyr.Options = {
  ratio: props.aspectRatio,
  controls: getVideoPlayerControls(),
}

const initPlayer = (): void => {
  if (!videoPlayerRef.value) return

  const instance = new Plyr(videoPlayerRef.value, videoPlayerOptions)

  videoPlayerInstance.value = instance

  instance.on('enterpictureinpicture', () => {
    emit('get-pip-mode', true)
  })

  instance.on('leavepictureinpicture', () => {
    emit('get-pip-mode', false)
  })
}

watch(() => [props.srcObject, videoPlayerRef.value], () => {
  if (videoPlayerRef.value && props.srcObject) {
    videoPlayerRef.value.srcObject = props.srcObject
    videoPlayerRef.value.muted = props.muted
    // Автоплей после установки потока
    videoPlayerRef.value.play().catch(console.error)
  }
}, { immediate: true })

onMounted(() => {
  initPlayer()
})

defineExpose({
  getVideoElement: () => videoPlayerRef.value
})
</script>

<template>
  <div>
    <video
      ref="videoPlayerRef"
      :src="url"
      :data-poster="poster"
      playsinline
      controls
      autoplay
      :muted="muted"
    ></video>
  </div>
</template>
