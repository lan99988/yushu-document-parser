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

# The portable image uses MinerU's ONNX/CPU base runtime. The GPU Compose
# override selects [full] and a CUDA-compatible PyTorch wheel index.
ARG MINERU_EXTRA=
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN if [ -n "${MINERU_EXTRA}" ]; then \
      pip install --index-url "${TORCH_INDEX_URL}" --extra-index-url https://pypi.org/simple "torch>=2.6,<3" torchvision; \
    fi && \
    pip install "mineru${MINERU_EXTRA}==4.0.7"

COPY entrypoint.sh /usr/local/bin/document-parser-entrypoint
RUN chmod 0755 /usr/local/bin/document-parser-entrypoint

WORKDIR /app
VOLUME ["/root/.mineru", "/app/output"]
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/document-parser-entrypoint"]
