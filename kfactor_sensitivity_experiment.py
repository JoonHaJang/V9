"""
K-factor 가중치 민감도 분석 실험
기준 가중치(c1=0.25, c2=0.30, c3=0.25, c4=0.20) 대비 각 가중치를 ±20% 변화시켜
요격률과 목적함수 값의 변동을 측정한다.
"""

import sys
import os
import csv
import time
from datetime import datetime
from unittest.mock import MagicMock

# 헤드리스 환경에서 tkinter 없이 실행 가능하도록 mock 처리
for _mod in ['tkinter', 'tkinter.ttk', 'tkinter.font',
             'tkinter.messagebox', 'tkinter.filedialog']:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# 프로젝트 루트 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_mip

BASE_WEIGHTS = (0.25, 0.30, 0.25, 0.20)  # c1, c2, c3, c4

# 9개 실험 조건: baseline + 각 가중치 ±20%
def make_conditions():
    c1, c2, c3, c4 = BASE_WEIGHTS
    return [
        ("Baseline",  c1,        c2,        c3,        c4       ),
        ("c1 +20%",   c1*1.20,   c2,        c3,        c4       ),
        ("c1 -20%",   c1*0.80,   c2,        c3,        c4       ),
        ("c2 +20%",   c1,        c2*1.20,   c3,        c4       ),
        ("c2 -20%",   c1,        c2*0.80,   c3,        c4       ),
        ("c3 +20%",   c1,        c2,        c3*1.20,   c4       ),
        ("c3 -20%",   c1,        c2,        c3*0.80,   c4       ),
        ("c4 +20%",   c1,        c2,        c3,        c4*1.20  ),
        ("c4 -20%",   c1,        c2,        c3,        c4*0.80  ),
    ]

SCENARIOS    = ["SMALL_3", "MEDIUM_10", "MEDIUM_20"]
ITERATIONS   = 3   # 조건당 반복 횟수
MAX_DURATION = 1600


def run_one(scenario: str, weights: tuple, iterations: int) -> dict:
    """단일 (시나리오, 가중치) 조합 실행 → 평균 통계 반환"""
    import io, contextlib
    from multi_missile_tracker_gui import MultiMissileTracker

    config_mip.K_FACTOR_WEIGHTS = weights
    config_mip.mip_config.scenario_type = scenario

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        tracker = MultiMissileTracker(use_mip=True, objective='MIN_DAMAGE', headless=True)
        tracker.comparison_mode = True

    intercept_rates = []
    objective_finals = []

    for i in range(iterations):
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            tracker.reset_for_next_iteration()
            tracker.run_simulation(max_duration=MAX_DURATION)

        stats = tracker.stats
        total     = stats['total']
        deviated  = stats.get('deviated', 0)
        actual    = max(total - deviated, 1)
        intercepted = min(stats['intercepted'], actual)
        intercept_rates.append(intercepted / actual * 100)

        obj_vals = [
            h[1] for h in tracker.optimization_history
            if len(h) >= 2 and h[1] is not None
            and h[1] != float('inf') and h[1] == h[1]
        ]
        objective_finals.append(obj_vals[-1] if obj_vals else 0.0)

    return {
        'intercept_rate_mean': sum(intercept_rates) / len(intercept_rates),
        'intercept_rate_std':  (sum((x - sum(intercept_rates)/len(intercept_rates))**2
                                    for x in intercept_rates) / len(intercept_rates)) ** 0.5,
        'objective_mean':      sum(objective_finals) / len(objective_finals),
    }


