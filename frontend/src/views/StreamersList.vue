<script setup lang="ts">
import axios from 'axios'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { config } from '@/config'

interface ModelItem {
  id: number
  name: string
  avatar_url: string
}

const router = useRouter()

// Моки — потом заменишь на данные с бэка
const models = ref<ModelItem[]>([])

const search = ref('')

const openModel = (model: ModelItem) => {
  // { path: '/streamers/:id/view', name: 'Viewer', component: Viewer }
  router.push({
    name: 'Viewer',
    params: { id: model.id },
  })
}

const getStarArray = (rating: number) => {
  const full = Math.floor(rating)
  const half = rating - full >= 0.25 && rating - full < 0.75
  const stars = []
  for (let i = 0; i < 5; i++) {
    if (i < full) stars.push('full')
    else if (i === full && half) stars.push('half')
    else stars.push('empty')
  }
  return stars
}

const getStreamers = async() => {
    const { data } = await axios.get(`${config.url}${config.apiUrl}/streamers`, {
        withCredentials: true,
    })

    models.value = data
}

onMounted(() => {
    getStreamers()
})

setInterval(() => {
    getStreamers()
}, 5000);
</script>

<template>
  <div class="models-page">
    <div class="models-card">
      <header class="models-header">
        <div>
          <h1 class="models-title">Модели онлайн</h1>
          <p class="models-subtitle">
            Выберите модель, чтобы открыть стрим
          </p>
        </div>
      </header>

      <main class="models-body">
        <div v-if="!models.length" class="empty-state">
          <p class="empty-title">Никого не найдено</p>
        </div>

        <div v-else class="models-grid">
          <article
            v-for="model in models"
            :key="model.id"
            class="model-card"
            @click="openModel(model)"
          >
            <div class="model-thumb-wrapper">
              <img
                :src="model.avatar_url"
                :alt="model.name"
                class="model-thumb"
              >

              <div class="online-badge">
                <span class="online-dot"></span>
                <span>Online</span>
              </div>
            </div>

            <div class="model-info">
              <div class="model-main-row">
                <h2 class="model-name">
                  {{ model.name }}
                </h2>
              </div>

              <!-- <div class="rating-row">
                <div class="stars">
                  <span
                    v-for="(star, idx) in getStarArray(model.rating)"
                    :key="idx"
                    class="star"
                    :class="{
                      'star--full': star === 'full',
                      'star--half': star === 'half',
                      'star--empty': star === 'empty',
                    }"
                  >
                    ★
                  </span>
                </div>
                <span class="rating-text">
                  {{ model.rating.toFixed(1) }}
                </span>
              </div> -->

              <button class="enter-btn">
                Смотерть стрим →
              </button>
            </div>
          </article>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.models-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: #020617;
  padding: 24px 16px;
  box-sizing: border-box;
}

.models-card {
  width: 100%;
  max-width: 1100px;
  background: #020617;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  padding: 16px 20px 20px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.9);
  box-sizing: border-box;
}

.models-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.models-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #e5e7eb;
}

.models-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #9ca3af;
}

.search-wrapper {
  width: 100%;
  max-width: 260px;
}

.search-input {
  width: 100%;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.7);
  background: rgba(15, 23, 42, 0.9);
  color: #e5e7eb;
  padding: 7px 12px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.12s ease, box-shadow 0.12s ease, background 0.12s ease;
}

.search-input::placeholder {
  color: rgba(148, 163, 184, 0.8);
}

.search-input:focus {
  border-color: #38bdf8;
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.6);
  background: #020617;
}

.models-body {
  margin-top: 8px;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 14px;
}

.model-card {
  cursor: pointer;
  background: radial-gradient(circle at top, #020617, #020617);
  border-radius: 14px;
  border: 1px solid rgba(30, 64, 175, 0.7);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition:
    transform 0.12s ease,
    box-shadow 0.12s ease,
    border-color 0.12s ease,
    background 0.12s ease;
}

.model-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.9);
  border-color: rgba(56, 189, 248, 0.9);
  background: radial-gradient(circle at top, #020617, #020617);
}

.model-thumb-wrapper {
  position: relative;
  aspect-ratio: 4 / 5;
  overflow: hidden;
}

.model-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: saturate(1.05);
  transform: scale(1.02);
}

.online-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(22, 163, 74, 0.82);
  color: #ecfdf5;
}

.online-badge--off {
  background: rgba(148, 163, 184, 0.85);
  color: #e5e7eb;
}

.online-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #22c55e;
}

.online-dot--off {
  background: #9ca3af;
}

.tags {
  position: absolute;
  bottom: 8px;
  left: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: rgba(15, 23, 42, 0.8);
  color: #e5e7eb;
}

.model-info {
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-main-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.model-name {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #f9fafb;
}

.viewers-pill {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: #e5e7eb;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.7);
}

.rating-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.stars {
  display: inline-flex;
  gap: 1px;
}

.star {
  font-size: 13px;
  color: #1f2933;
}

.star--full {
  color: #facc15;
  text-shadow: 0 0 6px rgba(250, 204, 21, 0.5);
}

.star--half {
  color: #facc15;
  opacity: 0.7;
}

.star--empty {
  color: #4b5563;
}

.rating-text {
  font-size: 12px;
  color: #e5e7eb;
}

.enter-btn {
  margin-top: 4px;
  width: 100%;
  padding: 6px 10px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #22c55e, #0ea5e9);
  color: #f9fafb;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  box-shadow: 0 10px 26px rgba(34, 197, 94, 0.38);
  transition:
    transform 0.12s ease,
    box-shadow 0.12s ease,
    opacity 0.1s ease;
}

.enter-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 36px rgba(34, 197, 94, 0.55);
}

.model-card:active .enter-btn {
  transform: translateY(0);
  box-shadow: 0 8px 20px rgba(34, 197, 94, 0.4);
}

.empty-state {
  padding: 40px 12px;
  text-align: center;
}

.empty-title {
  margin: 0 0 4px;
  font-size: 16px;
  color: #e5e7eb;
}

.empty-subtitle {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
}
</style>    