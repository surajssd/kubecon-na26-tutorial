<script setup lang="ts" generic="T extends string | number">
defineProps<{
  label: string
  options: { value: T, label: string }[]
  disabled?: boolean
}>()

const model = defineModel<T>({ required: true })
</script>

<!-- Buttons rather than a select: Slidev ignores navigation keys only while a button has focus. -->
<template>
  <div class="segmented" role="group" :aria-label="label" @mousedown.prevent>
    <span class="segmented-label">{{ label }}</span>
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :aria-pressed="model === option.value"
      :disabled="disabled"
      @click="model = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>
