#!/bin/bash
# 데이터베이스 초기화 스크립트

echo "데이터베이스 초기화 중..."

psql -h localhost -U onmi -d onmi_db -f migrations/001_init_schema.sql

echo "데이터베이스 초기화 완료!"



