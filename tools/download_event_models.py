"""Explicit online setup for pretrained weights only; never reads a video."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MODELS = {
    "facebook/dinov2-base": "f9e44c814b77203eaa57a6bdbbd535f21ede1415",
    "PekingU/rtdetr_v2_r50vd": "282494075698cab9faa1096ae26856890030c817",
    "google/owlv2-base-patch16-ensemble": "cfd3195ba4ea9592eec887ded089f4c08eff231d",
}


def main():
    from huggingface_hub import HfApi, snapshot_download
    parser=argparse.ArgumentParser()
    parser.add_argument("--vlm",choices=["mlx","transformers"],default="mlx")
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    selected=dict(MODELS)
    if args.vlm == "mlx":
        selected["mlx-community/Qwen3-VL-8B-Instruct-4bit"]="defcdea7cc7a4b0858fea563cbbce171d328e457"
    else:
        selected["Qwen/Qwen3-VL-4B-Instruct"]="ebb281ec70b05090aa6165b016eac8ec08e71b17"
    provenance=[]
    for repo, revision in selected.items():
        info=HfApi().model_info(repo,revision=revision)
        license_name=(info.card_data or {}).get("license")
        if license_name != "apache-2.0":
            raise RuntimeError(f"Review commercial-use license before downloading {repo}: {license_name}")
        kwargs={"local_dir":root/"models"/repo.split("/")[1]} if "Qwen" in repo else {}
        snapshot_download(repo, revision=revision, ignore_patterns=["*.bin","*.pt","*.pth"], **kwargs)
        provenance.append({"repo":repo,"revision":revision,"license":license_name})
    output=root/"artifacts/event-model-provenance.json"
    output.write_text(json.dumps(provenance,indent=2))
    print(f"Installed {len(provenance)} local models. Provenance: {output}")


if __name__=="__main__":main()
