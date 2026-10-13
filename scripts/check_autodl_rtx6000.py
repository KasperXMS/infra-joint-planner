"""Small offline CUDA/Transformers check; no checkpoint or model is loaded."""
import argparse
import json
import math
from importlib import metadata
from pathlib import Path

import torch
import torchvision
import transformers
from transformers import Qwen3_5ForConditionalGeneration


def main(output: Path) -> None:
    assert torch.__version__ == "2.8.0+cu128"
    assert torchvision.__version__ == "0.23.0+cu128"
    assert transformers.__version__ == "5.19.0"
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1
    assert torch.cuda.get_device_capability(0) == (12, 0)
    with torch.inference_mode():
        values = torch.arange(1024, device="cuda", dtype=torch.float32)
        assert values.sum().item() == 523776
        matrix = torch.eye(64, device="cuda", dtype=torch.bfloat16)
        assert torch.equal(matrix @ matrix, matrix)
        q = torch.ones((1, 1, 4, 16), device="cuda", dtype=torch.bfloat16)
        attended = torch.nn.functional.scaled_dot_product_attention(q, q, q)
        assert torch.isfinite(attended).all().item() and math.isclose(attended.float().mean().item(), 1.0)
    torch.cuda.synchronize()
    result = {"status": "pass", "gpu": torch.cuda.get_device_name(0), "compute_capability": [12, 0],
              "checks": ["CUDA reduction", "BF16 matrix multiplication", "SDPA", "Qwen3.5 class import"],
              "packages": {name: metadata.version(name) for name in
                           ("torch", "torchvision", "transformers", "accelerate", "modelscope", "modelscope-hub",
                            "huggingface_hub", "safetensors", "tokenizers", "jsonschema", "numpy", "matplotlib")},
              "loaded_model_checkpoints": 0, "qwen_class": Qwen3_5ForConditionalGeneration.__name__}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
