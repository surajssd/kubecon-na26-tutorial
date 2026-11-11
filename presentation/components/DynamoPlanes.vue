<script setup lang="ts">
import { computed } from 'vue'
import podIcon from '../assets/icons/pod.svg'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

type Plane = 'client' | 'request' | 'control' | 'storage'

// Step 0 is the whole diagram. Steps 1 to 3 focus one plane each, control first because the operator creates everything else. Step 4 highlights what lesson 4 runs.
const focusOrder: Plane[] = ['control', 'request', 'storage']
const lessonStep = focusOrder.length + 1
const current = computed(() => Math.min(Math.max(props.step, 0), lessonStep))
const focus = computed(() => focusOrder[current.value - 1])
const lessonMode = computed(() => current.value === lessonStep)

const captions: { topic?: string, text: string }[] = [
  { text: 'NVIDIA Dynamo is a distributed inference framework. It runs engines such as vLLM as workers and splits serving into three planes.' },
  { topic: 'Control plane:', text: 'the Dynamo Operator reconciles Kubernetes resources from Dynamo custom resources, such as a DynamoGraphDeployment. The Planner computes scaling targets, and Grove places multinode groups.' },
  { topic: 'Request plane:', text: 'the frontend accepts and normalizes requests. The router picks a worker for each request: in turn by default, or by load and KV overlap in KV mode. Prefill workers compute the prompt\'s KV cache, and decode workers generate output tokens.' },
  { topic: 'Storage and events plane:', text: 'KV events publish cache changes. Offloading moves KV blocks between GPU memory, host memory, and storage. The NVIDIA Inference Xfer Library (NIXL) transfers KV data between workers.' },
  { text: 'Lesson 4 runs the highlighted parts: the operator and DynamoGraphDeployment vllm, one frontend Pod whose single container runs the frontend and a round-robin router, one prefill Pod, one decode Pod, and NIXL over TCP. It runs no Planner, Grove, or KVBM.' },
]

interface Region { id: Plane, title?: string, x: number, y: number, w: number, h: number }
const regions: Region[] = [
  { id: 'client', x: 0, y: 20, w: 90, h: 150 },
  { id: 'request', title: 'REQUEST PLANE', x: 150, y: 0, w: 400, h: 210 },
  { id: 'control', title: 'CONTROL PLANE', x: 640, y: 0, w: 360, h: 400 },
  { id: 'storage', title: 'STORAGE & EVENTS PLANE', x: 100, y: 262, w: 470, h: 138 },
]

// A Pod outline groups the components that run in one Pod.
const pods = [
  { id: 'frontend-pod', x: 160, y: 40, w: 380, h: 62, plane: 'request' as Plane },
]

interface Box { id: string, lines: string[], x: number, y: number, w: number, h: number, plane: Plane, lesson?: string, align?: 'top', icon?: boolean, gpu?: boolean }
const boxes: Box[] = [
  { id: 'frontend', lines: ['Frontend'], x: 196, y: 52, w: 140, h: 38, plane: 'request', lesson: '' },
  { id: 'router', lines: ['Router'], x: 390, y: 52, w: 140, h: 38, plane: 'request', lesson: '' },
  { id: 'prefill', lines: ['Prefill', 'workers'], x: 180, y: 130, w: 140, h: 62, plane: 'request', lesson: '1 Pod · 1 GPU', icon: true, gpu: true },
  { id: 'decode', lines: ['Decode', 'workers'], x: 400, y: 130, w: 140, h: 62, plane: 'request', lesson: '1 Pod · 1 GPU', icon: true, gpu: true },
  { id: 'planner', lines: ['Planner'], x: 656, y: 44, w: 152, h: 100, plane: 'control', align: 'top' },
  { id: 'aiconfigurator', lines: ['AIConfigurator'], x: 668, y: 82, w: 128, h: 46, plane: 'control' },
  { id: 'operator', lines: ['Dynamo Operator'], x: 836, y: 44, w: 150, h: 54, plane: 'control', lesson: 'Dynamo 1.6.0' },
  { id: 'graph', lines: ['Dynamo Graph'], x: 826, y: 160, w: 130, h: 46, plane: 'control', lesson: 'DGD vllm' },
  { id: 'grove', lines: ['Grove'], x: 902, y: 236, w: 84, h: 38, plane: 'control' },
  { id: 'runtime', lines: ['Runtime resources'], x: 826, y: 318, w: 160, h: 48, plane: 'control', lesson: 'Deployments, Services' },
  { id: 'kvbm', lines: ['KVBM'], x: 118, y: 298, w: 88, h: 34, plane: 'storage' },
  { id: 'nixl', lines: ['NIXL'], x: 330, y: 298, w: 90, h: 34, plane: 'storage', lesson: 'UCX over TCP' },
  { id: 'disk', lines: ['Local SSD / NFS /', 'remote storage'], x: 300, y: 360, w: 150, h: 36, plane: 'storage' },
]