def main():
    os.makedirs('performance_results', exist_ok=True)
    conditions = make_conditions()
    timestamp  = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path   = f'performance_results/kfactor_sensitivity_{timestamp}.csv'

    rows = []

    # baseline 먼저 실행하여 기준값 확보
    baseline_ir  = {}  # scenario → baseline intercept_rate
    baseline_obj = {}

    print("=" * 70)
    print("K-factor 가중치 민감도 분석 실험")
    print(f"시나리오: {SCENARIOS}  |  반복: {ITERATIONS}회/조건")
    print("=" * 70)

    base_name, *base_w = conditions[0]
    for scenario in SCENARIOS:
        print(f"\n[Baseline] {scenario} ...", end=' ', flush=True)
        res = run_one(scenario, tuple(base_w), ITERATIONS)
        baseline_ir[scenario]  = res['intercept_rate_mean']
        baseline_obj[scenario] = res['objective_mean']
        rows.append({
            'condition': base_name, 'scenario': scenario,
            'c1': base_w[0], 'c2': base_w[1], 'c3': base_w[2], 'c4': base_w[3],
            'intercept_rate_mean': res['intercept_rate_mean'],
            'intercept_rate_std':  res['intercept_rate_std'],
            'objective_mean':      res['objective_mean'],
            'intercept_rate_delta': 0.0,
            'objective_delta_pct':  0.0,
        })
        print(f"요격률={res['intercept_rate_mean']:.1f}%  obj={res['objective_mean']:.4f}")

    # 나머지 8개 조건
    for cond_name, nc1, nc2, nc3, nc4 in conditions[1:]:
        for scenario in SCENARIOS:
            print(f"[{cond_name}] {scenario} ...", end=' ', flush=True)
            res = run_one(scenario, (nc1, nc2, nc3, nc4), ITERATIONS)

            delta_ir  = res['intercept_rate_mean'] - baseline_ir[scenario]
            base_obj  = baseline_obj[scenario]
            delta_obj = (abs(res['objective_mean'] - base_obj) / abs(base_obj) * 100
                         if abs(base_obj) > 1e-9 else 0.0)

            rows.append({
                'condition': cond_name, 'scenario': scenario,
                'c1': round(nc1, 4), 'c2': round(nc2, 4),
                'c3': round(nc3, 4), 'c4': round(nc4, 4),
                'intercept_rate_mean': res['intercept_rate_mean'],
                'intercept_rate_std':  res['intercept_rate_std'],
                'objective_mean':      res['objective_mean'],
                'intercept_rate_delta': delta_ir,
                'objective_delta_pct':  delta_obj,
            })
            print(f"요격률={res['intercept_rate_mean']:.1f}% "
                  f"(Δ{delta_ir:+.1f}pp)  obj_Δ={delta_obj:.2f}%")

    # CSV 저장
    fieldnames = ['condition', 'scenario', 'c1', 'c2', 'c3', 'c4',
                  'intercept_rate_mean', 'intercept_rate_std',
                  'objective_mean', 'intercept_rate_delta', 'objective_delta_pct']
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n결과 저장: {csv_path}")

    # 요약 출력
    print("\n" + "=" * 70)
    print("민감도 요약 (시나리오 평균)")
    print(f"{'조건':<12} {'요격률Δ(pp)':<14} {'목적함수Δ(%)'}")
    print("-" * 45)

    for cond_name, *_ in conditions[1:]:
        cond_rows = [r for r in rows if r['condition'] == cond_name]
        avg_ir_d  = sum(r['intercept_rate_delta'] for r in cond_rows) / len(cond_rows)
        avg_obj_d = sum(r['objective_delta_pct']  for r in cond_rows) / len(cond_rows)
        print(f"{cond_name:<12}  {avg_ir_d:+.2f}          {avg_obj_d:.2f}%")

    # 최대 편차
    all_ir_d  = [abs(r['intercept_rate_delta']) for r in rows if r['condition'] != 'Baseline']
    all_obj_d = [r['objective_delta_pct']       for r in rows if r['condition'] != 'Baseline']
    print("-" * 45)
    print(f"최대 절댓값: 요격률 ±{max(all_ir_d):.1f}pp,  목적함수 {max(all_obj_d):.1f}%")
    print("=" * 70)

    # 가중치 원복
    config_mip.K_FACTOR_WEIGHTS = BASE_WEIGHTS


if __name__ == '__main__':
    main()
