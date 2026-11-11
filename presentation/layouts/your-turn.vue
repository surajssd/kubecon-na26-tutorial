<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  lesson: string
  steps: string
  minutes: number
}>()

const pathParts = computed(() => ['tutorial/', `${props.lesson}/`, 'README.md'])
</script>

<template>
  <div class="slidev-layout your-turn">
    <aside>
      <p class="kicker">Hands-on</p>
      <h1 class="title">Your Turn</h1>
      <p class="path">
        Open
        <code><template v-for="(part, index) in pathParts" :key="part"><wbr v-if="index > 0"><span class="segment">{{ part }}</span></template></code>
      </p>
      <p class="steps">{{ steps }}</p>
      <div class="timebox">
        <span class="number">{{ minutes }}</span>
        <span>{{ minutes === 1 ? 'minute' : 'minutes' }}</span>
      </div>
      <p class="help">Raise your hand if a step fails. We will come to you.</p>
    </aside>
    <div class="content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.your-turn {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 36px;
}

aside {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 28px;
  border-right: 1px solid var(--line);
}

.title {
  margin: 0;
  font-size: 2.8rem;
}

.path {
  margin: 4px 0 0;
  font-size: 0.85rem;
  color: var(--ink);
}

/* Wrap the README path only after a slash, never at the hyphens in lesson names. */
.path .segment {
  white-space: nowrap;
}

.steps {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--ink);
}

.timebox {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 10px;
  color: var(--ink-muted);
}

.timebox .number {
  font-size: 3.2rem;
  font-weight: 800;
  line-height: 1;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}

.help {
  margin-top: auto;
  font-size: 0.78rem;
}

.content {
  align-self: center;
  min-width: 0;
}

.content :deep(h2) {
  margin: 0 0 14px;
  font-size: 1.6rem;
  line-height: 1.2;
}

.content :deep(p),
.content :deep(li) {
  font-size: 1.05rem;
}
</style>
