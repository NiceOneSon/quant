# Evidence.dev (BI-as-code) — data/ 의 parquet 을 DuckDB 로 읽어 차트 대시보드로 서빙.
# 컨테이너 레이아웃을 repo 와 동일하게(/app/viz/evidence + /app/data) 두어 소스 SQL 의
# 상대경로 ../../data 가 그대로 동작하게 한다.
FROM node:22-slim

WORKDIR /app/viz/evidence

# npm 레지스트리 네트워크 회복력(설치 중 idle 타임아웃 방지).
RUN npm config set fetch-timeout 600000 && npm config set fetch-retries 5

# 의존성 레이어 캐싱: lock 파일 먼저. duckdb 등 네이티브 바이너리는 이미지(linux)용으로 새로 받음.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

EXPOSE 3000
# 시작 시 소스(parquet) 재평가 후 dev 서버를 0.0.0.0:3000 에 바인딩.
CMD ["sh", "-c", "npx evidence sources && exec npx evidence dev --host 0.0.0.0 --port 3000"]
