# LOCAL qualification only. Build using git archive to exclude ignored secrets.
FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build:showcase

FROM python:3.11.9-slim-bookworm
WORKDIR /app
COPY deploy/requirements-showcase-free.txt /app/deploy/
RUN python -m pip install --no-cache-dir -r deploy/requirements-showcase-free.txt httpx==0.28.1 psutil==7.2.2
COPY . /app
COPY --from=frontend /build/frontend/dist /app/frontend/dist
ENV SHOWCASE_RUNTIME=e5-int8-fp32-corpus-v1 \
    SHOWCASE_EMBEDDING_DIR=/models \
    SHOWCASE_CLASSIFIER_PATH=/models/candidate.joblib \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
CMD ["python", "-m", "showcase.release_probe", "--encoder", "free-candidate", "--output", "/evidence/linux-free.json"]
