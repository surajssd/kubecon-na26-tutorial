<script setup lang="ts">
import { computed, ref } from 'vue'
import lwsIcon from '../assets/icons/lws.svg'
import podIcon from '../assets/icons/pod.svg'
import stsIcon from '../assets/icons/sts.svg'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

const replicas = ref(1)
const size = ref(2)
const replicaOptions = [1, 2, 3].map(value => ({ value, label: String(value) }))
const sizeOptions = [2, 3].map(value => ({ value, label: String(value) }))

type Level = 'lws' | 'leaders' | 'leader' | 'workers' | 'worker'

// Step 0 is the LWS concept diagram. Steps 1 to 5 each add one level of the objects that one LeaderWorkerSet creates.
const levelOrder: Level[] = ['lws', 'leaders', 'leader', 'workers', 'worker']
const rank = (level: Level) => levelOrder.indexOf(level) + 1
const current = computed(() => Math.min(Math.max(props.step, 0), levelOrder.length))

const icons: Record<Level, string> = { lws: lwsIcon, leaders: stsIcon, leader: podIcon, workers: stsIcon, worker: podIcon }

const width = 560
const height = 500
const groupsLeft = 112
const groupsRight = 548
const centerX = (groupsLeft + groupsRight) / 2
const gap = 14
const ellipsisWidth = 40
const maxBoxWidth = 132
const nameGap = 15

const rows: Record<Level, { y: number, size: number }> = {
  lws: { y: 46, size: 58 },
  leaders: { y: 146, size: 54 },
  leader: { y: 258, size: 50 },
  workers: { y: 342, size: 48 },
  worker: { y: 422, size: 34 },
}
const boxTop = 222
const boxBottom = 462
const groupLabelY = 482

interface Node { key: string, level: Level, x: number, name?: string }
interface Link { key: string, level: Level, d: string }
interface Group { key: string, x: number, width: number, label: string }

function curve(x1: number, y1: number, x2: number, y2: number) {
  const mid = (y1 + y2) / 2
  return `M ${x1} ${y1} C ${x1} ${mid}, ${x2} ${mid}, ${x2} ${y2}`
}

// Lay out the owner tree. A link carries the level of the object it points to, so it appears with that object.
function buildTree(labels: string[], workers: number, ellipsisAfter: number | null, name?: string) {
  const extra = ellipsisAfter === null ? 0 : ellipsisWidth
  const count = labels.length
  const boxWidth = Math.min(maxBoxWidth, (groupsRight - groupsLeft - gap * (count - 1) - extra) / count)
  const total = boxWidth * count + gap * (count - 1) + extra
  const labelSpace = name ? nameGap : 0
  const top = (level: Level) => rows[level].y - rows[level].size / 2
  const bottom = (level: Level) => rows[level].y + rows[level].size / 2 + labelSpace

  const nodes: Node[] = [
    { key: 'lws', level: 'lws', x: centerX, name },
    { key: 'leaders', level: 'leaders', x: centerX, name },
  ]
  const links: Link[] = [{ key: 'lws', level: 'leaders', d: `M ${centerX} ${bottom('lws')} V ${top('leaders')}` }]
  const groups: Group[] = []
  let ellipsisX: number | null = null
  let x = centerX - total / 2
  labels.forEach((label, group) => {
    const mid = x + boxWidth / 2
    const leaderName = name && `${name}-${group}`
    groups.push({ key: label, x, width: boxWidth, label })
    nodes.push({ key: `leader-${group}`, level: 'leader', x: mid, name: leaderName })
    nodes.push({ key: `workers-${group}`, level: 'workers', x: mid, name: leaderName })
    links.push({ key: `leader-${group}`, level: 'leader', d: curve(centerX, bottom('leaders'), mid, top('leader')) })
    links.push({ key: `workers-${group}`, level: 'workers', d: `M ${mid} ${bottom('leader')} V ${top('workers')}` })
    const spacing = Math.min(60, (boxWidth - 16) / workers)
    for (let worker = 0; worker < workers; worker++) {
      const workerX = mid + (worker - (workers - 1) / 2) * spacing
      nodes.push({ key: `worker-${group}-${worker}`, level: 'worker', x: workerX, name: leaderName && `${leaderName}-${worker + 1}` })
      links.push({ key: `worker-${group}-${worker}`, level: 'worker', d: curve(mid, bottom('workers'), workerX, top('worker')) })
    }
    x += boxWidth + gap
    if (group === ellipsisAfter) {
      ellipsisX = x + (ellipsisWidth - gap) / 2
      x += ellipsisWidth
    }
  })
  return { nodes, links, groups, ellipsisX }
}

