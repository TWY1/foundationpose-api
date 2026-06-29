#!/bin/bash
set -e

WEIGHTS_DIR="${FOUNDATIONPOSE_WEIGHTS:-/app/weights}"
DATA_DIR="${FOUNDATIONPOSE_DATA:-/app/data}"
OBJECTS_DIR="$DATA_DIR/objects"

echo "============================================="
echo "  FoundationPose API — Starting up"
echo "============================================="

# ── 1. Check / download model weights ─────────────────────────
if [ ! -d "$WEIGHTS_DIR/2024-01-11-20-02-45" ] || [ ! -d "$WEIGHTS_DIR/2023-10-28-18-33-37" ]; then
    echo "[entrypoint] Model weights missing — downloading…"
    mkdir -p "$WEIGHTS_DIR"
    pip install gdown -q 2>/dev/null

    echo "  → Downloading from Hugging Face (gpue/foundationpose-weights)..."
    pip3 install -q huggingface-hub gdown 2>/dev/null
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='gpue/foundationpose-weights',
                  local_dir='$WEIGHTS_DIR',
                  local_dir_use_symlinks=False)
" 2>/dev/null || {
        echo "  Hugging Face failed, trying Google Drive..."
        gdown --folder "https://drive.google.com/drive/folders/1DFezOAD0oD1BblsXVxqDsl8fj0qzB82i" \
            -O "$WEIGHTS_DIR" --quiet || \
        echo "  ⚠ All downloads failed — will run in mock mode"
    }
else
    echo "[entrypoint] Model weights found at $WEIGHTS_DIR"
fi

# ── 2. Generate default book models if none exist ─────────────
if [ -z "$(ls -A "$OBJECTS_DIR" 2>/dev/null)" ]; then
    echo "[entrypoint] No object models found — generating default book meshes…"
    python3 /app/scripts/generate_book_models.py --output "$OBJECTS_DIR"
else
    echo "[entrypoint] Object models present in $OBJECTS_DIR"
fi

# ── 3. Create data directories ────────────────────────────────
mkdir -p "$OBJECTS_DIR" "$DATA_DIR/output" "$DATA_DIR/yolo"

# ── 4. Print environment info ─────────────────────────────────
echo ""
echo "  Python : $(python3 --version)"
echo "  PyTorch: $(python3 -c 'import torch; print(torch.__version__)' 2>/dev/null || echo 'N/A')"
echo "  CUDA   : $(python3 -c 'import torch; print(torch.cuda.is_available())' 2>/dev/null || echo 'N/A')"
echo "  Weights: $WEIGHTS_DIR"
echo "  Data   : $DATA_DIR"
echo ""

# ── 5. Execute the main command ───────────────────────────────
echo "[entrypoint] Starting server…"
exec "$@"
