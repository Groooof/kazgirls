<script setup lang="ts">
import { handleGlobalError } from '@/utils/errorHandler.ts'
import { computed, onMounted, reactive, ref } from 'vue'
import { indexApi } from '@/fastApi/apiClient/index.ts'
import type { SubscriptionResponse } from '@/fastApi'
import HomeArtist from '@/components/Home/Artist/HomeArtist.vue'
import HomeSwiper from '@/components/Home/Swiper/HomeSwiper.vue'
import AppPageLoaderOverlay from '@/components/UI/AppPageLoaderOverlay/AppPageLoaderOverlay.vue'
import { isAxiosError } from 'axios'
import router from '@/router'
import { useRoute } from 'vue-router'

const route = useRoute()
const isLoading = ref<boolean>(false)
const errorMessage = ref('')
const userInfo = reactive<Partial<SubscriptionResponse>>({})

const token = computed(() => route.params.token as string)

const fetchProjects = async () => {
  try {
    errorMessage.value = ''
    isLoading.value = true
    const data = await indexApi.getSubscription(token.value)
    if (!data.is_active) {
      await router.push({ name: 'Confirm' })
      return
    }
    Object.assign(userInfo, data)
  } catch (error: unknown) {
    handleGlobalError(error)

    if (isAxiosError(error)) {
      console.error(error)
      errorMessage.value = error.message
    } else {
      console.error('Unexpected error', error)
      errorMessage.value = 'Unexpected error'
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchProjects()
})
</script>

<template>
  <div class="home">
    <AppPageLoaderOverlay v-if="isLoading" />
    <div v-else-if="errorMessage" class="container">
      <span class="error">{{ errorMessage }}</span>
    </div>
    <div v-else>
      <div class="home-greetings">
        <div class="container">
          <h1 v-if="userInfo.full_name">
            Hey {{ userInfo.full_name }},
            <span class="home-greetings__img">
              <img width="40" height="40" src="/icons/letter.png" alt="letter" />
            </span>
            <br class="home-greetings-separator" />
            Your&nbsp;postcard has arrived!
          </h1>

          <div>
            This tiny piece of art traveled a long way — with love, care, and a sprinkle of magic
          </div>
        </div>
      </div>
      <HomeSwiper />
      <HomeArtist />
    </div>
  </div>
</template>

<style scoped lang="scss">
.home {
  padding: 0 0 20px;

  &-greetings {
    padding-bottom: 20px;

    h1 {
      margin-bottom: 8px;
    }

    &__img {
      position: relative;
      display: inline-block;
      width: 40px;

      img {
        position: absolute;
        transform: translate(0%, -80%);
      }
    }
  }

  @media (min-width: $md) {
    padding: 22px 0 80px;

    &-greetings {
      padding-bottom: 48px;

      h1 {
        margin-bottom: 20px;
      }

      &-separator {
        display: none;
      }
    }
  }
}
</style>
