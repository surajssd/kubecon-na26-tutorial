import { describe, expect, test } from 'bun:test'
import { phaseConfig, phasePresets } from './scenarios'
import { createState, isDone, step } from './serving'

describe('Simulation B presets', () => {
  test('a preset with words has one word for every prompt and output token', () => {
    for (const preset of phasePresets.filter(item => item.words)) {
      expect(preset.requests).toHaveLength(1)
      expect(preset.words!.prompt).toHaveLength(preset.requests[0].promptTokens)
      expect(preset.words!.output).toHaveLength(preset.requests[0].outputTokens)
    }
  })

  test.each([16, 4])('the chat response ends with a separate stop token at budget %i', (budget) => {
    const preset = phasePresets.find(item => item.id === 'one')!
    let state = createState(phaseConfig(budget), preset.requests)
    while (state.requests.r1.emitted < 6)
      state = step(state)

    expect(preset.words!.output[state.requests.r1.emitted - 1]).toBe('.')
    expect(isDone(state)).toBe(false)
    expect(state.requests.r1.completedAt).toBeNull()

    const completed = step(state)
    expect(completed.requests.r1.emitted).toBe(7)
    expect(preset.words!.output[completed.requests.r1.emitted - 1]).toBe('<|im_end|>')
    expect(completed.steps.at(-1)!.decoded).toEqual(['r1'])
    expect(completed.time - state.time).toBeCloseTo(1.1)
    expect(isDone(completed)).toBe(true)
  })
})
