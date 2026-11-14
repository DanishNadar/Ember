"""Manual-only experiment preparation. Import, preview and preflight never submit jobs."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tarfile

import yaml
from .dashboard import fuzzball_command
from .build_workflow import make_workflow, GPU_IMAGE

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def defaults(dataset):
    dataset = Path(dataset).resolve()
    config = yaml.safe_load((dataset.parent / "baseline.yaml").read_text())
    return dict(experiment_name="manual-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
                dataset=str(dataset), output_root=str(ROOT / "artifacts/experiments"),
                config=config, optimizer="Adam", mode="single", trial_learning_rates=[.001, .0003],
                checkpoint=None, fine_tune=False, generate_physics=False,
                cpu_workers=4, physics_scenarios_per_region=1, physics_uri="",
                team_nodes=["CIQ-CHI-SPARK29", "CIQ-CHI-SPARK30"])


def command(*args):
    p = subprocess.run([*fuzzball_command(), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout


def cli_path(path):
    path = Path(path).resolve()
    if fuzzball_command()[0].lower().endswith("wsl.exe"):
        return "/mnt/" + path.drive[0].lower() + path.as_posix()[2:]
    return str(path)


def validate(options):
    """Inspect real arrays/metadata, never instantiate or execute a neural network."""
    o = options
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", o["experiment_name"]):
        raise ValueError("Experiment name must be a unique plain name (letters, numbers, _ or -)")
    if o["mode"] not in ("single", "independent"):
        raise ValueError("DDP launch is unavailable: configure and verify a cross-node rendezvous first; see observe/README.md")
    if o["optimizer"] != "Adam" or o.get("fine_tune"):
        raise ValueError("The verified single-GPU trainer supports Adam and fresh training only; fine-tuning is DDP-recipe-only")
    c = dict(o["config"])
    if (len(c["channel_names"]) != len(c["channel_types"]) or
            any(t not in ("binary", "continuous") for t in c["channel_types"]) or
            c["ignition_channel"] not in c["channel_names"]):
        raise ValueError("Channel names/types and ignition channel do not match the trainer contract")
    if c["horizon_seconds"] <= 0 or not math.isfinite(c["horizon_seconds"]):
        raise ValueError("horizon_seconds must be finite and positive")
    for key in ("epochs", "batch_size", "base_filters", "depth"):
        if type(c[key]) is not int or c[key] <= 0:
            raise ValueError(key + " must be a positive integer")
    if c["depth"] > 8 or c["grid_size"] % 2 ** c["depth"]:
        raise ValueError("Depth must be <=8 and grid_size divisible by 2**depth")
    for key in ("learning_rate", "positive_weight", "burn_loss_weight", "arrival_loss_weight"):
        if not isinstance(c[key], (float, int)) or not math.isfinite(c[key]) or c[key] <= 0:
            raise ValueError(key + " must be finite and positive")
    for key in ("dropout", "threshold", "weight_decay"):
        if not isinstance(c[key], (float, int)) or not math.isfinite(c[key]) or c[key] < 0:
            raise ValueError(key + " must be finite and nonnegative")
    if c["dropout"] >= 1 or not 0 < c["threshold"] < 1:
        raise ValueError("Dropout must be <1 and threshold must be between 0 and 1")
    if type(c["random_seed"]) is not int or c["random_seed"] < 0:
        raise ValueError("random_seed must be a nonnegative integer")
    if not 1 <= o["cpu_workers"] <= 16 or o["physics_scenarios_per_region"] < 1:
        raise ValueError("CPU workers must be 1..16; scenarios per region must be positive")
    if o["mode"] == "independent" and (len(o["trial_learning_rates"]) != 2 or
            any(not math.isfinite(v) or v <= 0 for v in o["trial_learning_rates"])):
        raise ValueError("Independent mode requires exactly two positive learning rates")
    data = Path(o["dataset"]).resolve()
    if not data.is_dir():
        raise ValueError("Dataset missing: select an actual root containing train/, val/, test/")
    manifest = data.parent / "dataset_manifest.json"
    if not manifest.is_file():
        raise ValueError("dataset_manifest.json must exist beside the data directory")
    if (Path(o["output_root"]) / o["experiment_name"]).exists():
        raise ValueError("Output already exists; choose a fresh experiment name")
    sys.path.insert(0, str(ROOT / "ml"))
    from arrival_dataset import discover, validate_checkpoint_contract
    c.update(data_dir=str(data), output_dir="outputs_baseline", device="cuda", num_workers=0)
    paths = discover(c)  # validates shapes, labels, channels, units and cross-split families
    m = json.loads(manifest.read_text())
    records = {r["file"]: r for r in m["simulations"] if r.get("accepted")}
    for split, files in paths.items():
        for file in files:
            key = file.relative_to(data.parent).as_posix()
            if key not in records or sha(file) != records[key]["sha256"]:
                raise ValueError("Dataset provenance mismatch: " + key)
    if o.get("checkpoint"):
        import torch
        checkpoint = torch.load(o["checkpoint"], map_location="cpu", weights_only=False)
        validate_checkpoint_contract(checkpoint, c, paths, o["checkpoint"])
    return c, paths, manifest


def preview(options):
    name = options["experiment_name"]
    prefix = "fb://user/ember/" + name
    wf = make_workflow(prefix + "/input.tgz", options["physics_uri"] or prefix + "/physics.tgz",
                       prefix + "/results", workers=options["cpu_workers"],
                       per_region=options["physics_scenarios_per_region"],
                       parallel_gpu=options["mode"] == "independent")
    if not options["generate_physics"]:
        for index in (0, 1):
            del wf["jobs"][f"physics-{index}"]
            del wf["volumes"][f"physics-{index}-data"]
    return wf


def preflight(options, *, remote=False, require_inputs=True):
    c, paths, manifest = validate(options)
    wf = preview(options)
    report = {"experiment": options["experiment_name"], "dataset_manifest_sha256": sha(manifest),
              "sample_counts": {s: len(p) for s, p in paths.items()}, "config": c,
              "mode": options["mode"], "ddp": False, "new_labels": options["generate_physics"],
              "jobs": {k: j["resource"] for k, j in wf["jobs"].items()},
              "output": str(Path(options["output_root"]) / options["experiment_name"]),
              "expected_artifacts": ["history.csv", "events.jsonl", "best.pt", "test_metrics.json", "gallery", "run_summary.json"],
              "image": GPU_IMAGE, "image_evidence": "GB10 CUDA verified by historical workflow ba78b08b-632e-4de8-9d4b-fcb7e105c61e",
              "remote_checked": False}
    if remote:
        report["context"] = command("context", "show")
        if "team15@fb-hack.local" not in report["context"]:
            raise ValueError("Active context is not verified Team 15; select the correct context")
        nodes = json.loads(command("node", "list", "--output", "json"))
        slots = []
        for node in nodes:
            if node["hostName"] in options["team_nodes"]:
                free = node["resource"]["free"]
                slots.append([free["cpu"]["cores"], int(free["mem"]["bytes"]), free["devices"].get("nvidia.com/gpu", 0)])
        report["free_team_resources"] = [list(s) for s in slots]
        for job in sorted(wf["jobs"].values(), key=lambda j: -j["resource"].get("devices", {}).get("nvidia.com/gpu", 0)):
            r = job["resource"]; cores = r["cpu"]["cores"]; gpu = r.get("devices", {}).get("nvidia.com/gpu", 0)
            memory = int(r["memory"]["size"].replace("GiB", "")) * 2 ** 30
            slot = next((s for s in slots if s[0] >= cores and s[1] >= memory and s[2] >= gpu), None)
            if slot is None:
                raise ValueError("Requested jobs do not fit current free Team 15 resources; reduce jobs/workers or wait")
            slot[0] -= cores; slot[1] -= memory; slot[2] -= gpu
        if require_inputs:
            for volume in wf["volumes"].values():
                command("object", "describe", volume["ingress"][0]["source"]["uri"], "--output", "json")
        report["remote_checked"] = True
        report["resource_note"] = "Point-in-time fit estimate, not a scheduler reservation or placement guarantee"
    return report


def prepare(options):
    """Create immutable local input bundle; no uploads or workflow submission."""
    c, paths, manifest = validate(options)
    run = Path(options["output_root"]) / options["experiment_name"]
    run.mkdir(parents=True, exist_ok=False)
    members = {"ml/" + p.name: p for p in (ROOT / "ml").glob("*.py")}
    members["orchestration/fuzzball/execute_training.py"] = ROOT / "orchestration/fuzzball/execute_training.py"
    for files in paths.values():
        for p in files:
            members["pilot/" + p.relative_to(Path(options["dataset"]).resolve().parent).as_posix()] = p
    members["pilot/dataset_manifest.json"] = manifest
    for label in (["baseline", "lower_lr"] if options["mode"] == "independent" else ["baseline"]):
        cfg = dict(c, data_dir="data", output_dir="outputs_" + label)
        if options["mode"] == "independent":
            cfg["learning_rate"] = options["trial_learning_rates"][0 if label == "baseline" else 1]
        p = run / (label + ".yaml"); p.write_text(yaml.safe_dump(cfg, sort_keys=False)); members["pilot/" + p.name] = p
    package = run / "package_manifest.json"
    package.write_text(json.dumps({"sha256": {k: sha(v) for k, v in members.items()}}, indent=2))
    members["pilot/package_manifest.json"] = package
    archive = run / "input.tgz"
    with tarfile.open(archive, "x:gz", compresslevel=1) as tar:
        for name, p in members.items(): tar.add(p, arcname=name, recursive=False)
    (run / "workflow.fz").write_text(yaml.safe_dump(preview(options), sort_keys=False))
    (run / "options.json").write_text(json.dumps(options, indent=2))
    provenance = {"source_git": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
                  "source_dirty": bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)),
                  "dataset_manifest_sha256": sha(manifest), "input_sha256": sha(archive),
                  "options_sha256": sha(run / "options.json"), "workflow_sha256": sha(run / "workflow.fz"),
                  "architecture": {k: c[k] for k in ["base_filters", "depth", "dropout", "channel_names"]}}
    (run / "provenance.json").write_text(json.dumps(provenance, indent=2))
    return run


def stage_inputs(run, *, confirm=False):
    if confirm is not True:
        raise ValueError("Set confirm=True deliberately to upload inputs; this never submits a workflow")
    run = Path(run); o = json.loads((run / "options.json").read_text())
    if sha(run / "input.tgz") != json.loads((run / "provenance.json").read_text())["input_sha256"]:
        raise ValueError("Prepared input changed; prepare a fresh experiment")
    return command("object", "put", cli_path(run / "input.tgz"), "fb://user/ember/" + o["experiment_name"] + "/input.tgz", "--ttl", "7d")


def launch(run, *, confirmation=None, dry_run=True):
    """Only this deliberate, guarded function may submit. No import-time effects."""
    run = Path(run); o = json.loads((run / "options.json").read_text())
    if dry_run:
        return {"submitted": False, "preview": preview(o)}
    if confirmation != o["experiment_name"]:
        raise ValueError("Type the exact experiment name to confirm launch")
    if (run / "submission.json").exists() or (run / "launch-attempt.json").exists():
        raise ValueError("A submission was already attempted; inspect workflow list before retrying")
    provenance = json.loads((run / "provenance.json").read_text())
    for file, key in [("input.tgz", "input_sha256"), ("options.json", "options_sha256"), ("workflow.fz", "workflow_sha256")]:
        if sha(run / file) != provenance[key]: raise ValueError("Prepared file changed: " + file)
    # Validate against a fresh output sentinel while retaining the immutable prepared directory.
    check = dict(o, output_root=str(run / "future-output-check"))
    report = preflight(check, remote=True)
    if report["dataset_manifest_sha256"] != provenance["dataset_manifest_sha256"]:
        raise ValueError("Dataset manifest changed after preparation")
    workflows = json.loads(command("workflow", "list", "--output", "json"))
    if any(w.get("name") == o["experiment_name"] for w in workflows):
        raise ValueError("Workflow name already exists remotely; choose a fresh experiment")
    remote = json.loads(command("object", "describe", "fb://user/ember/" + o["experiment_name"] + "/input.tgz", "--output", "json"))
    if provenance["input_sha256"] not in json.dumps(remote): raise ValueError("Remote input digest differs from prepared input")
    command("workflow", "validate", cli_path(run / "workflow.fz"))
    (run / "preflight.json").write_text(json.dumps(report, indent=2))
    with (run / "launch-attempt.json").open("x") as out:
        json.dump({"requested_at_utc": datetime.now(timezone.utc).isoformat()}, out)
    result = json.loads(command("workflow", "start", cli_path(run / "workflow.fz"), "--name", o["experiment_name"], "--output", "json"))
    (run / "submission.json").write_text(json.dumps(result, indent=2))
    return result


def retrieve(run):
    """Fetch finished artifacts into fresh per-job folders; never starts compute."""
    from .dashboard import events_from_text, fuzzball_log
    run = Path(run); o = json.loads((run / "options.json").read_text())
    workflow = json.loads((run / "submission.json").read_text())["ID"]
    status = json.loads(command("workflow", "describe", workflow, "--output", "json"))
    if not any(s.get("kind") == "STAGE_KIND_WORKFLOW" and s.get("status") == "STAGE_STATUS_FINISHED"
               for s in status["status"]["stages"]):
        raise ValueError("Workflow has not finished successfully; inspect live status/errors before retrieval")
    destination = run / ("retrieval-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    destination.mkdir()
    events, runs = [], {}
    for job in preview(o)["jobs"]:
        archive = destination / (job + ".tgz")
        uri = "fb://user/ember/" + o["experiment_name"] + "/results/" + job + "-results.tgz"
        info = command("object", "describe", uri, "--output", "json")
        command("object", "get", uri, cli_path(archive))
        if sha(archive) not in info: raise ValueError("Retrieved archive hash differs: " + job)
        target = destination / job; target.mkdir()
        with tarfile.open(archive) as tar: tar.extractall(target, filter="data")
        text = fuzzball_log(workflow, job)
        (target / "workflow.log").write_text(text, encoding="utf-8")
        events += events_from_text(text, workflow_id=workflow, job=job)
        for file in target.glob("**/run_summary.json"):
            runs[job] = {"summary": json.loads(file.read_text())}
    (destination / "retrieval_verification.json").write_text(json.dumps({"workflow_id": workflow, "runs": runs}, indent=2))
    collected = destination / "collected"; collected.mkdir()
    (collected / "events.jsonl").write_text(''.join(json.dumps(e)+'\n' for e in events))
    (destination / "workflow_status.json").write_text(json.dumps(status, indent=2))
    return destination
