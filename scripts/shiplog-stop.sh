#!/usr/bin/env bash
# Encerra o servidor do Shiplog iniciado em segundo plano.
DATA="${SHIPLOG_DATA_DIR:-$HOME/.shiplog}"
PID_FILE="$DATA/shiplog.pid"
if [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Shiplog encerrado."
  rm -f "$PID_FILE"
else
  pkill -f "shiplog --no-browser" 2>/dev/null && echo "Shiplog encerrado." || echo "Shiplog não estava rodando."
fi
