<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { playbackSpeeds, usePlayback } from '../composables/usePlayback'
import { requestClass } from '../composables/requestClass'
import { addRequest, type Cell, type Event, finishedAt, idle, initialState, isDone, type Policy, runToEnd, type State, step } from '../simulator/batching'
import { batchingPresets } from '../simulator/scenarios'

interface Lane {
  policy: Policy
  title: string
  state: State
  events: Event[]
}

type Command = { kind: 'step' } | { kind: 'add', outputTokens: number }

const titles: Record<Policy, string> = { static: 'Static batching', continuous: 'Continuous batching' }
const policies: Policy[] = ['static', 'continuous']
const maxRequests = 8
const maxColumns = 16
const lengthOptions = [1, 2, 4, 8].map(value => ({ value, label: String(value) }))
const capacityOptions = [1, 2, 3, 4].map(value => ({ value, label: String(value) }))
const presetOptions = batchingPresets.map(preset => ({ value: preset.id, label: preset.label }))
const speedOptions = playbackSpeeds.map(speed => ({ value: speed.delay, label: speed.label }))

const presetId = ref(batchingPresets[0].id)
const capacity = ref(batchingPresets[0].scenario.capacity)
const newLength = ref(2)
const notice = ref('')
const log = ref<Command[]>([])
let replayQueue: Command[] = []

function freshLanes(): Lane[] {
  const preset = batchingPresets.find(item => item.id === presetId.value)!
  const scenario = { ...preset.scenario, capacity: capacity.value }
  return policies.map(policy => ({ policy, title: titles[policy], state: initialState(policy, scenario), events: [] }))
}

const lanes = ref<Lane[]>(freshLanes())
const clock = computed(() => lanes.value[0].state.iteration)
const finished = computed(() => lanes.value.every(lane => isDone(lane.state)))
const requests = computed(() => Object.entries(lanes.value[0].state.targets).map(([id, outputTokens]) => ({ id, outputTokens })))
const totalColumns = computed(() => projectedColumns(lanes.value))
const stepNumbers = computed(() => Array.from({ length: totalColumns.value }, (_, index) => index + 1))
const rowHeight = computed(() => [56, 48, 38, 30][capacity.value - 1])

function projectedColumns(candidate: Lane[]): number {
  return Math.max(1, ...candidate.map(lane => runToEnd(lane.state).iteration))
}

function apply(command: Command) {
  if (command.kind === 'add') {
    const id = `r${requests.value.length + 1}`
    lanes.value = lanes.value.map(lane => ({ ...lane, state: addRequest(lane.state, { id, outputTokens: command.outputTokens }), events: [] }))
    return
  }
  lanes.value = lanes.value.map((lane) => {
    if (isDone(lane.state))
      return { ...lane, state: idle(lane.state), events: [] }
    const next = step(lane.state)
    return { ...lane, state: next.state, events: next.events }
  })
}

function run(command: Command) {
  apply(command)
  log.value = [...log.value, command]
}

function advance(): boolean {
  const command: Command | undefined = replayQueue.shift() ?? (finished.value ? undefined : { kind: 'step' })
  if (command === undefined)
    return false
  run(command)
  return replayQueue.length > 0 || !finished.value
}

const { playing, delay, play, pause } = usePlayback(advance)

function reset() {
  pause()
  replayQueue = []
  log.value = []
  notice.value = ''
  lanes.value = freshLanes()
}

function replay() {
  const recorded = log.value
  reset()
  replayQueue = [...recorded]
  play()
}

function togglePlay() {
  if (playing.value)
    pause()
  else if (finished.value)
    replay()
  else
    play()
}

function addNewRequest() {
  if (requests.value.length >= maxRequests) {
    notice.value = `This demo holds up to ${maxRequests} requests.`
    return
  }
  const id = `r${requests.value.length + 1}`
  const candidate = lanes.value.map(lane => ({ ...lane, state: addRequest(lane.state, { id, outputTokens: newLength.value }) }))
  if (projectedColumns(candidate) > maxColumns) {
    notice.value = `That request would need more than ${maxColumns} steps.`
    return
  }
  notice.value = ''
  run({ kind: 'add', outputTokens: newLength.value })
}

watch(presetId, (id) => {
  capacity.value = batchingPresets.find(item => item.id === id)!.scenario.capacity
  reset()
})
watch(capacity, reset)

function doneAt(lane: Lane): number | null {
  return isDone(lane.state) ? finishedAt(lane.state) : null
}

function tokensEmitted(state: State): number {
  return Object.values(state.emitted).reduce((sum, count) => sum + count, 0)
}

function totalTokens(state: State): number {
  return Object.values(state.targets).reduce((sum, count) => sum + count, 0)
}

