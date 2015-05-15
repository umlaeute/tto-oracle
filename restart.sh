#!/bin/sh

cd "${0%/*}"
TIMESTAMP=$(date +%Y%m%d-%H%M)

loop() {
mkdir -p prophecies
while true; do
  echo "starting The Tech Oracle @ $(date)"
  ./OracleServer.py texts/*.txt 2>&1
  sleep 1
done
}

mkdir -p logs

export PYTHONUNBUFFERED=1
loop | tee "logs/Oracle-${TIMESTAMP}.log" 

