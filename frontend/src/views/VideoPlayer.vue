<script lang="ts" setup>
import Plyr from 'plyr'
import { onMounted, ref, useTemplateRef, watch, nextTick } from 'vue'

export type TimeCodeData = Plyr.MarkersPoints

export type AppVideoPlayerAspectRatio = '16:9' | '4:3'

export interface AppVideoPlayerProps {
  url: string
  poster?: string
  aspectRatio?: AppVideoPlayerAspectRatio
  srcObject?: MediaStream | null
}

export interface AppVideoPlayerEmit {
  (e: 'get-pip-mode', value: boolean): void
}

const props = withDefaults(defineProps<AppVideoPlayerProps>(), {
  poster: '',
  markerPoints: () => [],
  aspectRatio: '16:9',
  srcObject: null,
})

const emit = defineEmits<AppVideoPlayerEmit>()

const videoPlayerRef = useTemplateRef<HTMLElement>('videoPlayerRef')
const videoPlayerInstance = ref()

const videoPlayerOptions: Plyr.Options = {
  ratio: props.aspectRatio,
  controls: [
    'play',
    'volume',
    'fullscreen',
  ]
}

const initPlayer = (): void => {
  if (!videoPlayerRef.value) return

  videoPlayerInstance.value = new Plyr(videoPlayerRef.value, videoPlayerOptions)

  videoPlayerInstance.value.on('enterpictureinpicture', () => {
    emit('get-pip-mode', true)
  })

  videoPlayerInstance.value.on('leavepictureinpicture', () => {
    emit('get-pip-mode', false)
  })
}

watch(() => props.srcObject, (newStream) => {
  if (videoPlayerRef.value && newStream) {
    videoPlayerRef.value.srcObject = newStream
    // Автоплей после установки потока
    videoPlayerRef.value.play().catch(console.error)
  }
}, { immediate: true })

onMounted(() => {
  initPlayer()

  console.log(props.url)
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
      muted
    ></video>
  </div>
</template>
