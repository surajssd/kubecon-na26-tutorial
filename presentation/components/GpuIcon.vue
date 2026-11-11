<script setup lang="ts">
import vllmMark from '../assets/companies/vllm-mark.svg'
</script>

<template>
  <svg class="gpu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="24" height="24" role="img" aria-label="GPU running vLLM">
    <rect x="7" y="7" width="18" height="18" rx="2" fill="var(--surface-raised)" stroke="currentColor" stroke-width="2" />
    <path d="M11 2v5 M16 2v5 M21 2v5 M11 25v5 M16 25v5 M21 25v5 M2 11h5 M2 16h5 M2 21h5 M25 11h5 M25 16h5 M25 21h5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    <image :href="vllmMark" x="7" y="7" width="18" height="18" />
  </svg>
</template>

<style scoped>
.gpu-icon {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: -0.2em;
  color: var(--live);
}
</style>
