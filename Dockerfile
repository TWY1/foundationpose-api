# ── Stage 1: Base with FoundationPose ──────────────────────────
FROM wenbowen123/foundationpose:latest AS foundationpose

# ── Stage 2: API layer ─────────────────────────────────────────
FROM foundationpose

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV FOUNDATIONPOSE_WEIGHTS=/app/weights
ENV FOUNDATIONPOSE_DATA=/app/data
ENV PORT=8000

# Install API dependencies
RUN pip3 install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    python-multipart==0.0.20 \
    pydantic==2.10.4 \
    gdown>=5.1.0 \
    numpy>=1.26.0 \
    opencv-python-headless>=4.9.0 \
    Pillow>=10.0.0 \
    trimesh>=4.0.0

# Optional: install YOLO for detect-and-pose pipeline
RUN pip3 install --no-cache-dir ultralytics>=8.0.0 2>/dev/null || true

WORKDIR /app

# Copy application code
COPY app/ /app/
COPY scripts/ /app/scripts/
COPY Makefile /app/

RUN mkdir -p /app/data/{objects,output,yolo} /app/weights

# Entrypoint: download weights if missing, then start server
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
