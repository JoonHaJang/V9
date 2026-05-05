# 논문 실험 결과 폴더

## 폴더 구조
```
paper_results/
├── exp1_scalability/     실험1: 위협 규모별 성능 프로파일 (5~100발)
├── exp2_warmstart/       실험2: Warm-start ON/OFF 비교 (BASELINE_15, DWTA_BALANCED)
└── exp3_battery_scale/   실험3: Stress-100 포대 규모 변형 (15/30/50포대)
```

## 실행 명령어 (각 폴더에서 실행 후 결과를 해당 폴더로 이동)

### 실험 1: 규모별 성능 프로파일 (10포대 고정, 3회 반복)
```
cd c:\Users\USER\Desktop\V9

python multi_missile_tracker_gui.py --compare SMALL_5      --iterations 3 MIP
python multi_missile_tracker_gui.py --compare MEDIUM_10    --iterations 3 MIP
python multi_missile_tracker_gui.py --compare BASELINE_15  --iterations 3 MIP
python multi_missile_tracker_gui.py --compare MEDIUM_20    --iterations 3 MIP
python multi_missile_tracker_gui.py --compare HEAVY_30     --iterations 3 MIP
python multi_missile_tracker_gui.py --compare LARGE_40     --iterations 3 MIP
python multi_missile_tracker_gui.py --compare STRESS_100   --iterations 3 MIP
```
→ 완료 후 `performance_results/comparison_summary_*.csv` 를 `exp1_scalability/` 로 이동

### 실험 2: Warm-start 효과 (3회 반복)
```
python multi_missile_tracker_gui.py --compare BASELINE_15  --iterations 3 MIP
python multi_missile_tracker_gui.py --compare DWTA_BALANCED --iterations 3 MIP
```
→ `stress_test_BASELINE_15_MIP_*.json` 및 `stress_test_DWTA_BALANCED_MIP_*.json` 을 `exp2_warmstart/` 로 이동
→ Warm-start 통계는 JSON 내 `solver_performance.warmstart_rate_pct` 확인

### 실험 3: Stress-100 포대 규모 변형 (3회 반복)
```
python multi_missile_tracker_gui.py --compare STRESS_100        --iterations 3 MIP
python multi_missile_tracker_gui.py --compare STRESS_100_BAT15  --iterations 3 MIP
python multi_missile_tracker_gui.py --compare STRESS_100_BAT30  --iterations 3 MIP
python multi_missile_tracker_gui.py --compare STRESS_100_BAT50  --iterations 3 MIP
```
→ 결과 JSON + CSV 를 `exp3_battery_scale/` 로 이동

## 논문 테이블에 필요한 지표 (JSON 키 기준)

| 논문 지표 | JSON 경로 |
|-----------|-----------|
| 평균 solver time | `solver_performance.avg_time_sec` |
| 최대 solver time | `solver_performance.max_time_sec` |
| Timeout율 | `solver_performance.timeout_rate_pct` |
| Warm-start율 | `solver_performance.warmstart_rate_pct` |
| 변수 수 (평균) | `problem_scale.avg_variables` |
| 제약 수 (평균) | `problem_scale.avg_constraints` |
| 요격율 | `simulation_result.intercept_rate_pct` |
| 상층/하층 요격 | `simulation_result.upper_intercepts` / `lower_intercepts` |
| 자산 보호율 | `simulation_result.assets_protected` / `total_assets` |
