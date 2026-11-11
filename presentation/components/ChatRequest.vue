<script setup lang="ts">
import { computed } from 'vue'

interface Message {
  tag: string
  role: 'user' | 'assistant'
  content: string
  units: number
}

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

const conversation: Message[] = [
  { tag: 'Q1', role: 'user', content: 'Explain Kubernetes in one sentence.', units: 2 },
  { tag: 'A1', role: 'assistant', content: 'Kubernetes runs containers…', units: 3 },
  { tag: 'Q2', role: 'user', content: 'How does it scale?', units: 2 },
  { tag: 'A2', role: 'assistant', content: 'It adds Pods…', units: 3 },
  { tag: 'Q3', role: 'user', content: 'And on GPUs?', units: 2 },
  { tag: 'A3', role: 'assistant', content: 'It schedules Pods that request GPUs…', units: 3 },
]
const windowUnits = 20

const currentStep = computed(() => Math.min(Math.max(props.step, 0), conversation.length - 1))
const current = computed(() => Math.floor(currentStep.value / 2) + 1)
const showAnswer = computed(() => currentStep.value % 2 === 1)
const messages = computed(() => conversation.slice(0, current.value * 2 - 1))
const answer = computed(() => conversation[current.value * 2 - 1])
const promptUnits = computed(() => messages.value.reduce((sum, message) => sum + message.units, 0))
const outputUnits = computed(() => showAnswer.value ? answer.value.units : 0)
const unusedUnits = computed(() => windowUnits - promptUnits.value - outputUnits.value)
</script>

<template>
  <div class="chat-request">
    <div class="top">
      <div class="exchange">
        <div class="json-label">Request · Q{{ current }}</div>
        <div class="json" :aria-label="`Request body for turn ${current}`">
          <div>{</div>
          <div class="depth-1"><span class="key">"model"</span>: <span class="str">"Qwen/Qwen3.5-0.8B"</span>,</div>
          <div class="depth-1"><span class="key">"messages"</span>: [</div>
          <div
            v-for="(message, index) in messages"
            :key="message.tag"
            class="depth-2 message"
            :class="index === messages.length - 1 ? 'fresh' : 'history'"
          >
            {<span class="key">"role"</span>: <span class="str">"{{ message.role }}"</span>, <span class="key">"content"</span>: <span class="str">"{{ message.content }}"</span>}{{ index < messages.length - 1 ? ',' : '' }}
          </div>
          <div class="depth-1">],</div>
          <div class="depth-1"><span class="key">"max_tokens"</span>: <span class="num">128</span>,</div>
          <div class="depth-1"><span class="key">"temperature"</span>: <span class="num">0</span></div>
          <div>}</div>
        </div>
        <div class="response" :class="{ visible: showAnswer }" :aria-hidden="!showAnswer">
          <div class="json-label">Response message · {{ answer.tag }}</div>
          <div class="json" :aria-label="`Response message for turn ${current}`">
            {<span class="key">"role"</span>: <span class="str">"{{ answer.role }}"</span>, <span class="key">"content"</span>: <span class="str">"{{ answer.content }}"</span>}
          </div>
        </div>
      </div>
      <div class="notes">
        <slot />
      </div>
    </div>

    <figure class="context">
      <figcaption>
        Turn {{ current }}: {{ showAnswer ? 'request + response' : 'request' }} in a 2,048-token context window
        <span class="badge simulated">Illustrative sizes</span>
      </figcaption>
      <div class="window">
        <div class="prompt" :style="{ flexGrow: promptUnits }">
          <div
            v-for="(message, index) in messages"
            :key="message.tag"
            class="part"
            :class="[message.role, index === messages.length - 1 ? 'fresh' : 'history']"
            :style="{ flexGrow: message.units }"
          >
            <strong>{{ message.tag }}</strong>
          </div>
        </div>
        <div v-if="showAnswer" :key="answer.tag" class="part answer fresh" :style="{ flexGrow: outputUnits }">
          <strong>{{ answer.tag }}</strong>
        </div>
        <div class="part unused" :style="{ flexGrow: unusedUnits }">
          <strong>Unused</strong>
        </div>
      </div>
      <div class="brackets">
        <span class="bracket" :style="{ flexGrow: promptUnits }">prompt_tokens</span>
        <span v-if="showAnswer" class="bracket output-bracket" :style="{ flexGrow: outputUnits }">completion_tokens</span>
        <span :style="{ flexGrow: unusedUnits }" />
      </div>
    </figure>
  </div>
</template>

<style scoped>
.top {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 28px;
  align-items: start;
  margin-bottom: 14px;
}

/* Reserve the turn 3 height (12 lines) so the context window bar does not move between turns. */
.exchange > .json {
  min-height: calc(12 * 1.5em + 22px);
}

.json-label {
  margin-bottom: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--ink-muted);
}

.json {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  font-family: var(--mono);
  font-size: 0.66rem;
  line-height: 1.5;
  white-space: nowrap;
  color: var(--ink-muted);
  background: var(--slidev-code-background);
}

.response {
  margin-top: 8px;
  visibility: hidden;
}

.response.visible {
  visibility: visible;
}

.response .json {
  border-color: var(--req-2);
}

.response.visible .json {
  animation: pop 0.35s ease-out;
}

.depth-1 {
  padding-left: 2ch;
}

.depth-2 {
  padding-left: 4ch;
}

.key {
  color: var(--req-5);
}

.str {
  color: var(--req-4);
}

.num {
  color: var(--req-3);
}

.message {
  border-radius: 3px;
}

.message.history {
  opacity: 0.5;
}

.message.fresh {
  background: color-mix(in srgb, var(--req-1) 14%, transparent);
  animation: pop 0.35s ease-out;
}

.notes :deep(ul) {
  margin: 0;
}

.notes :deep(li) {
  font-size: 0.9rem;
}

.context {
  margin: 0;
}

figcaption {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--ink);
}

.window,
.prompt,
.brackets {
  display: flex;
  gap: 3px;
}

.window > *,
.prompt > *,
.brackets > * {
  flex-basis: 0;
  min-width: 0;
  transition: flex-grow 0.5s ease;
}

.part {
  display: flex;
  align-items: center;
  min-height: 52px;
  padding: 6px 10px;
  border-radius: 6px;
  color: var(--ink-inverse);
  overflow: hidden;
}

.part strong {
  font-size: 0.82rem;
  white-space: nowrap;
  color: inherit;
}

.user,
.assistant {
  background: var(--req-1);
}

.assistant {
  background: var(--req-1-soft);
}

.part.history {
  opacity: 0.55;
}

.part.fresh {
  animation: pop 0.35s ease-out;
}

.answer {
  background: var(--req-2);
}

.unused {
  color: var(--ink-faint);
  border: 1px dashed var(--line);
}

.brackets {
  margin-top: 6px;
  font-size: 0.68rem;
  font-family: var(--mono);
  color: var(--ink-muted);
}

.bracket {
  padding-top: 4px;
  text-align: center;
  white-space: nowrap;
  border-top: 2px solid var(--req-1);
}

.output-bracket {
  border-top-color: var(--req-2);
}

@media (prefers-reduced-motion: reduce) {
  .message.fresh,
  .part.fresh,
  .response.visible .json {
    animation: none;
  }
}
</style>