function idleSlotSteps(state: State): number {
  const end = isDone(state) ? finishedAt(state) : state.columns.length
  return state.columns.slice(0, end).flat().filter(cell => cell.kind !== 'token').length
}

// The key includes the cell kind so a placeholder that becomes a real cell
// remounts and plays its entry animation.
function gridItems(lane: Lane): { key: string, cell: Cell | undefined, after: boolean }[] {
  const end = doneAt(lane)
  return Array.from({ length: capacity.value }, (_, slot) => slot).flatMap(slot => stepNumbers.value.map((number) => {
    const cell = lane.state.columns[number - 1]?.[slot]
    const after = end !== null && number > end
    return { key: `${slot}-${number}-${after ? 'after' : cell?.kind ?? 'future'}`, cell, after }
  }))
}

function cellClass(item: { cell: Cell | undefined, after: boolean }) {
  if (item.after)
    return 'after'
  if (item.cell === undefined)
    return 'future'
  if (item.cell.kind === 'token')
    return ['token', requestClass(item.cell.requestId), { last: item.cell.last }]
  return item.cell.kind
}

function status(lane: Lane): string {
  const { state, events } = lane
  if (state.iteration === 0)
    return `${state.waiting.length} requests waiting.`
  const admitted = events.filter(event => event.type === 'admit').map(event => event.requestId)
  const completed = events.filter(event => event.type === 'finish').map(event => event.requestId)
  const parts: string[] = []
  if (admitted.length > 0)
    parts.push(`${admitted.join(' and ')} ${admitted.length === 1 ? 'starts' : 'start'}`)
  if (completed.length > 0)
    parts.push(`${completed.join(' and ')} finished`)
  const held = state.slots.some(slot => slot?.finished)
  const canStart = state.policy === 'continuous' || state.slots.every(slot => slot === null)
  if (state.waiting.length > 0 && held)
    parts.push(`${state.waiting[0]} waits for the whole batch`)
  else if (state.waiting.length > 0 && canStart && state.slots.includes(null))
    parts.push(`${state.waiting[0]} starts next step`)
  if (parts.length === 0)
    parts.push('Decoding')
  return `${parts.join('. ')}.`
}
</script>

<template>
  <div class="batching">
    <header>
      <p class="kicker">Simulation A · decode only <span class="badge simulated">Simulated</span></p>
      <h1>Static vs Continuous Batching</h1>
      <p class="setup">
        Same requests, same GPU with <strong>{{ capacity }} sequence {{ capacity === 1 ? 'slot' : 'slots' }}</strong>.
        Each step emits one token for every running request.
      </p>
    </header>

    <div class="config">
      <Segmented v-model="presetId" label="Preset" :options="presetOptions" />
      <div class="config-right">
        <Segmented v-model="capacity" label="Slots" :options="capacityOptions" />
        <Segmented v-model="delay" label="Speed" :options="speedOptions" />
      </div>
    </div>

    <div class="requests" @mousedown.prevent>
      <ul class="legend" aria-label="Requests">
        <li v-for="request in requests" :key="request.id" :class="requestClass(request.id)">
          <span class="swatch" />{{ request.id }} <span class="muted">{{ request.outputTokens }}</span>
        </li>
      </ul>
      <div class="add">
        <Segmented v-model="newLength" label="New request tokens" :options="lengthOptions" />
        <button type="button" class="sim-button" @click="addNewRequest">Add request</button>
      </div>
    </div>

    <div class="board" :style="{ '--steps': totalColumns, '--row': `${rowHeight}px` }" :class="{ dense: totalColumns > 9, compact: rowHeight < 40 }">
      <div class="axis-label">Step</div>
      <div class="axis">
        <span v-for="number in stepNumbers" :key="number" :class="{ current: number === clock }">{{ number }}</span>
      </div>

      <template v-for="lane in lanes" :key="lane.policy">
        <div class="lane-info" :class="lane.policy">
          <div class="lane-title">{{ lane.title }}</div>
          <p class="status" aria-live="polite">
            <span v-if="doneAt(lane) !== null" class="done">Done in {{ doneAt(lane) }} steps</span>
            <template v-else>{{ status(lane) }}</template>
          </p>
          <p class="metrics">
            <span>{{ tokensEmitted(lane.state) }}/{{ totalTokens(lane.state) }} tokens</span>
            <span>{{ idleSlotSteps(lane.state) }} idle {{ idleSlotSteps(lane.state) === 1 ? 'slot-step' : 'slot-steps' }}</span>
          </p>
        </div>
        <div class="grid" role="img" :aria-label="`${lane.title} slots by step`">
          <div v-for="item in gridItems(lane)" :key="item.key" class="cell" :class="cellClass(item)">
            <template v-if="!item.after && item.cell?.kind === 'token'">
              <span class="id">{{ item.cell.requestId }}</span>
              <span class="count">{{ item.cell.token }}/{{ lane.state.targets[item.cell.requestId] }}</span>
            </template>
            <template v-else-if="!item.after && item.cell?.kind === 'held'">
              <span>idle</span>
              <span class="why">{{ item.cell.requestId }} done</span>
            </template>
            <span v-else-if="!item.after && item.cell?.kind === 'empty'">free</span>
          </div>
        </div>
      </template>
    </div>

    <!--
      Slidev's navigation bar covers the bottom-left corner, so the buttons stay on the right.
      Slidev ignores navigation keys while a button has focus, so a mouse click must not focus
      a button, or the presenter's clicker stops working.
    -->
    <footer class="controls" @mousedown.prevent>
      <span class="clock">Step {{ clock }} of {{ totalColumns }}</span>
      <span class="notice" aria-live="polite">{{ notice }}</span>
      <button type="button" class="sim-button primary" :disabled="finished || playing" @click="run({ kind: 'step' })">Step</button>
      <button type="button" class="sim-button" @click="togglePlay">{{ playing ? 'Pause' : finished ? 'Replay' : 'Play' }}</button>
      <button type="button" class="sim-button" :disabled="clock === 0 && log.length === 0" @click="reset">Reset</button>
    </footer>
  </div>