interface Label { id: string, lines: string[], x: number, y: number, anchor?: 'start' | 'middle' | 'end', plane: Plane, lesson?: boolean }
const labels: Label[] = [
  { id: 'client', lines: ['CLIENT'], x: 45, y: 100, anchor: 'middle', plane: 'client', lesson: true },
  { id: 'kv-state', lines: ['KV state'], x: 360, y: 154, anchor: 'middle', plane: 'request', lesson: true },
  { id: 'checkpoints', lines: ['Checkpoints'], x: 360, y: 184, anchor: 'middle', plane: 'request' },
  { id: 'reconcile', lines: ['(Reconcile)'], x: 918, y: 136, plane: 'control', lesson: true },
  { id: 'offload', lines: ['KV block', 'offload'], x: 354, y: 344, anchor: 'end', plane: 'storage' },
  { id: 'onboard', lines: ['KV block onboard,', 'model weights'], x: 396, y: 344, plane: 'storage' },
]

// A link belongs to every plane it touches, so it stays lit when either end is in focus.
interface Link { id: string, d: string, planes: Plane[], dashed?: boolean, lesson?: boolean, text?: { lines: string[], x: number, y: number, anchor?: 'start' | 'middle' | 'end' } }
const links: Link[] = [
  { id: 'request', d: 'M 90 40 H 150', planes: ['client', 'request'], dashed: true, lesson: true, text: { lines: ['request'], x: 98, y: 33 } },
  { id: 'response', d: 'M 150 122 H 90', planes: ['client', 'request'], dashed: true, lesson: true, text: { lines: ['response'], x: 98, y: 115 } },
  { id: 'frontend-router', d: 'M 336 71 H 390', planes: ['request'], lesson: true },
  { id: 'router-prefill', d: 'M 460 90 V 116 H 250 V 130', planes: ['request'], lesson: true },
  { id: 'router-decode', d: 'M 460 116 H 470 V 130', planes: ['request'], lesson: true },
  { id: 'kv-state', d: 'M 320 166 H 400', planes: ['request'], lesson: true },
  { id: 'observability', d: 'M 550 92 H 640', planes: ['request', 'control'], dashed: true, text: { lines: ['observability'], x: 558, y: 85 } },
  { id: 'capacity', d: 'M 640 162 H 550', planes: ['request', 'control'], dashed: true, text: { lines: ['capacity, placement'], x: 558, y: 155 } },
  { id: 'fault', d: '', planes: ['request', 'control'], text: { lines: ['fault tolerance'], x: 558, y: 180 } },
  { id: 'lifecycle', d: 'M 190 210 V 262', planes: ['request', 'storage'], dashed: true, text: { lines: ['lifecycle, handoff,', 'blocks (KVBM)'], x: 197, y: 230 } },
  { id: 'weights', d: 'M 330 262 V 210', planes: ['request', 'storage'], dashed: true, text: { lines: ['model', 'weights'], x: 337, y: 230 } },
  { id: 'kv-events', d: 'M 480 262 V 210', planes: ['request', 'storage'], dashed: true, text: { lines: ['cache visibility,', 'KV events to router'], x: 487, y: 230 } },
  { id: 'planner-operator', d: 'M 808 71 H 836', planes: ['control'] },
  { id: 'operator-graph', d: 'M 911 98 V 160', planes: ['control'], lesson: true },
  { id: 'graph-grove', d: 'M 944 206 V 236', planes: ['control'] },
  { id: 'graph-runtime', d: 'M 852 206 V 318', planes: ['control'], lesson: true },
  { id: 'grove-runtime', d: 'M 944 274 V 318', planes: ['control'] },
  { id: 'kvbm-nixl', d: 'M 206 315 H 330', planes: ['storage'] },
  { id: 'offload', d: 'M 362 332 V 360', planes: ['storage'] },
  { id: 'onboard', d: 'M 388 360 V 332', planes: ['storage'] },
]