const conceptTree = buildTree(['group-0', 'group-1', 'group-2', 'group-n'], 2, 2)
const lessonTree = computed(() => buildTree(Array.from({ length: replicas.value }, (_, group) => `group-${group}`), size.value - 1, null, 'vllm'))

// The concept layer always shows every level. The lesson layer shows the levels up to the current step.
const layers = computed(() => [
  { id: 'concept', on: current.value === 0, tree: conceptTree, reached: levelOrder.length, fresh: 0 },
  { id: 'lesson', on: current.value > 0, tree: lessonTree.value, reached: current.value, fresh: current.value },
].map(layer => ({
  ...layer,
  shown: (level: Level) => rank(level) <= layer.reached,
  isFresh: (level: Level) => rank(level) === layer.fresh,
})))

const segments = (text: string) => text.split('`').map((part, index) => ({ text: part, code: index % 2 === 1 }))
const listNames = (names: string[]) => names.length <= 3 ? names.map(name => `\`${name}\``).join(', ') : `\`${names[0]}\` to \`${names.at(-1)}\``

const steps = computed(() => {
  const leaders = Array.from({ length: replicas.value }, (_, group) => `vllm-${group}`)
  const workers = leaders.flatMap(leader => Array.from({ length: size.value - 1 }, (_, worker) => `${leader}-${worker + 1}`))
  return [
    `Apply \`vllm\` with \`replicas: ${replicas.value}\`, \`size: ${size.value}\`.`,
    'LWS creates the leaders StatefulSet.',
    `The leaders StatefulSet creates leader ${leaders.length === 1 ? 'Pod' : 'Pods'} ${listNames(leaders)}.`,
    `${leaders.length === 1 ? 'Leader' : 'Leaders'} ${listNames(leaders)} ${leaders.length === 1 ? 'owns' : 'each own'} a workers StatefulSet.`,
    `${replicas.value === 1 ? 'The workers StatefulSet creates' : 'The workers StatefulSets create'} worker ${workers.length === 1 ? 'Pod' : 'Pods'} ${listNames(workers)}.`,
  ].map(segments)
})

const explanation = computed(() => current.value === 0
  ? segments('Each group has one leader Pod and its workers.')
  : steps.value[current.value - 1])
</script>

