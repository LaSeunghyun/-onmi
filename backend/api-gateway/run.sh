#!/bin/bash
# API Gateway 실행 스크립트

export PYTHONPATH="${PYTHONPATH}:$(pwd)/../shared"

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000









