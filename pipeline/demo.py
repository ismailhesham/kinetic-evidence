"""Offline demo: runs the full pipeline on a sample script and produces MP4."""
from __future__ import annotations
import argparse
from pathlib import Path
from . import render


DEMO_SCRIPT = """The Amazon rainforest, often called the lungs of the Earth, spans more than five million square kilometers across nine countries.
In 2019 alone, an estimated 906,000 hectares were lost to deforestation.
Scientists warn that continued loss threatens global biodiversity.
Brazil, Peru, and Colombia hold the largest shares of the forest.
The question is whether the world can act in time."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="outputs/demo.mp4")
    ap.add_argument("--script", default=None)
    args = ap.parse_args()
    
    text = Path(args.script).read_text(encoding="utf-8") if args.script else DEMO_SCRIPT
    
    # Run full pipeline on local fallbacks
    result = render.run(text, preview=False, use_llm=False)
    
    if result.get("ok"):
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(result["output_mp4"], args.output)
        print(f"DEMO_MP4={args.output}")
    else:
        print(f"DEMO_FAILED: {result}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()