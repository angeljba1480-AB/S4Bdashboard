# Trainer LoRA en GPU NVIDIA (CUDA) — perfil alternativo

Entrena los adapters LoRA de MaestroAI en una **GPU NVIDIA** (nube: RunPod, Lambda,
Vast, o tu propio servidor) usando `transformers` + `peft` + `trl`. Es la alternativa
al laboratorio **MLX** de Apple Silicon (`integrations/n8n/`): mismo payload y mismo
callback, distinto motor.

> Recordatorio: **NaN no entrena** (su API no expone fine-tuning y sus microVM son
> CPU-only). El entrenamiento corre en infra del cliente: Mac/MLX **o** esta GPU/CUDA.

## Archivos
- **`train-lora-cuda.py`** — recibe el payload de MaestroAI por stdin, escribe
  `train/valid.jsonl`, entrena con PEFT (LoRA), guarda el adapter y hace el callback.
- **`fuse-and-serve.sh`** *(tú lo provees)* — fusiona el adapter y lo sirve (GGUF +
  `ollama create`, o vLLM con `--enable-lora`). Esqueleto abajo.

## Puesta en marcha
1. En la GPU:
   ```bash
   pip install "transformers>=4.44" peft datasets accelerate bitsandbytes trl torch
   huggingface-cli login    # para los modelos gated (Llama, Gemma)
   ```
2. Expón un webhook (n8n *Execute Command*, igual que el lab MLX) que haga:
   ```bash
   echo "$B64" | base64 --decode | python3 train-lora-cuda.py
   ```
3. En MaestroAI (Render/`.env`): `FINETUNE_ENABLED=true`,
   `FINETUNE_TRAINER_URL=<webhook GPU>`, y el modelo base (p. ej. `llama3.1:8b`).
   MaestroAI manda `hf_model` (repo HuggingFace, ver `HF_MODEL_MAP` en `app/finetune.py`).
4. Lanza un **job** desde *Fine-tuning*. Al terminar, el callback deja el job
   `completed` con la URL servida (`serve_base_url`) y el `served_model`.

## Servir el resultado (`fuse-and-serve.sh`)
Dos opciones; elige una:

**A) Ollama (GGUF):**
```bash
python -m peft.utils.merge ...        # o AutoPeftModelForCausalLM.merge_and_unload()
python convert_hf_to_gguf.py fused/ --outfile m.gguf --outtype f16
printf 'FROM ./m.gguf\n' > Modelfile && ollama create "$OLLAMA_NAME" -f Modelfile
```

**B) vLLM con LoRA (sin fusionar):**
```bash
vllm serve "$MODEL" --enable-lora --lora-modules "$OLLAMA_NAME=$ADAPTER" \
  --port 8000   # endpoint OpenAI-compatible en /v1
```
Luego conecta esa URL como ruta **local/VPC** en *Admin → Modelos y conectores*.

## Privacidad
Datasets anonimizados + gate de calidad/red-team **antes** de salir de MaestroAI; el
entrenamiento corre en **tu** GPU; el adapter se sirve como ruta privada. Datasets y
pesos viven solo en tu infra (no se suben a Git).
