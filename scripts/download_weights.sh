#!/bin/bash
# Download FoundationPose pretrained weights
# Scorer: 2024-01-11-20-02-45
# Refiner: 2023-10-28-18-33-37
set -e

WEIGHTS_DIR="${1:-./weights}"
mkdir -p "$WEIGHTS_DIR"

echo "Downloading FoundationPose weights to $WEIGHTS_DIR"

# Scorer
if [ ! -d "$WEIGHTS_DIR/2024-01-11-20-02-45" ]; then
    echo "→ Downloading scorer (2024-01-11-20-02-45)..."
    gdown --folder "https://drive.google.com/drive/folders/1EQsS0HdNHpsQmThHgJmpZqMXC3bS1Fnk" \
        -O "$WEIGHTS_DIR/2024-01-11-20-02-45" --quiet || \
    echo "  ⚠ Scorer download failed"
else
    echo "✓ Scorer already present"
fi

# Refiner
if [ ! -d "$WEIGHTS_DIR/2023-10-28-18-33-37" ]; then
    echo "→ Downloading refiner (2023-10-28-18-33-37)..."
    gdown --folder "https://drive.google.com/drive/folders/13QYmrRMqxjKARxaAMt3s2BMEDjIFGoRH" \
        -O "$WEIGHTS_DIR/2023-10-28-18-33-37" --quiet || \
    echo "  ⚠ Refiner download failed"
else
    echo "✓ Refiner already present"
fi

echo "Done. Weights: $WEIGHTS_DIR"
