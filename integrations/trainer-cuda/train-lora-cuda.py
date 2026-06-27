#!/usr/bin/env python3
"""train-lora-cuda.py — entrenador LoRA en GPU NVIDIA (CUDA) con transformers + PEFT.

Puente entre MaestroAI y una GPU en la nube/servidor propio (alternativa al lab MLX
de Apple Silicon). Lee el payload de MaestroAI por stdin, entrena un adapter LoRA con
`peft`, lo fusiona y lo sirve (Ollama vía GGUF, o vLLM con el adapter), y hace el
callback a MaestroAI.

Requisitos (en la GPU):
    pip install "transformers>=4.44" peft datasets accelerate bitsandbytes trl torch

Payload esperado (de finetune.build_trainer_payload):
    {job_id, hf_model, ollama_name, train_jsonl, valid_jsonl, callback_url, hyperparams}

Disparado por n8n (Execute Command) igual que el wrapper MLX:
    echo "$B64" | base64 -d | python3 train-lora-cuda.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def _callback(url: str, status: str, *, ollama_name: str, job_id: str, reason: str = "",
              serve_base_url: str = "") -> None:
    if not url:
        return
    body = json.dumps({
        "status": status,
        "adapter_uri": f"file://adapters/{job_id}",
        "serve_base_url": serve_base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "metrics": {"served_model": ollama_name, "reason": reason, "engine": "cuda-peft"},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception as exc:  # noqa: BLE001
        print(f"callback fallo: {exc}", file=sys.stderr)


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    job_id = payload.get("job_id", "job")
    hf_model = payload.get("hf_model") or payload.get("base_model")
    ollama_name = payload.get("ollama_name", "maestro-lora")
    cb = payload.get("callback_url", "")
    hp = payload.get("hyperparams", {})

    data_dir = f"datasets/{job_id}"
    adapter_dir = f"adapters/{job_id}"
    os.makedirs(data_dir, exist_ok=True)
    with open(f"{data_dir}/train.jsonl", "w", encoding="utf-8") as fh:
        fh.write(payload.get("train_jsonl", ""))
    valid = payload.get("valid_jsonl", "") or payload.get("train_jsonl", "")
    with open(f"{data_dir}/valid.jsonl", "w", encoding="utf-8") as fh:
        fh.write(valid)

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import SFTConfig, SFTTrainer

        tok = AutoTokenizer.from_pretrained(hf_model)
        model = AutoModelForCausalLM.from_pretrained(
            hf_model, torch_dtype=torch.bfloat16, device_map="auto")
        ds = load_dataset("json", data_files={"train": f"{data_dir}/train.jsonl",
                                              "validation": f"{data_dir}/valid.jsonl"})
        peft_cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM")
        sft = SFTConfig(
            output_dir=adapter_dir,
            num_train_epochs=1,
            max_steps=int(hp.get("iters", 600)),
            per_device_train_batch_size=int(hp.get("batch", 4)),
            learning_rate=float(hp.get("learning_rate", "1e-5")),
        )
        trainer = SFTTrainer(model=model, args=sft, train_dataset=ds["train"],
                             eval_dataset=ds["validation"], peft_config=peft_cfg,
                             processing_class=tok)
        trainer.train()
        trainer.save_model(adapter_dir)

        # Fusión + servir: deja el adapter listo. Convierte a GGUF / regístralo en
        # Ollama con tus scripts (o sirve el adapter con vLLM). Ver README.
        os.system(f'OLLAMA_NAME="{ollama_name}" ADAPTER="{adapter_dir}" '
                  f'MODEL="{hf_model}" bash ./fuse-and-serve.sh || true')
        _callback(cb, "completed", ollama_name=ollama_name, job_id=job_id, reason="ok")
    except Exception as exc:  # noqa: BLE001
        _callback(cb, "failed", ollama_name=ollama_name, job_id=job_id, reason=str(exc)[:200])
        raise


if __name__ == "__main__":
    main()
