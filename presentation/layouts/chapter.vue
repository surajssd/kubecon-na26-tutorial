<script setup lang="ts">
import logo from '../assets/kubecon/kubecon-na-2026-logo-white.svg'

defineProps<{
  lesson?: number
}>()
</script>

<template>
  <div class="slidev-layout chapter" :class="{ 'with-ladder': lesson }">
    <img class="logo" :src="logo" alt="KubeCon + CloudNativeCon North America 2026">
    <div class="chapter-body">
      <p v-if="lesson" class="kicker">Lesson {{ lesson }}</p>
      <slot />
    </div>
    <DeploymentLadder v-if="lesson" class="chapter-ladder" :current="lesson" compact />
  </div>
</template>

<style scoped>
.chapter {
  position: relative;
  display: flex;
  align-items: center;
  background: var(--brand-blue);
}

.logo {
  position: absolute;
  top: 22px;
  left: 34px;
  height: 58px;
}

.chapter.with-ladder {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 40px;
}

.chapter-body :deep(h1) {
  margin: 10px 0 12px;
  font-size: 3rem;
  line-height: 1.05;
}

.chapter-body :deep(p) {
  font-size: 1.1rem;
  color: var(--brand-ice);
}

.chapter-body :deep(.kicker) {
  font-size: 0.8rem;
  color: var(--brand-yellow);
}
</style>
