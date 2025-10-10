<script setup lang="ts">
import AppFooterSocial from '@/components/Footer/AppFooterSocial.vue'
import img from '@/assets/img/home-artist.webp'
</script>

<template>
  <div class="confirm">
    <div class="container">
      <div class="confirm-wrapper">
        <div class="confirm-image-wrapper">
          <img :src="img" alt="artist" fetchpriority="high" />
        </div>
        <h1>
          Thank you for confirming! <span><img src="/icons/letter.png" alt="letter" /></span>
        </h1>
        <div class="confirm-text">
          <div>You’re helping me keep this tiny magic alive.</div>
          <div>
            If you ever want to take a break — just don’t confirm next time,<br />and&nbsp;I’ll&nbsp;pause
            your mailings with love and no pressure.
          </div>
        </div>
        <div class="confirm-social">
          <h2>Real mail meets digital space</h2>
          <div class="confirm-social__text">
            The postcards I mail don’t just disappear — I post them here too. Follow along and let’s
            keep in touch.
          </div>
          <AppFooterSocial />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.confirm {
  display: flex;
  justify-content: center;
  flex-direction: column;
  align-items: center;
  flex: 1 1 0;
  padding: 20px 0 40px;

  &-wrapper {
    margin: 0 auto;
    max-width: 360px;
  }

  .container {
    max-width: 400px;
  }

  h1 {
    margin-top: 40px;

    span {
      position: relative;
      display: inline-block;
      width: 40px;

      img {
        position: absolute;
        transform: translate(0%, -80%);
      }
    }
  }

  &-text {
    margin-top: 16px;
    display: grid;
    gap: 16px;

    br {
      display: none;
    }
  }

  &-image-wrapper {
    width: 100%;
    aspect-ratio: 336 / 298;
    overflow: hidden;
    position: relative;
    border-radius: 8px;
    box-shadow: var(--box-shadow);

    & img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: 50% 12%;
      display: block;
      z-index: -1;
    }
  }

  &-social {
    text-align: start;
    margin-top: 40px;
    padding: 28px;
    background-color: var(--color-background);
    border-radius: 8px;
    box-shadow: 0 12px 42px -4px #18274b1f;

    &__text {
      margin: 16px 0 32px;
    }
  }

  @media (min-width: $xs) {
    text-align: center;

    &-wrapper {
      margin: 0;
      max-width: 750px;
    }
    &-image-wrapper {
      max-width: 360px;
      max-height: 340px;
      margin: 0 auto;
      aspect-ratio: 360/340;
    }
  }

  @media (min-width: $lg) {
    padding: 20px 0 60px;
    .container {
      max-width: 760px;
    }

    &-text {
      br {
        display: block;
      }
    }

    &-social {
      margin-top: 60px;
      padding: 40px;

      &__text {
        margin: 20px 0 32px;
      }
    }
  }
}
</style>
