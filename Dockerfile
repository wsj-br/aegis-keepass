FROM python:3.12-slim

ARG VERSION=dev
LABEL org.opencontainers.image.source="https://github.com/wsj-br/aegis-keepass"
LABEL org.opencontainers.image.version="${VERSION}"

WORKDIR /app

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --create-home app && \
    mkdir -p /tmp && chown app:app /tmp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aegis_keepass_lib.py .
COPY app/ app/
COPY wsgi.py .

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "--no-control-socket", "wsgi:app"]
