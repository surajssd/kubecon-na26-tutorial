# Inference 101

## Tutorial

Follow the tutorial in this order:

- Open [01-vllm/README.md](01-vllm/README.md) to deploy a model, inspect its logs, and send requests.
- Continue with [02-tensor-parallel/README.md](02-tensor-parallel/README.md) to serve Muse Glimmer 30B across two GPUs on one node.
- Continue with [03-pipeline-parallel/README.md](03-pipeline-parallel/README.md) to serve the same model across two nodes with pipeline parallelism and LeaderWorkerSet.
- Continue with [04-prefill-disaggregation/README.md](04-prefill-disaggregation/README.md) to separate prefill and decode with NVIDIA Dynamo and two GPUs.

## Workspace

The workspace runs inside the cluster, separately from your model workloads. New terminals start in `tutorial/` and inherit your workload namespace as `NAMESPACE`.

Use the same terminal across lessons. Service URLs use the workload namespace; the demo URL `http://127.0.0.1:8080/` refers to the workspace.

Complete each lesson's cleanup before continuing. Recreating the workspace does not delete model workloads. Cleanup preserves shared model storage and cluster-wide controllers.

## Model Management

The organizer downloads model files before the workshop. The workspace mounts them read-only at `/models`. Your workload namespace receives the shared `workshop-models` persistent volume claim (PVC) automatically. Models load offline from pinned revision paths.

Read `/models/catalog.yaml` for available revisions. Signing in does not download models.

Pods run as non-root with privilege escalation disabled, all capabilities dropped, and the default seccomp profile. Pods use RAM-backed shared memory.
