"""Pin official Hugging Face bytes; use only byte-identical ModelScope weights."""
import argparse
import concurrent.futures
import hashlib
import json
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path


def main(metadata: Path, output: Path):
    official = json.loads(metadata.read_bytes())
    output.mkdir(parents=True, exist_ok=True)

    def prepare(item):
        model, info = item
        root = output / model
        root.mkdir(exist_ok=True)
        url = f"https://www.modelscope.cn/api/v1/models/Qwen/{model}/repo/files?Revision=master&Recursive=true"
        with urllib.request.urlopen(url, timeout=30) as response:
            mirror = json.load(response)
        mirror_files = {f["Path"]: f for f in mirror["Data"]["Files"]}
        lock = {"repository": "Qwen/" + model, "revision": info["sha"], "files": {}}
        for file in info["siblings"]:
            name = file["rfilename"]
            if name.startswith(".") or name == "README.md":
                continue
            if name.endswith(".safetensors"):
                expected = file["lfs"]["sha256"]
                mirrored = mirror_files[name]
                if mirrored["Sha256"] != expected or mirrored["Size"] != file["size"]:
                    raise ValueError("Mirror weights differ from official bytes: " + model + "/" + name)
                query = urllib.parse.urlencode({"Revision": mirrored["Revision"], "FilePath": name})
                lock["files"][name] = {"sha256": expected, "bytes": file["size"],
                    "download_url": f"https://www.modelscope.cn/api/v1/models/Qwen/{model}/repo?{query}",
                    "source": "official Qwen ModelScope mirror, official HF LFS digest verified"}
            else:
                target = root / name
                if not target.exists():
                    with urllib.request.urlopen(f"https://huggingface.co/Qwen/{model}/resolve/{info['sha']}/{name}", timeout=60) as response:
                        target.write_bytes(response.read())
                data = target.read_bytes()
                if "lfs" in file:
                    valid = hashlib.sha256(data).hexdigest() == file["lfs"]["sha256"]
                else:
                    valid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == file["blobId"]
                if not valid:
                    raise ValueError("Official file hash mismatch: " + str(target))
                digest = hashlib.sha256(data).hexdigest()
                lock["files"][name] = {"sha256": digest, "bytes": len(data),
                                        "source": "official Hugging Face pinned revision"}
                mirrored = mirror_files.get(name, {})
                if mirrored.get("Sha256") == digest and mirrored.get("Size") == len(data):
                    query = urllib.parse.urlencode({"Revision": mirrored["Revision"], "FilePath": name})
                    lock["files"][name]["download_url"] = f"https://www.modelscope.cn/api/v1/models/Qwen/{model}/repo?{query}"
        return model, lock

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        locks = dict(pool.map(prepare, official.items()))
    (output / "models.lock.json").write_text(json.dumps(locks, indent=2) + "\n")
    with tarfile.open(output / "model-configs.tar.gz", "w:gz") as archive:
        for model, lock in locks.items():
            for name, info in lock["files"].items():
                if "download_url" not in info:
                    archive.add(output / model / name, arcname=model + "/" + name)
    print(json.dumps({m: {"revision": l["revision"], "files": len(l["files"])} for m, l in locks.items()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.metadata, args.output)
