<script lang="ts" setup>
import { computed } from 'vue'

interface Props {
  type?: string
  modelValue: string | number
  hasError?: boolean
  placeholder?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
}>()

const inputType = computed(() => props.type ?? 'text')

const displayValue = computed(() => {
  if (inputType.value === 'number') {
    if (props.modelValue === 0 || props.modelValue === '0') {
      return ''
    }
  }
  return props.modelValue
})

const onKeydown = (e: KeyboardEvent) => {
  if (inputType.value !== 'number') return

  const allowedKeys = [
    'Backspace',
    'Delete',
    'ArrowLeft',
    'ArrowRight',
    'Tab',
    'ArrowUp',
    'ArrowDown',
  ]

  const isNumberKey = /^[0-9]$/.test(e.key)

  if (!isNumberKey && !allowedKeys.includes(e.key)) {
    e.preventDefault()
    return
  }

  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault()

    const current = parseInt(props.modelValue.toString() || '0', 10)
    const step = e.key === 'ArrowUp' ? 1 : -1
    let next = current + step

    if (next < 0) next = 0
    if (next > 1000) next = 1000

    emit('update:modelValue', next.toString())
  }
}

const onPaste = (e: ClipboardEvent) => {
  if (inputType.value !== 'number') return

  const pasted = e.clipboardData?.getData('text') ?? ''
  if (!/^\d+$/.test(pasted)) {
    e.preventDefault()
  }
}

const onInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  let value = target.value

  if (inputType.value === 'number') {
    value = value.replace(/[^\d]/g, '')

    if (value === '') {
      emit('update:modelValue', '')
      return
    }

    let numericValue = parseInt(value, 10)

    if (numericValue > 1000) {
      numericValue = 1000
    }

    value = numericValue.toString()
    target.value = value
  }

  emit('update:modelValue', value)
}
</script>

<template>
  <div :class="['app-input', { 'app-input--error': hasError }]">
    <input
      :type="inputType"
      :value="displayValue"
      @input="onInput"
      @keydown="onKeydown"
      :placeholder="placeholder"
      @paste="onPaste"
      :max="inputType === 'number' ? 1000 : undefined"
      class="app-input__field"
    />
  </div>
</template>

<style scoped lang="scss">
.app-input {
  display: inline-block;
  border: 1px solid var(--color-blue-hover);
  border-radius: 8px;
  font-size: 20px;
  line-height: 1.2;
  max-width: 188px;
  color: var(--color-text-header);

  &__field {
    padding: 12px 15px;
    width: 100%;
    border: none;
    outline: none;

    &::placeholder {
      color: var(--color-blue-hover);
    }
  }

  &--error {
    border-color: red;
  }

  @media (min-width: $md) {
    max-width: 148px;
    font-size: 26px;
    line-height: 1.5;
    &__field {
      padding: 4.5px 15px;
    }
  }
}
</style>
