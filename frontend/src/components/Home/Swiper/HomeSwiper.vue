<script setup lang="ts">
import { Swiper, SwiperSlide } from 'swiper/vue'
import 'swiper/css'
import { reactive, ref } from 'vue'
import PaymentChoice from '@/components/Home/Payment/PaymentChoice.vue'
import { ConfirmPayType } from '@/types/types.ts'

interface ConfirmItem {
  text: string
  icon: string
  isActive: boolean
  price: number
  type: ConfirmPayType
}

const price = ref(0)
const type = ref<ConfirmPayType>(ConfirmPayType.NoMoney)
const initialSlide = ref(0)

const confirmType = reactive<ConfirmItem[]>([
  {
    text: 'Just&nbsp;confirm,<br/>no tip this<br/>time',
    icon: '/icons/check.png',
    price: 0,
    type: ConfirmPayType.NoMoney,
    isActive: true,
  },
  {
    text: 'Yes, I got it!<br/>And here’s<br/>$2',
    icon: '/icons/heart-star.png',
    price: 2,
    type: ConfirmPayType.Money,
    isActive: false,
  },
  {
    text: 'Yes!<br/>And $5<br/>to support you',
    icon: '/icons/star.png',
    price: 5,
    type: ConfirmPayType.Money,
    isActive: false,
  },
  {
    text: 'Yes!<br/>$10, love this<br/>project',
    icon: '/icons/rocket.png',
    price: 10,
    type: ConfirmPayType.Money,
    isActive: false,
  },
  {
    text: 'Yes!<br/>Leave custom<br/>tip',
    icon: '/icons/heart.png',
    price: 0,
    type: ConfirmPayType.Custom,
    isActive: false,
  },
])

const swiperOptions = {
  360: {
    slidesPerView: 2.05,
    spaceBetween: 12,
  },
  576: {
    slidesPerView: 3.1,
  },
  768: {
    slidesPerView: 3.7,
  },
  1024: {
    slidesPerView: 5,
  },
}

const onConfirmClick = (item: ConfirmItem): void => {
  confirmType.forEach((el) => {
    el.isActive = false
  })
  item.isActive = true
  type.value = item.type
  price.value = item.price
}
</script>

<template>
  <div class="home-confirm">
    <div class="container">
      <div class="home-confirm-wrapper">
        <div class="home-confirm-text">
          Please confirm you're still happy to&nbsp;receive more. Tap one of the buttons below
          to&nbsp;confirm<img src="/icons/index-finger.png" alt="index" />
        </div>
        <div class="home-confirm-text-twice">
          <h2>Please confirm you're still happy to receive more</h2>
          <div>
            If you don’t confirm twice in a row, I’ll gently stop sending to your address&nbsp;<img
              src="/icons/heart-broken.png"
              alt="heart-broken"
            />
          </div>
          <div>
            Tap one of the buttons below to confirm&nbsp;<img
              src="/icons/index-finger.png"
              alt="index"
            />
          </div>
        </div>
        <swiper
          class="home-confirm-swiper"
          :slides-per-view="1.6"
          :space-between="12"
          :initial-slide="initialSlide"
          :breakpoints="swiperOptions"
        >
          <swiper-slide @click="onConfirmClick(item)" v-for="item in confirmType" :key="item.icon">
            <button
              class="home-confirm-item"
              :class="{
                active: item.isActive,
                blur: item.isActive === false && type === ConfirmPayType.NoMoney,
              }"
              :disabled="item.isActive === false"
            >
              <img width="20" height="20" :src="item.icon" alt="item.icon" />
              <span v-html="item.text" class="home-confirm-item__text"></span>
            </button>
          </swiper-slide>
        </swiper>
        <PaymentChoice :type="type" :price="price" />
        <div class="home-confirm-description">
          If you don’t confirm twice in a row, I’ll gently stop sending to your address
          <img src="/icons/heart-broken.png" alt="heart-broken" />
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss">
.home-confirm {
  padding: 20px 0;
  background-color: var(--color-background);

  &-swiper {
    margin: 0 -12px;
    padding: 20px 15px;
  }

  &-item {
    width: 100%;
    padding: 6px;
    border-radius: 8px;
    background-color: var(--color-white);
    font-weight: 700;
    color: var(--color-blue);
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 12px 9px -4px #18274b1f;

    &.active {
      background-color: var(--color-blue);
      color: var(--color-white);

      &:hover:not(:disabled) {
        background-color: var(--color-blue);
        color: var(--color-white);
      }
    }

    &:hover:not(:disabled) {
      background-color: var(--color-background);
    }

    &:disabled {
      opacity: 0.5;
      cursor: grab;
    }

    img {
      display: inline;
      margin-right: 4px;
      transform: translateY(3px);
    }
  }

  &__btns {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    margin: 16px auto 20px;
    max-width: 350px;
  }

  &-text {
    img {
      display: inline;
      transform: translateY(4px);
    }
  }

  &-text-twice {
    display: none;

    h2 {
      padding-bottom: 8px;
    }

    img {
      display: inline;
      transform: translateY(4px);
    }
  }

  &-description {
    img {
      display: inline;
      transform: translateY(4px);
    }
  }

  h2 {
    line-height: 1.2;
  }

  @media (min-width: $xs) {
    &__btns {
      grid-template-columns: 1fr 1fr;
      max-width: none;
    }
    h2 {
      br {
        display: none;
      }
    }
    &-item {
      padding: 12px;
    }
  }

  @media (min-width: $md) {
    padding: 80px 0;

    &__btns {
      gap: 16px;
      margin: 24px auto 0;
    }

    &-description {
      display: none;
    }
    &-text {
      display: none;
    }
    &-text-twice {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
  }

  @media (min-width: $xl) {
    &-swiper {
      margin: 0 -40px;
      padding: 48px 40px 40px;
    }
    &-item {
      box-shadow: var(--box-shadow);
    }
  }
}
</style>
