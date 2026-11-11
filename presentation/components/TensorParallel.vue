<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const layers = [1, 2, 3, 4]
const current = computed(() => Math.min(Math.max(props.step, 0), 9))
const layer = computed(() => Math.min(Math.ceil(current.value / 2), layers.length))
const exchanging = computed(() => current.value > 0 && current.value <= 8 && current.value % 2 === 0)
const summary = computed(() => {
  if (current.value === 0) return 'Token xₜ is ready. Advance to start layer 1.'
  if (current.value === 9) return 'Output head and sampling produce xₜ₊₁. Repeat for the next token.'
  if (!exchanging.value) return `Layer ${layer.value}: both GPUs compute their part for the same token.`
  return `Layer ${layer.value}: exchange partial results before ${layer.value < 4 ? `layer ${layer.value + 1}` : 'the output head'}.`
})
</script>

<template>
  <figure class="tp" :data-step="current" aria-label="Tensor parallelism: both GPUs process the same token at each layer">
    <div class="node">
      <p class="node-label">One node · one Pod · <code>nvidia.com/gpu: 2</code></p>
      <p class="flow-label">One decode step · 4 illustrative layers · input xₜ</p>
      <div class="gpus">
        <div v-for="gpu in [0, 1]" :key="gpu" class="gpu">
          <p class="gpu-label"><GpuIcon width="18" height="18" /> GPU {{ gpu }} · TP rank {{ gpu }}</p>
          <div v-for="index in layers" :key="index" class="layer" :class="{ active: layer === index && current < 9, done: current > index * 2 }">
            <span class="half" :class="gpu === 0 ? 'left' : 'right'" />
            <span class="name">Layer {{ index }}</span>
          </div>
          <span class="token-state" :class="{ visible: current > 0 && current < 9 }" :style="{ transform: `translateY(${Math.max(0, layer - 1) * 30}px)` }" aria-hidden="true" />
        </div>
        <div class="exchange">
          <span v-for="index in layers" :key="index" class="arrow" :class="{ active: exchanging && layer === index }">⇄</span>
          <p>exchange partial results at every layer</p>
        </div>
      </div>
      <p class="output" :class="{ ready: current === 9 }" :aria-hidden="current !== 9">Next token xₜ₊₁</p>
    </div>
    <figcaption aria-live="polite"><strong>{{ current }}/9</strong> {{ summary }}</figcaption>
  </figure>
</template>

<style scoped>
.tp {
  margin: 0;
}

.node {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
}

.node-label,
.gpu-label {
  margin: 0 0 8px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--ink-muted);
}

.gpu-label {
  display: flex;
  align-items: center;
  gap: 4px;
}

.gpus {
  display: grid;
  grid-template-columns: 1fr 110px 1fr;
  gap: 8px;
}

.gpu { position: relative; }

.gpu:nth-child(2) {
  grid-column: 3;
  grid-row: 1;
}

.exchange {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 26px;
}

.arrow {
  height: 30px;
  font-size: 1.2rem;
  line-height: 30px;
  color: var(--accent);
  opacity: 0.2;
  transition: opacity 0.3s, transform 0.3s;
}

.arrow.active { opacity: 1; transform: scale(1.5); animation: exchange 0.6s ease-out; }

.exchange p {
  margin: 4px 0 0;
  font-size: 0.62rem;
  line-height: 1.25;
  text-align: center;
  color: var(--ink-muted);
}

.layer {
  position: relative;
  display: flex;
  align-items: center;
  height: 26px;
  margin-bottom: 4px;
  border: 1px solid var(--line);
  border-radius: 5px;
  overflow: hidden;
}

.layer { transition: border-color 0.3s, opacity 0.3s; }
.layer.active { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.layer.done { opacity: 0.55; }

.half {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 50%;
  background: var(--req-1);
  opacity: 0.85;
}

.half.left { left: 0; }
.half.right { right: 0; background: var(--req-2); }

.name {
  position: relative;
  width: 100%;
  font-size: 0.7rem;
  font-weight: 700;
  text-align: center;
  color: var(--ink);
  text-shadow: 0 1px 2px var(--ink-inverse);
}

.flow-label,
.output { margin: 0 0 10px; font-size: 0.72rem; color: var(--ink-muted); }
.output { margin: 8px 0 0; text-align: center; opacity: 0; }
.output.ready { opacity: 1; color: var(--live); }

.token-state {
  position: absolute;
  top: 32px;
  left: 10%;
  width: 14px;
  height: 14px;
  border: 2px solid var(--ink-inverse);
  border-radius: 50%;
  background: var(--ink);
  opacity: 0;
  transition: transform 0.45s ease, opacity 0.3s;
}
.gpu:nth-child(2) .token-state { left: auto; right: 10%; }
.token-state.visible { opacity: 1; }

figcaption {
  margin-top: 8px;
  min-height: 3em;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

@keyframes exchange {
  50% { transform: scale(1.5) translateX(5px); }
}

@media (prefers-reduced-motion: reduce) {
  .layer, .arrow, .token-state { transition: none; animation: none; }
}
</style>