<template>
  <div class="lws-flow">
    <div class="text">
      <p class="kicker">LeaderWorkerSet · lesson 3</p>
      <h1>LeaderWorkerSet Runs Groups of Pods</h1>
      <p class="phase">{{ current === 0 ? 'LWS concept' : `What LWS creates · step ${current} of ${levelOrder.length}` }}</p>
      <div class="explanation" aria-live="polite">
        <p :key="current" class="caption">
          <template v-for="(part, partIndex) in explanation" :key="partIndex"><code v-if="part.code">{{ part.text }}</code><template v-else>{{ part.text }}</template></template>
        </p>
      </div>
      <p class="source">Adapted from the LeaderWorkerSet concept diagram, lws.sigs.k8s.io (CC BY 4.0). Icons: Kubernetes community icons and the LWS logo.</p>
    </div>

    <div class="diagram">
      <div class="controls" :class="{ off: current === 0 }">
        <Segmented v-model="replicas" label="replicas" :options="replicaOptions" :disabled="current === 0" />
        <Segmented v-model="size" label="size" :options="sizeOptions" :disabled="current === 0" />
        <span class="hint">Lesson 3: replicas 1, size 2</span>
      </div>
      <svg :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="current === 0 ? 'A LeaderWorkerSet owns one leaders StatefulSet. It creates one leader Pod for each group, and each leader Pod owns a workers StatefulSet with the worker Pods of its group.' : `The objects that LeaderWorkerSet vllm creates, up to step ${current}`">
        <rect class="frame" x="2" y="2" :width="width - 4" :height="height - 4" rx="36" />
        <g v-for="layer in layers" :key="layer.id" class="layer" :class="{ off: !layer.on }">
          <text class="side-label el" :class="{ hidden: !layer.shown('leaders') }" text-anchor="end">
            <tspan :x="centerX - 40" :y="rows.leaders.y - 4">One leaders</tspan>
            <tspan :x="centerX - 40" :y="rows.leaders.y + 14">StatefulSet</tspan>
          </text>
          <text class="side-label el" :class="{ hidden: !layer.shown('workers') }" text-anchor="end">
            <tspan :x="layer.tree.groups[0].x - 14" :y="rows.workers.y - 14">A workers</tspan>
            <tspan :x="layer.tree.groups[0].x - 14" :y="rows.workers.y + 4">StatefulSet</tspan>
            <tspan :x="layer.tree.groups[0].x - 14" :y="rows.workers.y + 22">per leader</tspan>
          </text>
          <g v-for="group in layer.tree.groups" :key="group.key" class="el" :class="{ hidden: !layer.shown('leader') }">
            <rect class="box" :x="group.x" :y="boxTop" :width="group.width" :height="boxBottom - boxTop" rx="12" />
            <text class="group-label" :x="group.x + group.width / 2" :y="groupLabelY" text-anchor="middle">{{ group.label }}</text>
          </g>
          <g v-if="layer.tree.ellipsisX !== null" class="ellipsis el" :class="{ hidden: !layer.shown('workers') }">
            <circle v-for="dot in 3" :key="dot" :cx="layer.tree.ellipsisX! + (dot - 2) * 12" :cy="rows.workers.y" r="3.5" />
          </g>
          <path v-for="link in layer.tree.links" :key="link.key" class="link el" :class="{ hidden: !layer.shown(link.level) }" :d="link.d" />
          <g v-for="node in layer.tree.nodes" :key="node.key" class="el" :class="{ hidden: !layer.shown(node.level), fresh: layer.isFresh(node.level) }">
            <image
              :href="icons[node.level]"
              :x="node.x - rows[node.level].size / 2" :y="rows[node.level].y - rows[node.level].size / 2"
              :width="rows[node.level].size" :height="rows[node.level].size"
            />
            <GpuIcon
              v-if="layer.id === 'lesson' && (node.level === 'leader' || node.level === 'worker')"
              :x="node.x + rows[node.level].size / 2 - 9" :y="rows[node.level].y - rows[node.level].size / 2 - 6"
              width="20" height="20"
            />
            <text v-if="node.name" class="name" :x="node.x" :y="rows[node.level].y + rows[node.level].size / 2 + 12" text-anchor="middle">{{ node.name }}</text>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.lws-flow {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 24px;
  height: 100%;
}

.text {
  display: flex;
  flex-direction: column;
}

.text h1 {
  margin: 2px 0 10px;
  font-size: 1.8rem;
  line-height: 1.15;
}

.phase {
  margin: 0 0 8px;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}

.explanation {
  flex: 1;
}

.caption {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.5;
  color: var(--ink);
  animation: caption-in 0.6s ease-out;
}

@keyframes caption-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.source {
  margin: auto 0 0;
  font-size: 0.58rem;
  line-height: 1.35;
  color: var(--ink-faint);
}

.diagram {
  position: relative;
}

.diagram > svg {
  display: block;
  width: 100%;
  height: auto;
}

.controls {
  position: absolute;
  top: 12px;
  right: 18px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  transition: opacity 0.6s ease-out;
}

.controls.off {
  visibility: hidden;
  opacity: 0;
}

.hint {
  font-size: 0.62rem;
  color: var(--ink-faint);
}

.frame {
  fill: none;
  stroke: var(--req-1);
  stroke-opacity: 0.55;
  stroke-width: 2;
}

.layer {
  transition: opacity 0.6s ease-out;
}

.layer.off {
  opacity: 0;
}

.el {
  transition: opacity 0.6s ease-out;
}

.el.hidden {
  opacity: 0;
}

.link {
  fill: none;
  stroke: var(--ink-muted);
  stroke-width: 2.5;
}

.box {
  fill: none;
  stroke: var(--ink-faint);
  stroke-width: 2;
  stroke-dasharray: 8 6;
}

.group-label {
  font-family: var(--mono);
  font-size: 14px;
  fill: var(--ink-faint);
}

.side-label {
  font-size: 15px;
  font-weight: 700;
  fill: var(--live);
}

.ellipsis circle {
  fill: var(--ink-faint);
}

.name {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  fill: var(--ink);
}

.fresh image {
  filter: drop-shadow(0 0 7px var(--accent));
}

@media (prefers-reduced-motion: reduce) {
  .layer, .el, .controls { transition: none; }
  .caption { animation: none; }
}
</style>
