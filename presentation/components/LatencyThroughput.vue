<script setup lang="ts">
import { computed, ref } from 'vue'
import { requestMetrics, type RunSummary, summarize } from '../simulator/metrics'
import { loadLevels, sweepSequences, sweepTiming, sweepWorkload } from '../simulator/scenarios'
import { createState, runToEnd, type State } from '../simulator/serving'

const props = withDefaults(defineProps<{ revealed?: number }>(), { revealed: 2 })

const loadId = ref('heavy')
const selected = ref(4)
const loadOptions = loadLevels.map(level => ({ value: level.id, label: `${level.label} (every ${level.interval})` }))
const sequenceOptions = sweepSequences.map(value => ({ value, label: String(value) }))

interface Run {
  state: State
  summary: RunSummary
}

// Every run replays the same arrivals; only the sequence limit changes.
const runs = computed<Run[]>(() => {
  const interval = loadLevels.find(level => level.id === loadId.value)!.interval
  const workload = sweepWorkload(interval)
  return sweepSequences.map(maxSequences => {
    const state = runToEnd(createState({ policy: 'continuous', maxSequences, tokenBudget: 64, timing: sweepTiming }, workload))
    return { state, summary: summarize(state) }
  })
})

const charts = [
  { key: 'throughput', title: 'Output throughput', unit: 'tokens per time unit', value: (s: RunSummary) => s.outputThroughput, better: 'higher' },
  { key: 'ttft', title: 'Median TTFT', unit: 'time units', value: (s: RunSummary) => s.ttft?.median ?? 0, better: 'lower' },
  { key: 'tpot', title: 'Median TPOT', unit: 'time units per token', value: (s: RunSummary) => s.tpot?.median ?? 0, better: 'lower' },
]

const width = 250
const height = 148
const pad = { left: 36, right: 12, top: 18, bottom: 26 }
const xAt = (index: number) => pad.left + (index * (width - pad.left - pad.right)) / (sweepSequences.length - 1)

function chartData(value: (s: RunSummary) => number) {
  const values = runs.value.map(run => value(run.summary))
  const top = Math.max(...values)
  // The scale leaves 15% headroom above the highest point for its value label.
  const scale = top * 1.15 || 1
  const yAt = (v: number) => height - pad.bottom - (v / scale) * (height - pad.top - pad.bottom)
  const points = values.map((v, index) => ({ x: xAt(index), y: yAt(v), v }))
  return { top, topY: yAt(top), points }
}

const chartViews = computed(() => charts.map(chart => ({ ...chart, ...chartData(chart.value) })))
const selectedIndex = computed(() => sweepSequences.indexOf(selected.value))
const detail = computed(() => runs.value[selectedIndex.value])

const perRequest = computed(() => {
  const { state } = detail.value
  const metrics = state.order.map(id => ({ id, ...requestMetrics(state.requests[id]) }))
  const max = Math.max(...metrics.map(metric => metric.e2e ?? 0))
  return metrics.map(metric => ({
    id: metric.id,
    wait: ((metric.queueWait ?? 0) / max) * 100,
    service: (((metric.e2e ?? 0) - (metric.queueWait ?? 0)) / max) * 100,
    e2e: metric.e2e ?? 0,
  }))
})

const format = (value: number | undefined | null, digits = 1) => value === undefined || value === null ? 'N/A' : value.toFixed(digits)
</script>

