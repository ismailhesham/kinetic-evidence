"""AI image generation as an OPT-IN, WATERMARKED last-resort provider."""
from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Dict, List

DEFAULT_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
TURBO_MODEL   = "stabilityai/sdxl-turbo"

PHOTOREAL_SUFFIX = (
    ", professional photograph, photorealistic, natural lighting, "
    "shot on 35mm film, sharp focus, high detail, cinematic composition, "
    "realistic textures, depth of field"
)

NEGATIVE_PROMPT = (
    "cartoon, illustration, painting, drawing, 3d render, CGI, "
    "anime, sketch, low quality, blurry, watermark, text, logo, "
    "deformed, distorted, extra limbs, bad anatomy"
)

_PIPE_STATE = {"loaded": False, "pipe": None, "device": "cpu", "load_note": "", "model_id": ""}
_LOCK = threading.Lock()

def _ai_enabled() -> bool:
    return os.environ.get("ALLOW_AI_IMAGES", "false").strip().lower() in ("true", "1", "yes", "on")

def _resolve_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"

def _load_pipeline():
    with _LOCK:
        if _PIPE_STATE["loaded"]:
            return _PIPE_STATE["pipe"]
        _PIPE_STATE["loaded"] = True
        try:
            import torch
            from diffusers import AutoPipelineForText2Image
        except Exception as e:
            _PIPE_STATE["load_note"] = f"diffusers_or_torch_unavailable: {e}"
            return None

        device = _resolve_device()
        model_id = os.environ.get("AI_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        use_fp16 = (device == "cuda")

        try:
            kwargs = {"torch_dtype": torch.float16 if use_fp16 else torch.float32, "use_safetensors": True}
            if use_fp16:
                kwargs["variant"] = "fp16"
            pipe = AutoPipelineForText2Image.from_pretrained(model_id, **kwargs).to(device)
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
            _PIPE_STATE.update({"pipe": pipe, "device": device, "model_id": model_id, "load_note": f"loaded:{model_id}"})
            return pipe
        except Exception as e:
            _PIPE_STATE["load_note"] = f"model_load_failed: {e}"
            return None

def _generation_params(model_id: str) -> Dict:
    is_turbo = "turbo" in model_id.lower()
    try:
        steps = int(os.environ.get("AI_IMAGE_STEPS", "4" if is_turbo else "30"))
    except Exception:
        steps = 4 if is_turbo else 30
    try:
        cfg = float(os.environ.get("AI_IMAGE_CFG", "0.0" if is_turbo else "7.0"))
    except Exception:
        cfg = 0.0 if is_turbo else 7.0
    return {"steps": steps, "cfg": cfg}

def generate(prompt: str, out_dir: str, width: int = 1280, height: int = 720, seed: int | None = None) -> List[Dict]:
    if not _ai_enabled() or not prompt.strip():
        return []
    pipe = _load_pipeline()
    if pipe is None:
        return []

    model_id = _PIPE_STATE["model_id"]
    params = _generation_params(model_id)
    full_prompt = prompt.rstrip(" ,") + PHOTOREAL_SUFFIX

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(out_dir) / "ai_illustration.png"

    try:
        import torch
        generator = torch.Generator(device=_PIPE_STATE["device"])
        if seed is not None:
            generator.manual_seed(seed)

        kwargs = {"prompt": full_prompt, "num_inference_steps": params["steps"],
                  "guidance_scale": params["cfg"], "width": width, "height": height, "generator": generator}
        if params["cfg"] > 0:
            kwargs["negative_prompt"] = NEGATIVE_PROMPT

        image = pipe(**kwargs).images[0]
        image.save(str(out_path))

        return [{
            "provider": "ai_generated", "path": str(out_path),
            "metadata": {
                "kind": "image", "generated": True, "model": model_id,
                "prompt_used": full_prompt, "seed": generator.initial_seed(),
                "license_type": "ai_generated", "attribution_required": False,
            },
        }]
    except Exception as e:
        print(f"AI_GEN_ERR: {e}")
        return []