</template>

<style scoped>
.batching {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 10px;
}

header h1 {
  margin: 2px 0 4px;
  font-size: 1.9rem;
}

.setup {
  margin: 0;
  font-size: 0.9rem;
}

.config,
.requests {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.config-right,
.add {
  display: flex;
  align-items: center;
  gap: 14px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.8rem;
  color: var(--ink);
}

.legend li {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0;
  color: var(--ink);
}

.swatch {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  background: var(--req);
}

.board {
  display: grid;
  grid-template-columns: 210px 1fr;
  column-gap: 16px;
  row-gap: 10px;
}

.axis-label,
.axis {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.axis-label {
  align-self: end;
}

.axis,
.grid {
  display: grid;
  grid-template-columns: repeat(var(--steps), minmax(0, 1fr));
  gap: 5px;
}

.axis span {
  text-align: center;
  border-radius: 999px;
  transition: color 0.2s, background-color 0.2s;
}

.axis span.current {
  color: var(--accent-ink);
  background: var(--accent);
}

.lane-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  padding-left: 12px;
  border-left: 3px solid var(--line);
}

.lane-info.continuous {
  border-left-color: var(--accent);
}

.lane-title {
  font-size: 1.02rem;
  font-weight: 700;
  white-space: nowrap;
}

.done {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--accent-ink);
  background: var(--accent);
  animation: pop 0.35s ease-out;
}

.lane-info.static .done {
  color: var(--ink);
  background: var(--line);
}

.status {
  min-height: 2.5em;
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.25;
}

.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  margin: 0;
  font-size: 0.7rem;
  font-variant-numeric: tabular-nums;
  color: var(--ink-faint);
}

.cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: var(--row);
  border-radius: 7px;
  font-size: 0.68rem;
  line-height: 1.1;
  overflow: hidden;
}

.cell.future {
  border: 1px solid var(--line);
  opacity: 0.45;
}

.cell.after {
  opacity: 0.18;
  border: 1px solid var(--line);
}

.cell.token {
  color: var(--ink-inverse);
  background: var(--req);
  box-shadow: 0 0 16px -6px var(--req);
  animation: pop 0.3s ease-out;
}

.cell.token .id {
  font-size: 0.92rem;
  font-weight: 800;
}

.cell.token .count {
  font-variant-numeric: tabular-nums;
  opacity: 0.75;
}

.cell.token.last::after {
  content: "✓";
  position: absolute;
  top: 2px;
  right: 6px;
  font-size: 0.72rem;
  font-weight: 800;
}

.cell.held {
  color: var(--ink-muted);
  border: 1px dashed var(--ink-faint);
  background: repeating-linear-gradient(-45deg, transparent 0 6px, rgb(var(--tint) / 0.06) 6px 12px);
  animation: pop 0.3s ease-out;
}

.cell.held .why {
  font-size: 0.6rem;
  color: var(--ink-faint);
}

.cell.empty {
  color: var(--ink-faint);
  border: 1px dashed var(--line);
  animation: pop 0.3s ease-out;
}

.board.compact .cell {
  flex-direction: row;
  gap: 4px;
}

.board.dense .cell .why,
.board.dense .cell.token .count {
  display: none;
}

.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}

.clock {
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
  color: var(--ink-muted);
}

.notice {
  flex: 1;
  font-size: 0.78rem;
  color: var(--req-3);
}

@media (prefers-reduced-motion: reduce) {
  .cell, .done { animation: none; }
}
</style>
