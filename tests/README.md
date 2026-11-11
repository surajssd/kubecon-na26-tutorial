# Tests

Run local tests from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
```

The tests use the Python standard library. HTTP tests bind loopback ports. The demo process test requires port 8080.

## Live vLLM version checks

`vllm_live.py` deploys lessons 01, 02, and 03 in sequence. Unittest discovery does not run live checks.

Use an idle workload namespace with a bound `workshop-models` PVC containing the pinned lesson models. Reserve two GPUs for the run. Lesson 02 needs two GPUs on one node. Lesson 03 needs two GPU nodes and the LeaderWorkerSet controller.

> ⚠️ **Caution:** The runner creates and deletes lesson workloads and Services. Do not use a namespace with an active lesson.

Set `KUBECONFIG`, `CONTEXT`, and `NAMESPACE` to the test target. Run the checked-in version:

```bash
python3 -B tests/vllm_live.py \
  --kubeconfig "$KUBECONFIG" \
  --context "$CONTEXT" \
  --namespace "$NAMESPACE"
```

Expect one passing result and a cleanup message per lesson. The runner checks readiness, image selection, running version, GPU allocation, PP placement, health, model listing, metrics, chat completions, and streaming through the actual demo server. Inference must return an arithmetic answer, finish normally, and report output usage. Pods must have zero restarts.

The runner refuses namespaces with existing Pods, Deployments, StatefulSets, or Services. Each lesson releases its Pods and GPU quota before the next lesson starts. The runner preserves the namespace, PVC, and model data. Failed checks print Pod diagnostics before cleanup and return a nonzero exit status. Cleanup also runs after Ctrl+C. If the process is forcibly killed, delete the selected lesson's manifest from the same target before rerunning.

To test a candidate before changing the manifests, set `CANDIDATE_IMAGE` to `vllm/vllm-openai:vX.Y.Z@sha256:<digest>`. Run:

```bash
python3 -B tests/vllm_live.py \
  --kubeconfig "$KUBECONFIG" \
  --context "$CONTEXT" \
  --namespace "$NAMESPACE" \
  --image "$CANDIDATE_IMAGE"
```

The override changes the submitted manifests in memory. It does not edit repository files. The version endpoint must match the candidate tag. Use `--lessons 01` for one lesson or `--timeout 2400` to allow more startup time.

After a candidate passes all three lessons, update all three image pins, lesson README version references, and repository guidance together. Lesson 04 uses a separate Dynamo runtime and is outside this runner.
