<script setup lang="ts">
interface BarSegment {
  label: string
  value: number
  tone: 'weights' | 'runtime' | 'kv' | 'budget' | 'free' | 'over'
  note?: string
  flag?: string
  click?: number
}

const props = defineProps<{
  title: string
  segments: BarSegment[]
  scale?: number
  clicks?: number
}>()

function isPending(segment: BarSegment): boolean {
  return segment.click !== undefined && props.clicks !== undefined && props.clicks < segment.click
}
</script>

<template>
  <figure class="stacked">
    <figcaption>{{ title }}</figcaption>
    <div class="track" :style="{ width: scale ? `${scale * 100}%` : '100%' }">
      <div v-for="segment in segments" :key="segment.label" class="segment" :class="[segment.tone, { pending: isPending(segment) }]" :style="{ flex: segment.value }">
        <span class="label">{{ segment.label }}</span>
        <span v-if="segment.note" class="note">{{ segment.note }}</span>
        <code v-if="segment.flag" class="flag">{{ segment.flag }}</code>
      </div>
    </div>
  </figure>
</template>

<style scoped>
.stacked {
  margin: 0;
}

figcaption {
  margin-bottom: 5px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.track {
  display: flex;
  gap: 3px;
  min-height: 54px;
}

.segment {
  position: relative;
  z-index: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: 6px 10px;
  border: 1px dashed transparent;
  border-radius: 6px;
  color: var(--ink-inverse);
  overflow: hidden;
  transition: border-color 0.3s;
}

.segment::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--fill, transparent);
  transform-origin: left;
  transition: transform 0.6s ease-out;
}

.segment > * {
  transition: opacity 0.3s 0.35s;
}

.segment.pending {
  border-color: var(--line);
}

.segment.pending::before {
  transform: scaleX(0);
}

.segment.pending > * {
  opacity: 0;
  transition-delay: 0s;
}

.label {
  font-size: 0.82rem;
  font-weight: 700;
  white-space: nowrap;
}

.note {
  font-size: 0.68rem;
  white-space: nowrap;
  opacity: 0.8;
}

.flag {
  align-self: flex-start;
  margin-top: 3px;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 0.62rem;
  white-space: nowrap;
  color: var(--ink-inverse);
  background: color-mix(in srgb, var(--ink-inverse) 13%, transparent);
}

.weights { --fill: var(--req-2); }
.runtime { --fill: var(--req-5); }
.kv { --fill: var(--req-1); }
.budget { --fill: var(--req-3); }

.free {
  color: var(--ink-muted);
  border-color: var(--line);
}

.over {
  --fill: repeating-linear-gradient(-45deg, rgb(214 34 147 / 0.55) 0 8px, rgb(214 34 147 / 0.3) 8px 16px);
  color: var(--ink);
}

@media (prefers-reduced-motion: reduce) {
  .segment::before,
  .segment > * {
    transition: none;
  }
}
</style>
