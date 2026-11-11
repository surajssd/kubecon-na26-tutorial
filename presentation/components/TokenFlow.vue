<script setup lang="ts">
import { useIsSlideActive, useSlideContext } from '@slidev/client'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const prompt = ['Explain', ' Kubernetes', ' in', ' one', ' sentence', '.']
const reply = ['Kubernetes', ' runs', ' containers', ' …']

type Phase = 'rest' | 'prefill' | 'decode' | 'done'
interface Frame { phase: Phase, shown: number, ms: number }

// One loop: a pause, one prefill pass that reads the whole prompt and makes reply token 1, one decode step for each later token, then a hold on the full reply.
const frames: Frame[] = [
  { phase: 'rest', shown: 0, ms: 700 },
  { phase: 'prefill', shown: 0, ms: 1100 },
  { phase: 'prefill', shown: 1, ms: 900 },
  ...reply.slice(1).map((_, index) => ({ phase: 'decode' as const, shown: index + 2, ms: 750 })),
  { phase: 'done', shown: reply.length, ms: 2200 },
]
const lastFrame = frames.length - 1

// Only the visible slide animates. The overview, the next-slide preview, and exports show the finished reply.
const { $renderContext } = useSlideContext()
const active = useIsSlideActive()
const animated = computed(() => active.value && ['slide', 'presenter'].includes($renderContext.value))

const index = ref(lastFrame)
let timer: ReturnType<typeof setTimeout> | undefined

function stop() {
  clearTimeout(timer)
  timer = undefined
}

function schedule() {
  timer = setTimeout(() => {
    index.value = (index.value + 1) % frames.length
    schedule()
  }, frames[index.value].ms)
}

function sync() {
  stop()
  if (animated.value && !document.hidden) {
    index.value = 0
    schedule()
  }
  else {
    index.value = lastFrame
  }
}

watch(animated, sync)
onMounted(() => {
  sync()
  document.addEventListener('visibilitychange', sync)
})
onBeforeUnmount(() => {
  stop()
  document.removeEventListener('visibilitychange', sync)
})

const frame = computed(() => frames[index.value])
const working = computed(() => frame.value.phase === 'prefill' || frame.value.phase === 'decode')
const emitted = computed(() => index.value > 0 && frame.value.shown > frames[index.value - 1].shown)
const label = computed(() => {
  if (frame.value.phase === 'prefill')
    return emitted.value ? 'Prefill: the same pass makes the first token' : 'Prefill: one pass reads the whole prompt'
  if (frame.value.phase === 'decode')
    return `Decode step ${frame.value.shown - 1}: one new token`
  if (frame.value.phase === 'done')
    return 'Prefill makes the first token, then decode makes one token per step'
  return ''
})
</script>

<template>
  <div class="token-flow">
    <div class="row">
      <div class="token-stream prompt" :class="{ lit: frame.phase === 'prefill' }">
        <span v-for="(token, position) in prompt" :key="position">{{ token }}</span>
      </div>
      <div class="model-box" :class="{ busy: working }">
        Model<br><span>weights in GPU memory</span>
        <i class="arrow in" :class="{ lit: frame.phase === 'prefill' }" aria-hidden="true">→</i>
        <i class="arrow out" :class="{ lit: emitted }" aria-hidden="true">→</i>
        <i v-if="working" :key="frame.phase === 'prefill' ? 'prefill' : index" class="pulse" aria-hidden="true" />
      </div>
      <div class="token-stream reply">
        <span
          v-for="(token, position) in reply" :key="position"
          :class="{ shown: position < frame.shown, fresh: emitted && position === frame.shown - 1 }"
        >{{ token }}</span>
      </div>
    </div>
    <p class="phase">{{ label }}</p>
  </div>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 1fr 150px 1fr;
  align-items: center;
  gap: 26px;
  margin: 18px 0 4px;
}

.row .token-stream {
  font-size: 0.95rem;
}

.prompt span,
.reply span {
  transition: box-shadow 0.3s, transform 0.3s, opacity 0.3s;
}

.prompt.lit span {
  box-shadow: 0 0 0 2px var(--accent);
  transform: translateY(-2px);
}

.reply span {
  opacity: 0;
  transform: translateY(6px);
}

.reply span.shown {
  opacity: 1;
  transform: none;
}

.reply span.fresh {
  box-shadow: 0 0 0 2px var(--accent);
}

/* The arrows sit in the grid gaps on each side of the model box. */
.arrow {
  position: absolute;
  top: 50%;
  font-size: 1rem;
  font-style: normal;
  font-weight: 700;
  color: var(--ink-faint);
  transform: translateY(-50%);
  transition: color 0.3s;
}

.arrow.in {
  left: -20px;
}

.arrow.out {
  right: -20px;
}

.arrow.lit {
  color: var(--accent);
}

.model-box {
  position: relative;
  padding: 16px;
  text-align: center;
  font-weight: 800;
  border: 1px solid var(--accent);
  border-radius: 12px;
  box-shadow: 0 0 24px -10px var(--accent);
  transition: box-shadow 0.3s;
}

.model-box.busy {
  box-shadow: 0 0 32px -4px var(--accent);
}

.model-box span {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--ink-muted);
}

/* Restarted for every decode frame, so each decode step shows one pulse. Both prefill frames share one pulse, because prefill is one pass. */
.pulse {
  position: absolute;
  inset: -1px;
  border: 2px solid var(--accent);
  border-radius: 12px;
  pointer-events: none;
  animation: model-pulse 0.6s ease-out forwards;
}

@keyframes model-pulse {
  from { opacity: 0.9; transform: scale(1); }
  to { opacity: 0; transform: scale(1.12); }
}

.phase {
  min-height: 1.4em;
  margin: 2px 0 0;
  text-align: center;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--accent);
}

@media (prefers-reduced-motion: reduce) {
  .pulse { display: none; }
  .prompt span, .reply span, .arrow, .model-box { transition: none; }
}
</style>
