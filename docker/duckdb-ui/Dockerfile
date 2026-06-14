FROM python:3.12-slim

# socat: UI 서버(127.0.0.1)를 컨테이너 외부로 브리지하기 위함.
RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "duckdb>=1.2.1"
# ui 확장을 이미지에 미리 설치(런타임 다운로드 회피; 프런트엔드는 여전히 ui.duckdb.org 사용).
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL ui')"

WORKDIR /app
COPY serve.py /app/serve.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 4214
ENTRYPOINT ["/app/entrypoint.sh"]
