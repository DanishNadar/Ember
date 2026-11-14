"""Explicit, versioned Observatory export. No execution or publication by default.

Export: python scripts/export_observatory.py --experiment-id EXPERIMENT
Publish an inspected snapshot only: --publish-manifest PATH --approve-sha256 HASH
--publish-branch reports/observatory-UNIQUE. Publication never changes the checkout.
"""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

import nbformat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orchestration.observe.locations import experiment_roots, notebook_roots

SECRET_KEYS = {"token", "access_token", "refresh_token", "authorization", "password",
               "client_secret", "secret", "api_key", "cookie", "cookies", "connection_key"}
SECRET_PATTERNS = [r"gh[pousr]_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{30,}",
                   r"AKIA[0-9A-Z]{16}", r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
                   r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scrub(value):
    """Redact credentials, home paths and private IPs in text/metadata, not numbers."""
    if isinstance(value, dict):
        return {k: "[REDACTED]" if k.lower() in SECRET_KEYS else v if k == "image/png" else scrub(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if not isinstance(value, str):
        return value
    for pattern in SECRET_PATTERNS:
        value = re.sub(pattern, "[REDACTED]", value, flags=re.S)
    value = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9_.+/=-]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)(token|api_key|password|client_secret)=([^\s&\"'<>]+)", r"\1=[REDACTED]", value)
    value = re.sub(r'''(?i)\b(token|api_key|access_token|password|client_secret)\s*=\s*(["'])([^"'\r\n]+)\2''',
                   r'\1="[REDACTED]"', value)
    value = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[REDACTED]@", value)
    # Read strings are decoded before scrubbing; both slash styles are supported.
    value = re.sub(r"(?i)(?:[a-z]:[\\/]+Users[\\/]+|/mnt/[a-z]/Users/)[^\\/\s\"'<>]+", "[user-home]", value)
    value = re.sub(r"/(?:home|Users)/[^/\s\"'<>]+", "[user-home]", value)
    def address(match):
        try:
            return "[private-ip]" if ipaddress.ip_address(match.group()).is_private else match.group()
        except ValueError:
            return match.group()
    return re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", address, value)


def git_info(path):
    command = ["git", "--no-optional-locks", "-C", str(path)]
    def read(args):
        p = subprocess.run(command + args, capture_output=True, text=True, timeout=20)
        return p.stdout.strip() if p.returncode == 0 else None
    return {"sha": read(["rev-parse", "HEAD"]),
            "branch": read(["branch", "--show-current"]),
            "dirty": bool(read(["status", "--porcelain=v1"]))}


def inspect_notebook(path):
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    outputs = [o for c in nb.cells for o in c.get("outputs", [])]
    stats = {"cells": len(nb.cells), "code_cells": sum(c.cell_type == "code" for c in nb.cells),
             "executed_cells": sum(c.get("execution_count") is not None for c in nb.cells),
             "output_types": dict(Counter(o.output_type for o in outputs)),
             "mime_types": dict(Counter(k for o in outputs for k in o.get("data", {}))),
             "output_json_bytes": len(json.dumps(outputs).encode("utf-8")),
             "errors": [{"name": o.ename, "message": o.evalue} for o in outputs if o.output_type == "error"],
             "warning_streams": sum(o.output_type == "stream" and o.get("name") == "stderr" for o in outputs)}
    return nb, stats


def newest_executed(roots):
    candidates = {p.resolve() for base in roots if base.is_dir() for p in base.rglob("*.ipynb")
                  if ".ipynb_checkpoints" not in p.parts and "reports" not in p.parts}
    for path in sorted(candidates, key=lambda p: p.stat().st_mtime_ns, reverse=True):
        _, stats = inspect_notebook(path)
        if stats["executed_cells"] and stats["output_types"]:
            return path
    raise ValueError("No saved executed notebook found; save outputs or pass --notebook explicitly")


def run_metrics(roots, experiment_id):
    results, seen = [], set()
    for root in roots:
        if not root.is_dir():
            continue
        for file in sorted(root.glob("**/run_summary.json")):
            if experiment_id not in file.parts:
                continue
            summary = json.loads(file.read_text(encoding="utf-8"))
            identity = summary.get("checkpoint_sha256") or sha(file)
            if identity in seen:
                continue
            seen.add(identity)
            test_file, history_file = file.parent / "test_metrics.json", file.parent / "history.csv"
            if not test_file.is_file() or not history_file.is_file():
                raise ValueError("Incomplete result bundle: " + str(file.parent))
            test = json.loads(test_file.read_text(encoding="utf-8"))
            dataset_file = file.parent / "dataset_manifest.json"
            dataset = json.loads(dataset_file.read_text(encoding="utf-8")) if dataset_file.is_file() else {}
            verification = []
            for parent in file.parents:
                if parent == root.parent:
                    break
                verification = list(parent.glob("*verification.json"))
                if verification:
                    break
            workflow_ids = []
            node = None
            for provenance in verification:
                data = json.loads(provenance.read_text(encoding="utf-8"))
                candidates = list(data.get("runs", {}).values()) or [data]
                if any(c.get("summary", {}).get("checkpoint_sha256") == identity for c in candidates):
                    if data.get("workflow_id"):
                        workflow_ids.append(data["workflow_id"])
                    for candidate in candidates:
                        if candidate.get("summary", {}).get("checkpoint_sha256") == identity:
                            node = candidate.get("node")
            hardware = summary.get("hardware", {})
            results.append({"run": file.parent.name, "workflow_ids": sorted(set(workflow_ids)),
                            "checkpoint_sha256": summary.get("checkpoint_sha256"), "node": scrub(node),
                            "completed_epochs": summary.get("completed_epochs"), "best_epoch": summary.get("best_epoch"),
                            "training_wall_seconds": summary.get("training_wall_seconds"),
                            "validation": summary.get("validation"), "test": test,
                            "sample_counts": summary.get("sample_counts"), "families": summary.get("families"),
                            "hardware": {k: hardware.get(k) for k in ("gpu_name", "architecture", "torch", "cuda", "cudnn", "compute_capability")},
                            "dataset": {k: dataset.get(k) for k in ("dataset_kind", "scope", "source_commit", "forefire_version", "grid_size", "cell_size_meters", "horizon_seconds", "split_policy", "channel_names")},
                            "source_hashes": {"run_summary": sha(file), "test_metrics": sha(test_file), "history_csv": sha(history_file)},
                            "history_source": history_file})
    return results


def export(root, experiment_id=None, notebook=None, output_root=None, allow_errors=False):
    roots = notebook_roots(root) + [ROOT / "notebooks"]
    source = Path(notebook).resolve() if notebook else newest_executed(roots)
    nb, stats = inspect_notebook(source)
    if not stats["executed_cells"] or not stats["output_types"]:
        raise ValueError("Notebook has no saved execution outputs")
    if stats["errors"] and not allow_errors:
        raise ValueError("Notebook contains exceptions; inspect them or explicitly use --allow-errors")
    if experiment_id is None:
        candidates = set()
        for base in experiment_roots(root):
            for summary in base.glob("**/run_summary.json"):
                candidates.add(base.name if (base / "dataset_manifest.json").exists()
                               else summary.relative_to(base).parts[0])
        mentioned = {value for value in candidates if value in nbformat.writes(nb)}
        if len(mentioned) == 1:
            experiment_id = mentioned.pop()
        elif len(candidates) == 1:
            experiment_id = candidates.pop()
        elif candidates:
            raise ValueError("Multiple experiments found; choose --experiment-id explicitly")
        else:
            experiment_id = "notebook-" + sha(source)[:12]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", experiment_id):
        raise ValueError("Use a plain experiment ID; paths and traversal are not allowed")
    now = datetime.now(timezone.utc)
    version = now.strftime("%Y%m%dT%H%M%S.%fZ") + "-" + sha(source)[:12]
    base = Path(output_root) if output_root else Path(root) / "reports/observatory"
    destination = base / experiment_id / version
    destination.mkdir(parents=True, exist_ok=False)
    # Image data is retained byte-for-byte; text, metadata and source are sanitized.
    safe = nbformat.reads(json.dumps(scrub(json.loads(nbformat.writes(nb)))), as_version=4)
    safe.metadata.pop("widgets", None)
    safe.metadata.pop("vscode", None)
    safe.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    executed = destination / "Ember_Observatory.executed.ipynb"
    nbformat.write(safe, executed)
    figures = destination / "figures"; figures.mkdir()
    known_images, figure_names = {}, []
    for cell in safe.cells:
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if "image/png" in data:
                blob = base64.b64decode(data["image/png"], validate=True)
                digest = hashlib.sha256(blob).hexdigest()
                if digest not in known_images:
                    file = figures / f"figure_{len(known_images) + 1:03d}.png"
                    file.write_bytes(blob); known_images[digest] = file.name
                figure_names.append("figures/" + known_images[digest])
    runs = run_metrics(experiment_roots(root), experiment_id)
    for run in runs:
        history = run.pop("history_source")
        (destination / (run["run"] + "_history.csv")).write_text(history.read_text(encoding="utf-8"), encoding="utf-8")
    metrics = {"experiment_id": experiment_id, "runs": runs,
               "selection_criterion": "Lowest validation loss; held-out test is reporting only",
               "selected_run": min(runs, key=lambda r: r["validation"]["loss"])["run"] if runs else None,
               "scope": "Agreement with ForeFire simulator labels; not observed wildfire accuracy"}
    # Runtime checks and held-out galleries are evidence alongside training,
    # never an input to the validation-only checkpoint selection above.
    supplemental = {}
    for base in experiment_roots(root):
        experiment = base if base.name == experiment_id else base / experiment_id
        verification = experiment / "runtime_verification.json"
        if verification.is_file():
            supplemental["runtime_verification"] = json.loads(verification.read_text(encoding="utf-8"))
        for file in sorted(experiment.glob("**/gallery_metrics.json")):
            supplemental.setdefault("prediction_galleries", []).append(
                json.loads(file.read_text(encoding="utf-8")))
    metrics.update(supplemental)
    (destination / "metrics.json").write_text(json.dumps(scrub(metrics), indent=2, allow_nan=False), encoding="utf-8")
    timings = [v for c in nb.cells for k, v in c.metadata.get("execution", {}).items() if k.endswith("idle")]
    metadata = {"experiment_id": experiment_id, "exported_at_utc": now.isoformat(),
                "source_notebook_sha256": sha(source), "source_notebook_saved_at_utc": datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(),
                "execution_finished_at_utc": max(timings) if timings else None,
                "execution_time_note": "Saved-file timestamp is not execution time; unknown execution timestamps remain null",
                "source_git": git_info(source.parent), "exporter_git": git_info(ROOT),
                "exporter_script_sha256": sha(__file__), "notebook": stats,
                "workflow_ids": sorted({w for r in runs for w in r["workflow_ids"]}),
                "figures": sorted(set(figure_names)),
                "publication": "Saved snapshot provenance; publication status is recorded separately in publication.json",
                "redactions": "Home paths, private IPs and recognizable credentials removed from text/metadata; inspect images before publication"}
    (destination / "metadata.json").write_text(json.dumps(scrub(metadata), indent=2), encoding="utf-8")
    # Basic nbconvert template has no remote JavaScript/CSS dependencies.
    from nbconvert import HTMLExporter
    from bs4 import BeautifulSoup
    body, _ = HTMLExporter(template_name="basic").from_notebook_node(safe)
    soup = BeautifulSoup(body, "html.parser")
    for element in soup.find_all(["script", "iframe", "object", "embed"]):
        element.decompose()
    for element in soup.find_all(True):
        for attribute in list(element.attrs):
            if attribute.lower().startswith("on"):
                del element.attrs[attribute]
        if element.name == "img" and not str(element.get("src", "")).startswith("data:image/png;base64,"):
            element.decompose()
    css = "body{max-width:1200px;margin:2em auto;padding:0 1em;font:16px system-ui}pre{overflow:auto;background:#f5f5f5;padding:1em}img{max-width:100%;height:auto}table{border-collapse:collapse}td,th{padding:.5em;border:1px solid #bbb}.input_prompt,.output_prompt{color:#666}"
    report = '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; img-src data:; style-src &#39;unsafe-inline&#39;"><title>Ember Observatory - ' + html.escape(experiment_id) + '</title><style>' + css + '</style></head><body>'
    report += '<p>Versioned saved-output snapshot. Simulator agreement only. <a href="metrics.json">Metrics JSON</a>; <a href="metadata.json">provenance</a>.</p>' + str(soup) + '</body></html>'
    (destination / "report.html").write_text(report, encoding="utf-8")
    index = ["# Ember Observatory snapshot", "", f"Experiment: `{experiment_id}`", "",
             "[HTML report](report.html) - [executed notebook](Ember_Observatory.executed.ipynb) - [metrics](metrics.json) - [provenance](metadata.json)", "",
             "| Run | Epochs | Validation IoU | Test IoU | Conditional test arrival MAE (s) |", "|---|---:|---:|---:|---:|"]
    for run in runs:
        index.append(f"| {run['run']} | {run['completed_epochs']} | {run['validation']['iou']:.6f} | {run['test']['iou']:.6f} | {run['test']['arrival_mae_seconds_on_reached']:.3f} |")
    index += ["", "Validation and test use different held-out regions. Conditional arrival error omits missed fire cells. This is a small simulator pilot, not operational wildfire accuracy.", ""]
    index += [f"![Saved notebook visualization]({name})" for name in sorted(set(figure_names))]
    (destination / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    files = [{"path": str(p.relative_to(destination).as_posix()), "bytes": p.stat().st_size, "sha256": sha(p)}
             for p in sorted(destination.rglob("*")) if p.is_file()]
    manifest = {"schema_version": 1, "experiment_id": experiment_id, "version": version,
                "source_notebook_sha256": sha(source), "files": files}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    digest = sha(destination / "manifest.json")
    (destination / "manifest.sha256").write_text(digest + "  manifest.json\n", encoding="utf-8")
    verify_manifest(destination / "manifest.json", digest)
    archive = destination.parent / (version + ".zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as zipped:
        for p in sorted(destination.rglob("*")):
            if p.is_file():
                zipped.write(p, p.relative_to(destination))
    return {"directory": str(destination), "manifest": str(destination / "manifest.json"),
            "manifest_sha256": digest, "upload_bundle": str(archive), "notebook": stats,
            "runs": len(runs), "published": False}


def verify_manifest(path, expected):
    path = Path(path).resolve()
    if sha(path) != expected:
        raise ValueError("Manifest differs from the explicitly approved SHA-256")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,150}",
            manifest.get(key, "")) for key in ("experiment_id", "version")):
        raise ValueError("Invalid manifest schema, experiment ID or version")
    for item in manifest["files"]:
        file = (path.parent / item["path"]).resolve()
        if not file.is_relative_to(path.parent) or not file.is_file() or sha(file) != item["sha256"]:
            raise ValueError("Artifact is missing, outside the snapshot, or changed: " + item["path"])
        if file.stat().st_size > 10_000_000 or file.suffix not in {".png", ".svg", ".json", ".html", ".md", ".csv", ".ipynb"}:
            raise ValueError("Artifact is too large or not an approved report type")
        if file.suffix != ".png":
            text = file.read_text(encoding="utf-8")
            if any(re.search(pattern, text, re.S) for pattern in SECRET_PATTERNS):
                raise ValueError("Recognizable credential remains in " + item["path"])
    return manifest


def publication_receipt(manifest_sha256, branch, repository):
    """Publication adds a receipt without rewriting approved snapshot bytes."""
    return {"state": "published", "published_at_utc": datetime.now(timezone.utc).isoformat(),
            "repository": repository, "branch": branch,
            "approved_manifest_sha256": manifest_sha256,
            "scope": "Receipt is shared in the same commit as the approved snapshot"}


def publish(root, manifest_path, approved_sha256, branch):
    """Push ONLY a reviewed snapshot using a temporary index; leave main and files alone."""
    if not branch or not branch.startswith("reports/observatory-"):
        raise ValueError("Use a new reports/observatory-... branch; main is never a publication target")
    path = Path(manifest_path).resolve()
    manifest = verify_manifest(path, approved_sha256)
    root = Path(root).resolve()
    def git(*args, data=None, env=None, check=True):
        return subprocess.run(["git", "-C", str(root), *args], input=data, capture_output=True,
                              env=env, check=check, timeout=90)
    git("check-ref-format", "--branch", branch)
    remote = git("remote", "get-url", "origin").stdout.decode().strip()
    match = re.fullmatch(r"(?:https://github.com/|git@github.com:)([^/]+/[^/]+?)(?:\.git)?", remote)
    if not match:
        raise ValueError("Publication supports a verified GitHub origin only")
    ref = "refs/heads/" + branch
    if git("show-ref", "--verify", "--quiet", ref, check=False).returncode == 0:
        raise ValueError("Publication branch already exists locally; choose a fresh branch")
    exists = git("ls-remote", "--exit-code", "--heads", "origin", ref, check=False)
    if exists.returncode != 2:
        raise ValueError("Remote branch already exists or could not be checked; publication stopped")
    git("fetch", "--no-tags", "origin", "main")
    base = git("rev-parse", "origin/main").stdout.decode().strip()
    prefix = Path("reports/observatory") / manifest["experiment_id"] / manifest["version"]
    with tempfile.TemporaryDirectory(prefix="ember-publish-") as temporary:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / "index"))
        git("read-tree", base, env=env)
        payloads = {}
        for item in manifest["files"]:
            data = (path.parent / item["path"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Artifact changed after approval: " + item["path"])
            payloads[item["path"]] = data
        payloads["manifest.json"] = path.read_bytes()
        if hashlib.sha256(payloads["manifest.json"]).hexdigest() != approved_sha256:
            raise ValueError("Manifest changed after approval")
        payloads["manifest.sha256"] = (approved_sha256 + "  manifest.json\n").encode()
        payloads["publication.json"] = json.dumps(publication_receipt(
            approved_sha256, branch, match.group(1)), indent=2).encode()
        for name, data in payloads.items():
            blob = git("hash-object", "-w", "--stdin", data=data).stdout.decode().strip()
            git("update-index", "--add", "--cacheinfo", "100644", blob, (prefix / name).as_posix(), env=env)
        tree = git("write-tree", env=env).stdout.decode().strip()
    commit = git("commit-tree", tree, "-p", base,
                 data=f"Publish approved Observatory snapshot {manifest['experiment_id']}\n\nManifest SHA-256: {approved_sha256}\n".encode()).stdout.decode().strip()
    git("update-ref", ref, commit, "0" * 40)
    git("push", "--set-upstream", "origin", ref + ":" + ref)
    actual = git("ls-remote", "origin", ref).stdout.decode().split()[0]
    if actual != commit:
        raise RuntimeError("Could not verify published snapshot head")
    url = f"https://github.com/{match.group(1)}/blob/{commit}/{prefix.as_posix()}"
    return {"commit": commit, "branch": branch, "index_url": url + "/README.md",
            "html_url": url + "/report.html", "metrics_url": url + "/metrics.json",
            "notebook_url": url + "/Ember_Observatory.executed.ipynb"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--experiment-id", help="Auto-detected only when the saved snapshot identifies one experiment")
    parser.add_argument("--notebook", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--allow-errors", action="store_true")
    parser.add_argument("--publish-manifest", type=Path)
    parser.add_argument("--approve-sha256")
    parser.add_argument("--publish-branch")
    args = parser.parse_args()
    if args.publish_manifest:
        if not args.approve_sha256:
            parser.error("Review the local export and supply --approve-sha256 before publication")
        result = publish(args.project_root, args.publish_manifest, args.approve_sha256, args.publish_branch)
    else:
        result = export(args.project_root, args.experiment_id, args.notebook, args.output_root, args.allow_errors)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
