#!/bin/sh
# DuckDB UI 는 IPv6 루프백(::1:4213)에 바인딩된다(외부 바인드 옵션 없음).
# socat 으로 IPv4 0.0.0.0:4214 → [::1]:4213 브리지. compose 가 host 4213 → container 4214 매핑.
set -e
python /app/serve.py &
exec socat TCP-LISTEN:4214,fork,reuseaddr TCP6:[::1]:4213
