"""Package ForeFire source scenarios, physical input layers and shard runner.

Uses the repository's actual dataset sources. Does NOT include completed labels
or fabricate them. Upload the resulting archive to the object URI used in Fuzzball.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]


def checksum(path):
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for data in iter(lambda: fp.read(4 * 1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    required = [ROOT / "dataset/ember_init_v2",
                ROOT / "dataset/ember_bench",
                ROOT / "dataset/data_real",
                ROOT / "orchestration/observe/cpu_shard.py",
                ROOT / "ml/observability.py"]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Required ForeFire input missing: {path}")
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Never overwrite a physics archive: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    members = []
    with tarfile.open(output, "x:gz") as tar:
        for src in required:
            paths = sorted(src.rglob("*")) if src.is_dir() else [src]
            for path in paths:
                if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                relative = path.relative_to(ROOT)
                tar.add(path, arcname=relative.as_posix(), recursive=False)
                members.append(str(relative))
    info = {"archive": str(output), "bytes": output.stat().st_size,
            "sha256": checksum(output), "members": len(members),
            "scope": "real ForeFire scenario inputs and CPU simulator code; no derived labels"}
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