<template>
  <div class="perf">
    <header>
      <p class="kicker">Simulation D · latency and throughput <span class="badge simulated">Simulated</span></p>
      <h1>More Concurrency Is Not Free</h1>
      <p class="setup">
        16 requests with mixed lengths arrive at a fixed interval. Every run uses the same arrivals;
        only the sequence limit changes. Bigger batches make each step slower.
      </p>
    </header>

    <div class="config">
      <Segmented v-model="loadId" label="Offered load" :options="loadOptions" />
      <Segmented v-model="selected" label="Max sequences" :options="sequenceOptions" />
    </div>

    <div class="charts">
      <figure v-for="(chart, index) in chartViews" :key="chart.key" class="chart" :class="{ unrevealed: index > props.revealed }" :aria-hidden="index > props.revealed">
        <figcaption>{{ chart.title }} <span>{{ chart.better }} is better</span></figcaption>
        <svg :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="`${chart.title} by max sequences`">
          <rect
            :x="xAt(selectedIndex) - 14" :y="pad.top - 6" width="28" :height="height - pad.top - pad.bottom + 6"
            rx="5" class="band"
          />
          <line :x1="pad.left" :x2="width - pad.right" :y1="height - pad.bottom" :y2="height - pad.bottom" class="axis-line" />
          <text :x="pad.left - 6" :y="chart.topY + 4" class="axis-text" text-anchor="end">{{ chart.top >= 10 ? Math.round(chart.top) : chart.top.toFixed(1) }}</text>
          <text :x="pad.left - 6" :y="height - pad.bottom" class="axis-text" text-anchor="end">0</text>
          <text v-for="(value, index) in sweepSequences" :key="value" :x="xAt(index)" :y="height - 6" class="axis-text" text-anchor="middle">{{ value }}</text>
          <g class="series">
            <polyline :points="chart.points.map(point => `${point.x},${point.y}`).join(' ')" />
            <circle v-for="(point, index) in chart.points" :key="index" :cx="point.x" :cy="point.y" :r="index === selectedIndex ? 4.5 : 3" />
          </g>
          <!-- Over the first point, the value starts at the point, so it does not reach the axis labels on the left. -->
          <text
            :x="xAt(selectedIndex) - (selectedIndex === 0 ? 3 : 0)" :y="chart.points[selectedIndex].y - 9"
            class="value-text" :text-anchor="selectedIndex === 0 ? 'start' : 'middle'"
          >{{ format(chart.points[selectedIndex].v) }}</text>
        </svg>
      </figure>
    </div>
    <p class="chart-legend">
      x axis: max sequences · simulated time units, not a GPU benchmark
    </p>

    <div class="detail" :class="{ unrevealed: props.revealed < 2 }" :aria-hidden="props.revealed < 2">
      <div class="detail-head">
        <span class="segmented-label">Max sequences {{ selected }}</span>
        <span class="window">
          {{ detail.summary.completedRequests }}/{{ detail.summary.requests }} requests ·
          window {{ format(detail.summary.window.start) }}–{{ format(detail.summary.window.end) }}
        </span>
      </div>
      <div class="detail-body">
        <dl class="numbers">
          <div><dt>Output<br>throughput</dt><dd>{{ format(detail.summary.outputThroughput, 2) }}</dd></div>
          <div><dt>Median<br>TTFT</dt><dd>{{ format(detail.summary.ttft?.median) }}</dd></div>
          <div><dt>Median<br>TPOT</dt><dd>{{ format(detail.summary.tpot?.median, 2) }}</dd></div>
          <div><dt>Median<br>E2E</dt><dd>{{ format(detail.summary.e2e?.median) }}</dd></div>
          <div><dt>Mean<br>running</dt><dd>{{ format(detail.summary.meanRunning, 1) }}</dd></div>
        </dl>
        <div>
          <div class="bars" role="img" aria-label="End-to-end latency per request, split into queue wait and service">
            <div v-for="bar in perRequest" :key="bar.id" class="bar" :title="`${bar.id}: ${bar.e2e.toFixed(1)}`">
              <span class="service" :style="{ height: `${bar.service}%` }" />
              <span class="wait" :style="{ height: `${bar.wait}%` }" />
            </div>
          </div>
          <p class="bars-caption">Per-request latency, r1 to r16: <i class="wait-key" /> queue wait <i class="service-key" /> prefill and decode</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.perf {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 9px;
}

header h1 {
  margin: 2px 0 4px;
  font-size: 1.9rem;
}

.setup {
  margin: 0;
  font-size: 0.82rem;
}

.config {
  display: flex;
  justify-content: space-between;
}

.charts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.chart {
  margin: 0;
  padding: 6px 8px 2px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.unrevealed {
  visibility: hidden;
}

figcaption {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--ink);
}

figcaption span {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--ink-faint);
}

svg {
  display: block;
  width: 100%;
}

.band {
  fill: rgb(214 34 147 / 0.14);
}

.axis-line {
  stroke: var(--line);
}

.axis-text {
  font-size: 12px;
  fill: var(--ink-faint);
}

.value-text {
  font-size: 13px;
  font-weight: 700;
  fill: var(--ink);
}

.series polyline {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
}

.series circle {
  fill: var(--accent);
}

.chart-legend {
  margin: -2px 0 0;
  font-size: 0.8rem;
  color: var(--ink-faint);
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.window {
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
  color: var(--ink-faint);
}

.detail-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: end;
}

.numbers {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin: 0;
}

.numbers dt {
  font-size: 0.8rem;
  line-height: 1.2;
  color: var(--ink-faint);
}

.numbers dd {
  margin: 2px 0 0;
  font-size: 1.15rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}

.bars {
  display: grid;
  grid-template-columns: repeat(16, 1fr);
  align-items: end;
  gap: 3px;
  height: 64px;
}

.bar {
  display: flex;
  flex-direction: column-reverse;
  height: 100%;
}

.bar .wait {
  border: 1px dashed var(--ink-faint);
  border-bottom: none;
}

.bar .service {
  background: var(--accent);
}

.bars-caption {
  margin: 3px 0 0;
  font-size: 0.75rem;
  color: var(--ink-faint);
}

.wait-key,
.service-key {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin: 0 3px 0 6px;
}

.wait-key {
  border: 1px dashed var(--ink-faint);
}

.service-key {
  background: var(--accent);
}
</style>
