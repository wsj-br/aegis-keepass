FROM python:3.13-alpine

ARG VERSION=dev
LABEL org.opencontainers.image.source="https://github.com/wsj-br/aegis-keepass"
LABEL org.opencontainers.image.version="${VERSION}"

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup -g 1000 app && \
    adduser -D -u 1000 -G app app && \
    mkdir -p /tmp && chown app:app /tmp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aegis_keepass_lib.py .
COPY app/ app/
COPY wsgi.py .
COPY LICENSE NOTICES ./

USER app

EXPOSE 8580

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8580/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8580", "--workers", "1", "--timeout", "300", "--no-control-socket", "wsgi:app"]
