#!/usr/bin/env python3
"""
몬테카를로 시뮬레이션 테스트 스크립트
5회 실행으로 빠르게 테스트
"""

import subprocess
import sys

print("=" * 60)
print("몬테카를로 시뮬레이션 테스트 (5회)")
print("=" * 60)
print()

# 5회 실행
result = subprocess.run([
    sys.executable,
    "monte_carlo_cli_fixed.py",
    "--runs", "5",
    "--output", "monte_carlo_test_5runs.json"
], cwd=r"c:\Users\USER\Desktop\Paper_DWTA_2025_12_08-20251212T221250Z-3-001\Paper_DWTA_2025_12_08")

print()
print("=" * 60)
print("테스트 완료!")
print("결과 파일: monte_carlo_test_5runs.json")
print("=" * 60)
