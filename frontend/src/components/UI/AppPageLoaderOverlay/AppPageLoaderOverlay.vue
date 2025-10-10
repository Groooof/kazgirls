<template>
  <div class="app-page-loader-overlay">
    <div class="app-page-loader-overlay__spinner" aria-label="Загрузка..."></div>
  </div>
</template>

<style lang="scss">
.app-page-loader-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  background-color: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: all;
}

.app-page-loader-overlay__spinner {
  width: 48px;
  height: 48px;
  border: 5px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
