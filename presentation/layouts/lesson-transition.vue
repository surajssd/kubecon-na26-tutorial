<script setup lang="ts">
defineProps<{
  problem: string
  next: number
}>()
</script>

<template>
  <div class="slidev-layout lesson-transition">
    <header>
      <p class="kicker">Next problem · lesson {{ next }}</p>
      <h1>{{ problem }}</h1>
    </header>
    <div class="body">
      <div class="content">
        <slot />
      </div>
      <DeploymentLadder :current="next" compact />
    </div>
  </div>
</template>

<style scoped>
.lesson-transition {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

header h1 {
  margin: 6px 0 0;
  font-size: 2rem;
}

.body {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 32px;
  align-items: start;
}

.content {
  min-width: 0;
}

.content :deep(pre.slidev-code code) {
  white-space: pre-wrap;
}

.content :deep(ol) {
  margin: 0;
  padding-left: 1.2rem;
}

.content :deep(li) {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
}

.content :deep(li::marker) {
  font-weight: 700;
  color: var(--accent);
}

.content :deep(pre.slidev-code) {
  margin: 4px 0 2px;
}
</style>
