<script setup lang="ts">
import { computed } from 'vue'

interface Run {
  concurrency: number
  completed: number
}

const props = defineProps<{ runs: Run[] }>()

const runSeconds = 60

// traffic.py gives each open request its own worker, so a run is `concurrency` lanes of back-to-back requests.
const lanes = computed(() => props.runs.map((run) => {
  const perLane = Math.floor(run.completed / run.concurrency)
  const extra = run.completed % run.concurrency
  const counts = Array.from({ length: run.concurrency }, (_, lane) => perLane + (lane < extra ? 1 : 0))
  const interval = runSeconds / run.completed
  return { ...run, counts, interval: interval.toFixed(1) }
}))

// Every lane has the same number of slots, so all boxes have one width and the rows compare by count. Box widths do not show time.
const slots = computed(() => Math.max(...lanes.value.flatMap((run) => run.counts)))
</script>

<template>
  <figure class="concurrency-lanes" :style="{ '--slots': slots }">
    <div
      v-for="run in lanes"
      :key="run.concurrency"
      class="run"
      role="img"
      :aria-label="`Concurrency ${run.concurrency}: ${run.completed} requests finished in one minute, one finished every ${run.interval} seconds`"
    >
      <div class="label">
        <strong>Concurrency {{ run.concurrency }}</strong>
        <span>{{ run.concurrency }} {{ run.concurrency === 1 ? 'request' : 'requests' }} open at a time</span>
      </div>
      <div class="lanes">
        <div v-for="(count, lane) in run.counts" :key="lane" class="lane">
          <span v-for="request in count" :key="request" class="request" />
        </div>
      </div>
      <div class="result">
        <strong>{{ run.completed }} finished</strong>
        <span>one finished every {{ run.interval }} s</span>
      </div>
    </div>
  </figure>
</template>

<style scoped>
.concurrency-lanes {
  margin: 0;
}

.run {
  display: grid;
  grid-template-columns: 190px 1fr 170px;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
}

.label,
.result {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
  line-height: 1.3;
  color: var(--ink-muted);
}

.label strong,
.result strong {
  font-size: 1rem;
  color: var(--ink);
}

.result strong {
  font-size: 1.4rem;
}

.lanes {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lane {
  display: grid;
  grid-template-columns: repeat(var(--slots), 1fr);
  gap: 2px;
  height: 18px;
}

.request {
  border-radius: 3px;
  background: var(--req-1);
}

</style>
