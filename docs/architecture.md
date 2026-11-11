# Presentation architecture

This document defines the design contract for the local Slidev deck in `presentation/` and its deterministic inference simulator. Simulations A-D are implemented as teaching models. Planner tracks implementation status and task dependencies.

## Delivery boundaries

| Component | Responsibility | Required connection |
| --- | --- | --- |
| `presentation/` | Slidev chapters, Vue controls, and simulations A-D | Local HTTP server only, after dependency installation and asset preparation |
| [Tutorial lessons](../tutorial/README.md) | Deploy real model servers and inspect their behavior | Workshop workspace, Kubernetes API, model Services, and shared model storage |
| [Streaming demo](../tutorial/server/demo.py) | Forward real streamed requests and display browser timing | Reachable OpenAI-compatible model endpoint |
| [Traffic client](../tutorial/server/traffic.py) | Generate bounded load and report completion-token throughput | Reachable model endpoint |
| Workshop Grafana | Display collected GPU, engine, and frontend metrics | Authenticated workshop gateway and monitoring stack |

The deck must work without a cluster, GPU, external API, or internet connection. Live labs and dashboards require the workshop network. Captures of live observations belong to the prepared backup material.

## State ownership

Use plain TypeScript for the engine. A transition accepts state and a command, validates inputs, then returns the next state and explanatory events without mutating its inputs. Reject invalid commands before changing state. Keep queue order, request progress, simulated time, memory accounting, and metric timestamps in engine values.

Use Vue for controls, wall-clock playback timers, focus, and SVG/CSS rendering. Vue issues engine commands and renders their results. Animation completion must not emit a token, admit a request, or release memory.

Use Slidev for chapter order, explanatory clicks, notes, and routing. Each simulation slide owns an engine instance initialized from a named scenario. Do not add a global mutable store.

Keep transitions independent of the network, `Date.now()`, animation frames, and unseeded randomness. Resolve arrival ties by stable insertion order. Manual stepping, playback, and replay use the same commands. Retain bounded command traces for repeatable replay. Playback speed changes only the delay between commands.

## Simulation contracts

### A: Continuous batching

Start with decode only. Prefill has finished and memory is sufficient. Display iterations, output tokens, request state, and sequence-slot occupancy. This profile supplies no time to first token (TTFT), measured GPU utilization, or hardware throughput.

At each iteration boundary:

1. Enqueue due arrivals in arrival order.
2. Admit requests according to the selected policy.
3. Emit one output token for each active unfinished request.
4. Record completions at the end of the iteration.
5. Release finished capacity and advance the iteration.

Replacements produce work at the next boundary. Static batching starts the oldest nonempty cohort whenever no cohort remains active. Completed members retain their cohort slots until the whole cohort finishes. Continuous batching refills available slots at each boundary.

The acceptance fixture has capacity two and output lengths `[2, 5, 2]`, all arriving initially. Static batching takes seven iterations. Continuous batching takes five. Both emit nine tokens. Use hand-written expected traces to verify these results.

Capacity and policy changes reset the scenario explicitly. Output-length changes affect only newly added requests. The sequence limit, token budget per iteration, and memory capacity remain separate quantities.

### B: Prefill and decode

Extend the lifecycle with prompt progress and a token budget. Admit requests in first-in, first-out (FIFO) order up to the sequence limit. Process one input token for each selected decode request, then spend the remaining budget on the oldest active prefill request. Require the token budget to be at least the sequence limit. Use finite scripted workloads and output lengths. Label this scheduler as a teaching model.

The final prefill operation emits output token one. Later decode operations consume the preceding output token and emit the next token.

Timed arrivals use absolute simulated timestamps. Mid-iteration arrivals retain their timestamps and wait until the next boundary. Enqueue all due arrivals before admission. When only future arrivals remain, advance directly to the next arrival without emitting tokens. Manual additions arrive at the current boundary.

Use normalized simulated time units. Define iteration duration as:

```text
fixed cost
+ prefill coefficient * prompt inputs processed
+ decode coefficient * decode sequences processed
+ context coefficient * sum of decode context lengths before the step
```

The fixed cost is positive. Other coefficients are nonnegative and visible in scenario documentation. Exclude network transport, tokenization, buffering, kernels, and hardware contention. The simulator does not model disaggregated key-value (KV) cache transfer.

