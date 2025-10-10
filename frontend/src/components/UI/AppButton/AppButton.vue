<script setup lang="ts">
defineProps<{
  loading?: boolean
  error?: string
}>()
</script>

<template>
  <div class="app-button-wrapper">
    <button class="app-button" :disabled="loading">
      <span class="app-button__content">
        <template v-if="loading">
          <span class="loader" aria-hidden="true"></span>
        </template>
        <template v-else>
          <slot></slot>
        </template>
      </span>
    </button>
    <p v-if="error" class="app-button__error">{{ error }}</p>
  </div>
</template>

<style lang="scss">
.app-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-white);
  font-weight: 500;
  line-height: 1.5;
  width: 100%;
  border-radius: 40px;
  padding: 14px;
  background: var(--linear-gradient); // базовый градиент
  transition: color 0.3s ease;
  position: relative;
  overflow: hidden;

  @media (min-width: $md) {
    font-size: 18px;
  }

  &-wrapper {
    width: 100%;
  }

  &__content {
    position: relative;
    z-index: 1;
  }

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, #ffb338 0%, #ffab24 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, #ff3636 0%, #e1911d 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }

  &:hover:not(:disabled)::before,
  &:active::after {
    opacity: 1;
  }

  &:disabled::before,
  &:disabled::after {
    opacity: 0 !important;
  }

  // Контент поверх ::before
  > * {
    position: relative;
    z-index: 1;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &__error {
    margin-top: 8px;
    color: red;
    font-size: 14px;
    text-align: center;
  }
}

.loader {
  display: block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
