#!/bin/bash
# Download FoundationPose pretrained weights.
# Primary source: Hugging Face (gpue/foundationpose-weights)
# Fallback: Google Drive
set -e

WEIGHTS_DIR="${1:-./weights}"
mkdir -p "$WEIGHTS_DIR"

echo "Downloading FoundationPose weights to $WEIGHTS_DIR"
echo ""

# ── Method 1: Hugging Face (preferred) ────────────────────────
if python3 -c "import huggingface_hub" 2>/dev/null; then
    echo "→ Downloading from Hugging Face (gpue/foundationpose-weights)..."
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='gpue/foundationpose-weights',
    local_dir='$WEIGHTS_DIR',
    local_dir_use_symlinks=False,
)
print('Download complete')
" && echo "✓ Weights downloaded from Hugging Face" && exit 0
fi

# ── Method 2: pip install huggingface-hub and retry ───────────
echo "huggingface_hub not found, installing..."
pip3 install -q huggingface-hub
echo "→ Downloading from Hugging Face (gpue/foundationpose-weights)..."
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='gpue/foundationpose-weights',
    local_dir='$WEIGHTS_DIR',
    local_dir_use_symlinks=False,
)
print('Download complete')
" && echo "✓ Weights downloaded from Hugging Face" && exit 0

# ── Method 3: Google Drive fallback ───────────────────────────
echo ""
echo "Hugging Face download failed, trying Google Drive..."
pip3 install -q gdown
gdown --folder "https://drive.google.com/drive/folders/1DFezOAD0oD1BblsXVxqDsl8fj0qzB82i" \
    -O "$WEIGHTS_DIR" --quiet && echo "✓ Weights downloaded from Google Drive" && exit 0

# ── All methods failed ────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   ⚠ All download methods failed.                            ║"
echo "║   Please download manually:                                 ║"
echo "║                                                             ║"
echo "║   Option A: Hugging Face (recommended)                      ║"
echo "║     pip install huggingface-hub                             ║"
echo "║     python3 -c \"from huggingface_hub import snapshot_download; ║"
echo "║       snapshot_download(repo_id='gpue/foundationpose-weights',║"
echo "║         local_dir='./weights')\"                              ║"
echo "║                                                             ║"
echo "║   Option B: Google Drive                                   ║"
echo "║     https://drive.google.com/drive/folders/1DFezOAD0oD1Bbls║"
echo "║        xVxqDsl8fj0qzB82i                                   ║"
echo "║     Download both folders into ./weights/:                  ║"
echo "║     - 2023-10-28-18-33-37  (refiner)                       ║"
echo "║     - 2024-01-11-20-02-45  (scorer)                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
exit 1
