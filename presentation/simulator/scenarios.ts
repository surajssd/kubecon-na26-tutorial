import type { Scenario } from './batching'
import type { RequestSpec, ServingConfig, Timing } from './serving'

export interface BatchingPreset {
  id: string
  label: string
  scenario: Scenario
}

function decodeOnly(capacity: number, lengths: number[]): Scenario {
  return { capacity, requests: lengths.map((outputTokens, index) => ({ id: `r${index + 1}`, outputTokens })) }
}

export const principal = decodeOnly(2, [2, 5, 2])

export const batchingPresets: BatchingPreset[] = [
  { id: 'uneven', label: 'Uneven lengths', scenario: principal },
  { id: 'long', label: 'One long request', scenario: decodeOnly(2, [8, 1, 1, 1, 1]) },
  { id: 'equal', label: 'Equal lengths', scenario: decodeOnly(2, [3, 3, 3, 3]) },
]

// Normalized time units. These coefficients illustrate the shape of the
// tradeoffs; they are not measured from a GPU.
export const teachingTiming: Timing = { fixed: 1, prefillPerToken: 0.1, decodePerSequence: 0.1, contextPerToken: 0 }

export interface PhasePreset {
  id: string
  requests: RequestSpec[]
  budgets: { label: string, tokenBudget: number }[]
  words?: { prompt: string[], output: string[] }
}

export const phasePresets: PhasePreset[] = [
  {
    id: 'one',
    requests: [{ id: 'r1', arrival: 0, promptTokens: 12, outputTokens: 7 }],
    budgets: [
      { label: 'Whole prompt', tokenBudget: 16 },
      { label: 'Chunks of 4', tokenBudget: 4 },
    ],
    // Illustrative tokens in a Qwen-style chat format. A real tokenizer and
    // chat template produce a different count.
    words: {
      prompt: ['<|im_start|>', 'user', 'Explain', ' Kubernetes', ' in', ' one', ' sentence', '.', '<|im_end|>', '<|im_start|>', 'assistant', '\n'],
      output: ['Kubernetes', ' runs', ' and', ' scales', ' containers', '.', '<|im_end|>'],
    },
  },
  {
    id: 'busy',
    requests: [
      { id: 'r1', arrival: 0, promptTokens: 6, outputTokens: 10 },
      { id: 'r2', arrival: 3, promptTokens: 32, outputTokens: 3 },
      { id: 'r3', arrival: 8, promptTokens: 32, outputTokens: 3 },
    ],
    budgets: [
      { label: 'Whole prompt', tokenBudget: 40 },
      { label: 'Chunks of 8', tokenBudget: 8 },
    ],
  },
]

export function phaseConfig(tokenBudget: number): ServingConfig {
  return { policy: 'continuous', maxSequences: 4, tokenBudget, timing: teachingTiming }
}

// One illustrative full-attention layout, used for the KV math slide.
export const exampleLayout = { layers: 32, kvHeads: 8, headDimension: 128, bytesPerElement: 2 }

export const kvRequests: RequestSpec[] = [
  { id: 'r1', arrival: 0, promptTokens: 10, outputTokens: 6 },
  { id: 'r2', arrival: 0, promptTokens: 12, outputTokens: 8 },
  { id: 'r3', arrival: 0, promptTokens: 6, outputTokens: 6 },
  { id: 'r4', arrival: 0, promptTokens: 8, outputTokens: 4 },
]

export const kvPoolTokens = 48

export function kvConfig(blockSize: number): ServingConfig {
  return {
    policy: 'continuous',
    maxSequences: 4,
    tokenBudget: 16,
    timing: { fixed: 1, prefillPerToken: 0, decodePerSequence: 0, contextPerToken: 0 },
    kv: { blockSize, poolBlocks: kvPoolTokens / blockSize },
  }
}

export interface LoadLevel {
  id: string
  label: string
  interval: number
}

export const loadLevels: LoadLevel[] = [
  { id: 'light', label: 'Light', interval: 8 },
  { id: 'medium', label: 'Medium', interval: 3 },
  { id: 'heavy', label: 'Heavy', interval: 1 },
]

export const sweepSequences = [1, 2, 4, 8, 16]

export const sweepTiming: Timing = { fixed: 1, prefillPerToken: 0.04, decodePerSequence: 0.12, contextPerToken: 0.004 }

const sweepPrompts = [24, 12, 32, 16]
const sweepOutputs = [6, 18, 10, 14]

export function sweepWorkload(interval: number): RequestSpec[] {
  return Array.from({ length: 16 }, (_, index) => ({
    id: `r${index + 1}`,
    arrival: index * interval,
    promptTokens: sweepPrompts[index % sweepPrompts.length],
    outputTokens: sweepOutputs[index % sweepOutputs.length],
  }))
}
