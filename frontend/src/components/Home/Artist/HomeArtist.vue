<script setup lang="ts">
import img from '@/assets/img/home-artist.webp'
</script>

<template>
  <div class="home-artist">
    <div class="container">
      <div class="home-artist-wrapper">
        <div class="home-artist-image-wrapper">
          <img :src="img" alt="artist" fetchpriority="high" />
        </div>
        <div class="home-artist-content">
          <h2>
            I draw each postcard and cover all printing and&nbsp;shipping costs
            <span>by&nbsp;myself</span>
          </h2>
          <div class="home-artist-content__text">
            <div>
              When you confirm, I know someone’s still waiting on the other side — and that I can
              keep sending to you.
            </div>
            <div>
              It’s also your way of saying thank you — and it&nbsp;means the world to&nbsp;me!
            </div>
          </div>
          <div class="home-artist-content__bottom">
            <img src="/icons/heart-red.png" alt="heart" />
            Svinka
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.home-artist {
  max-width: 430px;
  margin: 0 auto;

  &-wrapper {
    display: grid;
    gap: 12px;
    padding-top: 20px;
  }

  h2 {
    span {
      background: var(--linear-gradient);
      -webkit-text-fill-color: transparent;
      -webkit-background-clip: text;
    }
  }

  &-image-wrapper {
    width: 100%;
    aspect-ratio: 1 / 1;
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

  &-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 28px;
    background-color: var(--color-white);
    border-radius: 8px;
    box-shadow: var(--box-shadow);

    &__text {
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1 1 0;
    }

    &__bottom {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 14px;
    }
  }

  @media (min-width: $md) {
    max-width: none;

    &-wrapper {
      grid-template-columns: 360px auto;
      padding-top: 80px;
    }
    &-content {
      padding: 40px;
      &__bottom {
        font-size: 16px;
      }
    }
    &-image-wrapper {
      max-height: 400px;
      aspect-ratio: auto;
    }
  }
}
</style>
