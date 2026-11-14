ARG OLLAMA_IMAGE=ollama/ollama@sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592
FROM ${OLLAMA_IMAGE}

COPY entrypoint.sh /usr/local/bin/notiiq-ollama-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/notiiq-ollama-entrypoint \
    && chmod +x /usr/local/bin/notiiq-ollama-entrypoint

ENV OLLAMA_HOST=0.0.0.0:11434 \
    OLLAMA_MODEL=qwen3:8b

EXPOSE 11434
VOLUME ["/root/.ollama"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD ollama list >/dev/null 2>&1 || exit 1

ENTRYPOINT ["/usr/local/bin/notiiq-ollama-entrypoint"]
