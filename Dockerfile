FROM node:22-bookworm-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EASYOCR_MODEL_STORAGE_DIRECTORY=/opt/easyocr/models \
    PORT=8000

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

RUN mkdir -p "${EASYOCR_MODEL_STORAGE_DIRECTORY}" \
    && python -c "import easyocr; easyocr.Reader(['ko', 'en'], gpu=False, model_storage_directory='${EASYOCR_MODEL_STORAGE_DIRECTORY}')" \
    && chmod -R a+rX /opt/easyocr

COPY backend/ backend/
COPY --from=frontend-build /build/frontend/dist/ frontend/dist/

RUN addgroup --system notiiq \
    && adduser --system --ingroup notiiq --home /app --no-create-home notiiq \
    && chown -R notiiq:notiiq /app

ENV EASYOCR_DOWNLOAD_ENABLED=false

USER notiiq

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health', timeout=4)"

CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
