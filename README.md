# quant

모듈형 퀀트 투자 시스템. 아키텍처와 개발 규칙은 `CLAUDE.md` 참고.

## 빠른 시작

```bash
# 1) 가상환경 생성 + 의존성 설치 (dev 포함)
uv sync --extra dev

# 2) 가상환경 활성화 (선택 — uv run 을 쓰면 불필요)
source .venv/bin/activate

# 3) 테스트
uv run pytest

# 4) 백테스트
uv run python scripts/backtest.py --config configs/backtest.yaml
```

## 디렉터리

- `src/data_layer` 수집·정제 (point-in-time)
- `src/research` 시그널·백테스트
- `src/portfolio` 최적화·리스크 모델
- `src/execution` 집행 (기본 dry-run)
- `src/risk` 사전 체크·모니터링
- `src/common` 설정·로깅·공통

`.env.example` 을 `.env` 로 복사해 시크릿을 채우세요 (`.env` 는 커밋 금지).

## 시각화 (DuckDB UI)

`data/` 의 parquet(유니버스·가격·금리)을 브라우저에서 SQL/차트로 탐색합니다.

```bash
docker compose up -d --build     # → http://localhost:4213
docker compose logs -f           # 뷰 생성 / 서버 로그
docker compose down              # 종료
```

- 등록되는 뷰: `prices`, `universe`, `universe_snapshots`, `rates` (각 디렉터리의 parquet).
  예) `SELECT symbol, date, close FROM prices WHERE filename LIKE '%kospi40%';`
- `data/` 는 **읽기전용** 마운트(시각화 전용). UI 노트북 상태는 named volume 에 영속.
- UI 프런트엔드는 `ui.duckdb.org` 에서 로드됩니다 — **데이터는 로컬**, 앱 셸만 원격(인터넷 필요).
- 코드/노트북에서 직접 쓰려면: `uv sync --extra viz` 후 `import duckdb`.

### Evidence.dev (코드형 BI 대시보드)

마크다운+SQL 로 차트 대시보드를 작성하는 옵션. 프로젝트는 `viz/evidence/`.

```bash
docker compose up -d --build evidence    # → http://localhost:3000
docker compose logs -f evidence          # sources 평가 / Vite 로그
docker compose down                       # 종료
```

- 데이터 소스: `viz/evidence/sources/quant/*.sql` (DuckDB `read_parquet('../../data/...')`).
- 대시보드 페이지: `viz/evidence/pages/index.md` (가격·금리·유니버스 차트). 페이지를 추가/수정해 확장.
- `data/` 를 읽기전용 마운트. 데이터 재수집 후 컨테이너 재시작하면 반영(`evidence sources` 재실행).
- 로컬 개발: `cd viz/evidence && npm install && npm run dev` (http://localhost:3000).
