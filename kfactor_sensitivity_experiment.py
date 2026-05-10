"""
K-factor 가중치 민감도 분석 실험 (§4.6)

McCormick 논문 연구 설계 기반:
  Case 1  Baseline       cT=0.25 cG=0.30 cM=0.25 cE=0.20
  Case 2  Geometry-heavy cT=0.20 cG=0.40 cM=0.25 cE=0.15  기하 요소 강조
  Case 3  Motion-heavy   cT=0.20 cG=0.25 cM=0.40 cE=0.15  운동 요소 강조
  Case 4  Equal          cT=0.25 cG=0.25 cM=0.25 cE=0.25  균등 가중치

분석 지표:
  - 평균 목적함수 값
  - 평균 요격률 (%)
  - 평균 풀이 시간 (s)
  - 할당 패턴 변화율 (%) : 연속 최적화 스텝 간 할당 집합이 바뀐 비율
"""

import sys, os, csv, io, contextlib
from datetime import datetime
from unittest.mock import MagicMock

for _m in ['tkinter', 'tkinter.ttk', 'tkinter.font',
           'tkinter.messagebox', 'tkinter.filedialog']:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config_mip

# ── 실험 설계 ─────────────────────────────────────────────────────────────
CONDITIONS = [
    # (이름,           cT,    cG,    cM,    cE  )
    ("Base",           0.30,  0.25,  0.25,  0.20),
    ("Time-heavy",     0.45,  0.20,  0.20,  0.15),
    ("Geo-heavy",      0.20,  0.40,  0.25,  0.15),
    ("Motion-heavy",   0.20,  0.25,  0.40,  0.15),
    ("Equal",          0.25,  0.25,  0.25,  0.25),
]

SCENARIOS    = ["SMALL_3", "MEDIUM_10", "MEDIUM_20", "STRESS_100"]
ITERATIONS   = 3
MAX_DURATION = 1600


# ── 할당 패턴 변화율 측정용 패치 ────────────────────────────────────────
def _patch_tracker(tracker):
    """_process_optimization_results 를 래핑하여 할당 스냅샷을 기록한다."""
    tracker._assignment_snapshots = []
    _orig = tracker._process_optimization_results

    def _patched(result, solve_time):
        _orig(result, solve_time)
        upper = frozenset(result.get('upper_assignments', {}).items())
        lower = frozenset(result.get('lower_assignments', {}).items())
        tracker._assignment_snapshots.append(upper | lower)

    tracker._process_optimization_results = _patched


def _assignment_change_rate(snapshots) -> float:
    if len(snapshots) < 2:
        return 0.0
    changes = sum(1 for a, b in zip(snapshots, snapshots[1:]) if a != b)
    return changes / (len(snapshots) - 1) * 100.0


# ── 단일 조건 실행 ────────────────────────────────────────────────────────
def run_one(scenario: str, weights: tuple, iterations: int) -> dict:
    from multi_missile_tracker_gui import MultiMissileTracker

    config_mip.K_FACTOR_WEIGHTS = weights
    config_mip.mip_config.scenario_type = scenario

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        tracker = MultiMissileTracker(use_mip=True, objective='MIN_DAMAGE', headless=True)
        tracker.comparison_mode = True
    _patch_tracker(tracker)

    intercept_rates, obj_finals, solve_times_avg, change_rates = [], [], [], []

    for _ in range(iterations):
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            tracker.reset_for_next_iteration()
            tracker._assignment_snapshots = []
            tracker.run_simulation(max_duration=MAX_DURATION)

        # 요격률
        stats   = tracker.stats
        total   = stats['total']
        dev     = stats.get('deviated', 0)
        actual  = max(total - dev, 1)
        ir      = min(stats['intercepted'], actual) / actual * 100
        intercept_rates.append(ir)

        # 목적함수 (마지막 유효값)
        obj_vals = [h[1] for h in tracker.optimization_history
                    if len(h) >= 2 and h[1] is not None
                    and h[1] != float('inf') and h[1] == h[1]]
        obj_finals.append(obj_vals[-1] if obj_vals else 0.0)

        # 평균 풀이 시간
        st = [h[2] for h in tracker.optimization_history if len(h) >= 3]
        solve_times_avg.append(sum(st) / len(st) if st else 0.0)

        # 할당 패턴 변화율
        change_rates.append(_assignment_change_rate(tracker._assignment_snapshots))

    n = len(intercept_rates)
    return {
        'intercept_rate': sum(intercept_rates) / n,
        'objective':      sum(obj_finals)      / n,
        'solve_time':     sum(solve_times_avg) / n,
        'change_rate':    sum(change_rates)    / n,
    }


# ── 메인 ─────────────────────────────────────────────────────────────────
def main():
    os.makedirs('performance_results', exist_ok=True)
    ts       = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = f'performance_results/kfactor_sensitivity_v2_{ts}.csv'

    rows = []
    print("=" * 72)
    print("K-factor 가중치 민감도 분석 (4조건 × 3시나리오 × 3반복)")
    print("=" * 72)

    for cond_name, ct, cg, cm, ce in CONDITIONS:
        for scenario in SCENARIOS:
            print(f"  [{cond_name:13s}] {scenario:<12} ...", end=' ', flush=True)
            res = run_one(scenario, (ct, cg, cm, ce), ITERATIONS)
            rows.append({
                'condition': cond_name, 'scenario': scenario,
                'cT': ct, 'cG': cg, 'cM': cm, 'cE': ce,
                **res,
            })
            print(f"요격률={res['intercept_rate']:.1f}%  "
                  f"obj={res['objective']:.2f}  "
                  f"solve={res['solve_time']:.4f}s  "
                  f"chg={res['change_rate']:.1f}%")

    # CSV 저장
    fields = ['condition', 'scenario', 'cT', 'cG', 'cM', 'cE',
              'intercept_rate', 'objective', 'solve_time', 'change_rate']
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n결과 저장: {csv_path}")

    # 조건별 시나리오 평균 요약
    print("\n" + "=" * 72)
    print(f"{'조건':<14} {'요격률(%)':>10} {'목적함수':>12} {'풀이시간(s)':>12} {'할당변화율(%)':>14}")
    print("-" * 68)
    for cond_name, *_ in CONDITIONS:
        rs = [r for r in rows if r['condition'] == cond_name]
        print(f"{cond_name:<14} "
              f"{sum(r['intercept_rate'] for r in rs)/len(rs):>10.1f} "
              f"{sum(r['objective']      for r in rs)/len(rs):>12.2f} "
              f"{sum(r['solve_time']     for r in rs)/len(rs):>12.4f} "
              f"{sum(r['change_rate']    for r in rs)/len(rs):>14.1f}")
    print("=" * 72)

    config_mip.K_FACTOR_WEIGHTS = (0.30, 0.25, 0.25, 0.20)  # 원복


if __name__ == '__main__':
    main()
