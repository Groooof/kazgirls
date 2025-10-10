<script setup lang="ts">
import AppButton from '@/components/UI/AppButton/AppButton.vue'
import AppInput from '@/components/UI/AppInput/AppInput.vue'
import AppIcon from '@/components/UI/AppIcon/AppIcon.vue'
import { computed, ref, watch } from 'vue'
import { indexApi } from '@/fastApi/apiClient'
import router from '@/router'
import { useRoute } from 'vue-router'
import { ConfirmPayType } from '@/types/types.ts'

interface Props {
  type: ConfirmPayType
  price?: number
}

const props = withDefaults(defineProps<Props>(), {
  type: ConfirmPayType.NoMoney,
  price: 0,
})

const route = useRoute()
const tip = ref(props.price)
const isLoading = ref(false)
const token = computed(() => route.params.token as string)

const onConfirm = async (): Promise<void> => {
  try {
    isLoading.value = true
    await indexApi.confirmWithoutSupport(token.value)
    await router.push({ name: 'Confirm' })
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.price,
  (newPrice) => {
    tip.value = newPrice
  },
)
</script>

<template>
  <div class="payments-choice">
    <h2 v-if="props.type !== ConfirmPayType.NoMoney">
      Confirm and leave<br v-if="type === ConfirmPayType.Custom" />
      a $
      <AppInput
        v-if="type === ConfirmPayType.Custom"
        type="number"
        placeholder="100"
        v-model="tip"
      />
      <span v-else>{{ tip }}</span>
      tip
    </h2>
    <div v-if="type !== ConfirmPayType.NoMoney" class="payments-choice__btns">
      <AppButton @click="onConfirm">
        <AppIcon width="24" height="24" icon="apple" />
        <span>by Apple Pay</span>
      </AppButton>
      <AppButton @click="onConfirm">
        <AppIcon width="24" height="24" icon="paypal" />
        <span>by PayPal</span>
      </AppButton>
      <AppButton @click="onConfirm">
        <AppIcon width="24" height="24" icon="google" />
        <span>by Google Pay</span>
      </AppButton>
      <AppButton @click="onConfirm">
        <AppIcon width="24" height="24" icon="card" />
        <span>by Debit or Credit card</span>
      </AppButton>
    </div>
    <div v-else class="payments-choice__btns">
      <AppButton :loading="isLoading" @click="onConfirm"> Confirm and don't leave a tip </AppButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
.payments-choice {
  &__btns {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    margin: 16px 0 20px;
    max-width: 350px;
  }

  @media (min-width: $xs) {
    &__btns {
      grid-template-columns: 1fr 1fr;
      max-width: none;
      margin: 16px auto 20px;
    }
    h2 {
      br {
        display: none;
      }
    }
  }

  @media (min-width: $md) {
    &__btns {
      gap: 16px;
      margin: 24px auto 0;
    }
  }
}
</style>