// The client is lit with the request plane, because it only talks to that plane.
const dimmed = (plane: Plane | Plane[], lesson: boolean | undefined) => {
  if (lessonMode.value) return !lesson
  if (!focus.value) return false
  const planes = (Array.isArray(plane) ? plane : [plane]).map(item => item === 'client' ? 'request' : item)
  return !planes.includes(focus.value)
}

const iconSize = 26
const regionViews = computed(() => regions.map(region => ({ ...region, dim: !lessonMode.value && dimmed(region.id, true) })))
const podViews = computed(() => pods.map(pod => ({ ...pod, dim: dimmed(pod.plane, true), lit: lessonMode.value })))
const boxViews = computed(() => boxes.map((box) => {
  const tagged = lessonMode.value && Boolean(box.lesson)
  const textX = box.icon ? box.x + iconSize + (box.w - iconSize) / 2 : box.x + box.w / 2
  return {
    ...box,
    dim: dimmed(box.plane, box.lesson !== undefined),
    lit: lessonMode.value && box.lesson !== undefined,
    tagged,
    textX: box.align === 'top' ? box.x + 12 : textX,
    textY: box.align === 'top' ? box.y + 20 : box.y + box.h / 2 - ((box.lines.length - 1) * 15) / 2 + 5 - (tagged ? 7 : 0),
  }
}))
const labelViews = computed(() => labels.map(label => ({ ...label, dim: dimmed(label.plane, label.lesson) })))
const linkViews = computed(() => links.map(link => ({ ...link, dim: dimmed(link.planes, link.lesson) })))
const caption = computed(() => captions[current.value])
</script>

<template>
  <div class="dynamo-planes">
    <p class="kicker">NVIDIA Dynamo · lesson 4</p>
    <h1>Dynamo Splits Serving Into Three Planes</h1>
    <svg viewBox="0 0 1000 400" role="img" aria-label="Dynamo architecture: a client talks to the request plane, where one frontend Pod runs the frontend and the router, and prefill and decode workers run in their own Pods. The control plane holds the Planner, the Dynamo Operator, the Dynamo Graph, Grove, and the runtime resources. The storage and events plane holds KVBM, NIXL, and storage.">
      <defs>
        <marker id="dynamo-planes-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" class="arrow-head" />
        </marker>
      </defs>

      <g v-for="region in regionViews" :key="region.id" class="region el" :class="[region.id, { dim: region.dim }]">
        <rect class="plane" :x="region.x" :y="region.y" :width="region.w" :height="region.h" />
        <template v-if="region.title">
          <rect class="plane-head" :x="region.x" :y="region.y" :width="region.w" height="30" />
          <text class="plane-title" :x="region.x + 12" :y="region.y + 21">{{ region.title }}</text>
        </template>
      </g>

      <g v-for="pod in podViews" :key="pod.id" class="el" :class="{ dim: pod.dim, lit: pod.lit }">
        <rect class="pod" :x="pod.x" :y="pod.y" :width="pod.w" :height="pod.h" rx="10" />
        <image :href="podIcon" :x="pod.x + 7" :y="pod.y + (pod.h - 22) / 2" width="22" height="22" />
      </g>

      <g v-for="link in linkViews" :key="link.id" class="el" :class="{ dim: link.dim }">
        <path v-if="link.d" class="link" :class="{ dashed: link.dashed }" :d="link.d" marker-end="url(#dynamo-planes-arrow)" />
        <text v-if="link.text" class="link-text" :text-anchor="link.text.anchor ?? 'start'">
          <tspan v-for="(line, index) in link.text.lines" :key="index" :x="link.text.x" :y="link.text.y + index * 14">{{ line }}</tspan>
        </text>
      </g>

      <g v-for="box in boxViews" :key="box.id" class="el" :class="{ dim: box.dim, lit: box.lit }">
        <rect class="box" :x="box.x" :y="box.y" :width="box.w" :height="box.h" />
        <image v-if="box.icon" :href="podIcon" :x="box.x + 8" :y="box.y + (box.gpu ? 5 : (box.h - iconSize) / 2)" :width="iconSize" :height="iconSize" />
        <GpuIcon v-if="box.gpu" :x="box.x + 10" :y="box.y + box.h - 28" width="22" height="22" />
        <text class="box-text" :text-anchor="box.align === 'top' ? 'start' : 'middle'">
          <tspan v-for="(line, index) in box.lines" :key="index" :x="box.textX" :y="box.textY + index * 15">{{ line }}</tspan>
        </text>
        <text v-if="box.lesson" class="lesson-tag" :class="{ shown: box.tagged }" :x="box.textX" :y="box.y + box.h - 8" text-anchor="middle">{{ box.lesson }}</text>
      </g>

      <g v-for="label in labelViews" :key="label.id" class="el" :class="{ dim: label.dim }">
        <text :class="label.id === 'client' ? 'client-text' : 'link-text'" :text-anchor="label.anchor ?? 'start'">
          <tspan v-for="(line, index) in label.lines" :key="index" :x="label.x" :y="label.y + index * 14">{{ line }}</tspan>
        </text>
      </g>
    </svg>
    <p class="caption">
      <span class="step">{{ current === 0 ? 'Architecture' : current === lessonStep ? 'Lesson 4' : `Plane ${current} of ${focusOrder.length}` }}</span>
      <span><strong v-if="caption.topic">{{ `${caption.topic} ` }}</strong>{{ caption.text }}</span>
    </p>
    <p class="source">Adapted from the Dynamo architecture diagram in the Dynamo v1.6.0 documentation, docs.nvidia.com/dynamo (Apache-2.0). Pod icon: Kubernetes icon set.</p>
  </div>
