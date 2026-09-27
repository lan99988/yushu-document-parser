FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      fonts-noto-cjk \
      libgl1 \
      libglib2.0-0 \
      libgomp1 \
      libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Keep CPU as the portable default. For GPU builds, set TORCH_INDEX_URL to the
# PyTorch wheel index that matches the server's CUDA driver and platform.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --index-url "${TORCH_INDEX_URL}" \
      --extra-index-url https://pypi.org/simple \
      "torch>=2.6,<3" torchvision
RUN pip install "mineru[pipeline]==3.2.3"

WORKDIR /app
VOLUME ["/root/.cache", "/app/output"]
EXPOSE 8000
ENTRYPOINT ["mineru-api"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
