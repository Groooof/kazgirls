<script setup lang="ts">
import PaymentChoice from '@/components/Home/Payment/PaymentChoice.vue'
import { ConfirmPayType } from '@/types/types.ts'
import img from '@/assets/img/payment.webp'
</script>

<template>
  <div class="payment-failed">
    <div class="container">
      <div class="payment-failed-wrapper">
        <img class="payment-failed__img" :src="img" alt="payment" fetchpriority="high" />
        <h1>
          Your payment failed <img src="/icons/sad.png" alt="sad" />, but the order was successfully
          confirmed
        </h1>
        <div>
          Please try again if you want to leave a tip. It's definitely going to work this time.
        </div>
      </div>
    </div>
  </div>
  <div class="payment-failed-choice">
    <div class="container">
      <div class="payment-failed-choice-wrapper">
        <h2>Please confirm you're still happy to receive more</h2>
        <PaymentChoice :type="ConfirmPayType.Custom" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.payment-failed {
  .container {
    max-width: 1000px;
  }

  &-wrapper {
    margin-bottom: 20px;
  }

  h1 {
    margin-bottom: 8px;

    img {
      width: 30px;
      transform: translateY(2px);
      display: inline-block;
    }
  }

  &__img {
    width: 100%;
    max-width: 360px;
    margin: 0 auto 24px;
    box-shadow: 0 12px 42px -4px #18274b1f;
    min-height: 200px;
  }

  &-choice {
    padding: 20px 0;
    margin-bottom: 20px;
    background-color: var(--color-background);

    .container {
      max-width: 1000px;
    }

    h2 {
      font-size: 16px;
      font-weight: 400;
      line-height: 1.5;
      margin-bottom: 20px;
      color: var(--color-text);
    }
  }

  @media (min-width: $xs) {
    text-align: center;

    &-wrapper {
      margin-bottom: 40px;
    }

    &__img {
      margin: 0 auto 40px;
    }

    &-choice {
      padding: 60px 15px 40px;
      margin-bottom: 60px;

      h2 {
        font-size: 22px;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 40px;
        color: var(--color-text-header);
      }
    }
  }

  @media (min-width: $lg) {
    h1 {
      margin-bottom: 20px;

      img {
        width: auto;
      }
    }

    &-wrapper {
      margin-bottom: 48px;
    }

    &-choice {
      border-radius: 8px;

      h2 {
        font-size: 32px;
      }
    }
  }

  @media (min-width: $md) {
    h1 {
      margin-bottom: 20px;
    }

    &-choice {
      padding: 0;
      background-color: transparent;

      &-wrapper {
        padding: 60px;
        background-color: var(--color-background);
        border-radius: 8px;
      }
    }
  }
}
</style>
