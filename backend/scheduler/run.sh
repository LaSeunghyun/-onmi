#!/bin/bash
# Scheduler 실행 스크립트

export PYTHONPATH="${PYTHONPATH}:$(pwd)/../shared:$(pwd)/../ingestor/src:$(pwd)/../nlp-service/src"

python src/scheduler.py