Derive metrics from the same trace:

| Metric | Definition |
| --- | --- |
| Queue wait | Admission time minus arrival time |
| TTFT | First output time minus arrival time |
| End-to-end latency | Completion time minus arrival time |
| Time per output token (TPOT) | Last output time minus first output time, divided by output count minus one |

Show TPOT as `N/A` when fewer than two output tokens exist.

### C: KV cache and memory

Model one full-attention decoder-only cache layout. KV bytes per cached input token equal `2 * layerCount * kvHeadCount * headDimension * bytesPerElement`. Use KV heads, not query heads. Display weights, reserved runtime memory, and the KV pool separately.

Track processed inputs directly. After prefill, for prompt length `P` and `g` emitted outputs, cached inputs before cleanup are `P + g - 1`. The newest output has not been consumed. For target output length `O`, peak cached inputs are `P + O - 1`.

For block size `B`, allocate `ceil(processedInputs / B)` blocks. Internal waste equals allocated token capacity minus processed inputs. Show logical-to-physical mapping and deterministic block reuse.

Reserve `ceil((P + O - 1) / B)` blocks at admission, then allocate blocks as inputs are processed. Enforce `allocated <= reserved <= pool capacity` per request and in aggregate. Other requests cannot use unused reservations. Release allocations and reservations on completion.

Reject individually impossible requests before enqueue. Other requests wait FIFO until reservations fit. This conservative policy needs known output lengths and can admit fewer requests than a production scheduler. Memory, block-size, and model-parameter changes reset the scenario.

Exclude tensor sharding, quantization metadata, allocator overhead, prefix sharing, sliding-window attention, preemption, swap, and other architectures. This formula does not reproduce the hybrid Gemma cache in lesson 04.

### D: Latency and throughput

Use the shared engine, timed profile, and trace. Separate offered arrival rate, maximum sequences, and observed active concurrency. Comparisons use identical arrival timestamps and request lengths.

For a completed finite run, measure from first arrival to last completion, including internal idle intervals. Output throughput is emitted output tokens divided by that interval. Request throughput is completed requests divided by that interval.

For incomplete runs, show pending counts and label metrics as provisional or `N/A`. Name the observation window. Show sample counts with aggregate statistics. Synthetic curves do not predict GPU performance, and higher concurrency does not guarantee higher throughput.

## Playback and offline operation

Use one authoritative projected play window on one laptop. Both presenters operate that window in turn. A companion notes window must not operate another independent simulation. Verify custom component behavior in the pinned Slidev version before relying on presenter navigation synchronization.

Use public Slidev lifecycle and render-context APIs. Inactive slides, overview tiles, and previews must not run playback timers. Leaving a slide or hiding the tab pauses playback. Returning leaves it paused. Reset restores the selected scenario. Explanatory clicks do not advance engine time unless an authored sequence explicitly maps them.

Disable remote font providers and bundle required media locally. Serve the production build through a documented local HTTP command. Install dependencies and browser binaries before travel. Verify offline loading in a fresh browser context that permits only the local server origin and rejects attempted external requests.

Prepare deterministic replay, a PDF with explicit scenario states, and recordings of complex interactions. Replay depends on the application, so it cannot replace the PDF or recordings after an application failure. Both presenters must test their local backup copies.

## Ownership and verification

| Owner | Responsibility |
| --- | --- |
| Presenter A | Chapter sequence, explanatory copy, visual readability, and handoffs |
| Presenter B | Engine semantics, memory assumptions, metric definitions, and live-value disclosures |
| Integration owner | Engine interfaces, `package.json`, `bun.lock`, `slides.md`, and CI |

These are roles, not confirmed assignments of names. During serial implementation, the active contributor owns integration. Before parallel implementation, assign one named integration owner and agree on shared interfaces. Both presenters review the agenda and control-window arrangement.

Use meaningful tests with Bun's test runner (`bun test`) for pure transitions, exact traces, and invariants. Use Playwright with real components and the real engine for controls, lifecycle, keyboard focus, and offline operation. Keep the existing Python integration tests independent. Add checks with implemented behavior rather than empty suites.