</template>

<style scoped>
.dynamo-planes {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.dynamo-planes h1 {
  margin: 2px 0 10px;
}

.dynamo-planes > svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

.el {
  transition: opacity 0.35s;
}

.el.dim {
  opacity: 0.2;
}

.plane {
  fill: color-mix(in srgb, var(--req-5) 10%, transparent);
  stroke: color-mix(in srgb, var(--req-5) 70%, transparent);
  stroke-width: 1.5;
}

.client .plane {
  fill: color-mix(in srgb, var(--req-5) 16%, transparent);
}

.plane-head {
  fill: color-mix(in srgb, var(--req-5) 28%, transparent);
  stroke: color-mix(in srgb, var(--req-5) 70%, transparent);
  stroke-width: 1.5;
}

.plane-title {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.02em;
  fill: var(--ink);
}

.pod {
  fill: rgb(var(--tint) / 0.04);
  stroke: var(--req-1);
  stroke-width: 1.5;
  stroke-dasharray: 6 4;
  transition: stroke 0.3s;
}

.lit .pod {
  stroke: var(--accent);
  stroke-width: 2.5;
}

.box {
  fill: var(--surface-raised);
  stroke: color-mix(in srgb, var(--req-5) 80%, transparent);
  stroke-width: 1.5;
  transition: stroke 0.3s, stroke-width 0.3s;
}

.lit .box {
  stroke: var(--accent);
  stroke-width: 2.5;
}

.box-text {
  font-size: 14px;
  font-weight: 600;
  fill: var(--ink);
}

.client-text {
  font-size: 15px;
  font-weight: 700;
  fill: var(--ink);
}

.lesson-tag {
  font-size: 11px;
  font-weight: 700;
  fill: var(--accent);
  opacity: 0;
  transition: opacity 0.3s;
}

.lesson-tag.shown {
  opacity: 1;
}

.link {
  fill: none;
  stroke: var(--req-5);
  stroke-width: 1.6;
}

.link.dashed {
  stroke-dasharray: 6 5;
}

.arrow-head {
  fill: var(--req-5);
}

.link-text {
  font-size: 12px;
  fill: var(--ink-muted);
}

.caption {
  display: flex;
  align-items: baseline;
  gap: 12px;
  /* Room for two lines with border-box sizing, so the box keeps one size across steps. */
  min-height: 4.1em;
  margin: auto 0 0;
  padding: 7px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  font-size: 0.8rem;
  line-height: 1.4;
  color: var(--ink);
}

.caption .step {
  flex: none;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}

.source {
  margin: 6px 0 -14px;
  font-size: 0.5rem;
  line-height: 1.2;
  color: var(--ink-faint);
}

@media (prefers-reduced-motion: reduce) {
  .el, .lesson-tag { transition: none; }
}
</style>
