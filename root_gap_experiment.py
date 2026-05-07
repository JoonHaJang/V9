#!/usr/bin/env python3
"""
Root Node Gap 측정 실험
McCormick 선형화의 LP 완화 품질을 정량적으로 측정한다.

Root Node Gap = |Z_LP_root - Z*_integer| / |Z*_integer| × 100%

논문 Table 추가용: 8개 시나리오 × 30회 반복 → 평균/최대 gap 보고
"""
import sys, time, statistics
sys.path.insert(0, '/home/user/V9')

from config_mip import mip_config
from nonlinear_mip_optimizer import NonLinearMIPOptimizer, Asset, InterceptorSystem, Threat
from scenario_dwta_balanced import ScenarioManager

# ── 시나리오 정의 (논문 Table 4와 동일) ────────────────────────────────────
SCENARIOS = [
    ("SMALL3",    "SMALL_3"),
    ("SMALL5",    "SMALL_5"),
    ("SMALL8",    "SMALL_8"),
    ("MEDIUM10",  "MEDIUM_10"),
    ("BASELINE15","BASELINE_15"),
    ("MEDIUM20",  "MEDIUM_20"),
    ("LARGE40",   "LARGE_40"),
    ("STRESS100", "STRESS_100"),
]

N_RUNS = 30   # 시나리오당 반복 횟수

def build_optimizer_inputs(scenario_data):
    """시나리오 dict → optimizer 입력 객체 변환"""
    assets_raw    = scenario_data.get('assets', [])
    batteries_raw = scenario_data.get('batteries', [])
    threats_raw   = scenario_data.get('threats', [])

    # Asset 객체
    assets = [
        Asset(id=a['id'], position=tuple(a.get('position', (0,0))),
              value=a.get('value', 1.0), priority=a.get('priority', 1),
              estimated_threat_missiles=[])
        for a in assets_raw
    ]

    # Battery 초기화
    for b in batteries_raw:
        if 'available_missiles' not in b:
            try:
                b['available_missiles'] = b['specs']['battery_config']['total_missiles']
            except (KeyError, TypeError):
                b['available_missiles'] = 20
        b.setdefault('status', 'OPERATIONAL')
        b.setdefault('position', (0.0, 0.0))

    # InterceptorSystem 객체
    systems = []
    for b in batteries_raw:
        if b.get('available_missiles', 0) <= 0:
            continue
        try:
            specs = b['specs']['ballistic_missile_specs']
            pk    = specs['intercept_probability']
            rng   = specs['engagement_range_km']['max']
            simul = b['specs']['battery_config'].get('simultaneous_engagements', 3)
        except (KeyError, TypeError):
            pk, rng, simul = 0.85, 200.0, 3
        systems.append(InterceptorSystem(
            id=b['id'], system_type=b.get('system_type','LSAM'),
            position=tuple(b.get('position',(0,0))),
            available_missiles=b['available_missiles'],
            max_missiles_per_target=min(simul, b['available_missiles']),
            intercept_probability=pk, engagement_range=rng
        ))

    # Threat 객체
    threats = [
        Threat(
            id=t['id'],
            target_asset_id=t.get('target_asset') or t.get('target_asset_id',''),
            current_position=(t.get('position',[0,0])[0],
                              t.get('position',[0,0])[1],
                              t.get('altitude', 30000.0)),
            estimated_impact_time=t.get('flight_time', 200.0),
            launch_position=tuple(t.get('launch_position',(0,0))),
            flight_time=t.get('flight_time', 200.0),
            specs=t.get('specs', {}),
            launch_time=t.get('launch_time', 0.0),
            trajectory_type=t.get('trajectory_type','BALLISTIC'),
            rcs=t.get('rcs', 0.1)
        )
        for t in threats_raw
    ]
    return assets, systems, threats, batteries_raw


def run_one(scenario_key, capture_gap=True):
    """시나리오 1회 최적화 → (gap_pct, z_lp, z_star, solve_time, n_vars, n_cons) 반환"""
    sd = ScenarioManager.create_scenario(scenario_key)
    assets, systems, threats, batteries = build_optimizer_inputs(sd)

    if not assets or not systems or not threats:
        return None

    opt = NonLinearMIPOptimizer(mip_config)
    opt.capture_root_gap = capture_gap
    opt.use_warm_start = False      # 재현성을 위해 warm-start 비활성화

    try:
        opt.create_model(assets=assets, interceptor_systems=systems,
                         threats=threats, batteries=batteries,
                         engagement_matrix=None, current_time=0.0)
        result = opt.solve()
    except Exception as e:
        return None

    if not result or not result.get('feasible'):
        return None

    gap   = result.get('root_node_gap_pct')
    z_lp  = result.get('z_lp_root')
    z_star= result.get('objective_value')
    t_sec = result.get('solve_time', 0.0)
    n_var = result['diagnosis'].get('num_variables', 0)
    n_con = result['diagnosis'].get('num_constraints', 0)
    return gap, z_lp, z_star, t_sec, n_var, n_con


def main():
    print("=" * 72)
    print("Root Node Gap 실험 (McCormick 선형화 품질 측정)")
    print(f"시나리오당 {N_RUNS}회 반복")
    print("=" * 72)

    rows = []
    for label, key in SCENARIOS:
        gaps, times, n_vars, n_cons = [], [], [], []
        valid = 0
        print(f"\n[{label}] 시나리오 실행 중 ...", end='', flush=True)

        for _ in range(N_RUNS):
            res = run_one(key, capture_gap=True)
            if res is None:
                continue
            gap, z_lp, z_star, t_sec, nv, nc = res
            valid += 1
            times.append(t_sec)
            n_vars.append(nv)
            n_cons.append(nc)
            if gap is not None:
                gaps.append(gap)
            print('.', end='', flush=True)

        print(f" ({valid}/{N_RUNS})", end='')

        # 통계
        avg_gap  = statistics.mean(gaps)  if gaps  else float('nan')
        max_gap  = max(gaps)              if gaps  else float('nan')
        avg_time = statistics.mean(times) if times else float('nan')
        avg_vars = statistics.mean(n_vars) if n_vars else 0
        avg_cons = statistics.mean(n_cons) if n_cons else 0

        rows.append((label, valid, avg_vars, avg_cons, avg_gap, max_gap, avg_time))
        print(f"  → avg gap={avg_gap:.2f}%, max gap={max_gap:.2f}%")

    # 결과 테이블 출력
    print("\n")
    print("=" * 80)
    print(f"{'Scenario':<12} {'Valid':>5} {'Avg.Vars':>9} {'Avg.Cons':>9} "
          f"{'Avg Gap(%)':>10} {'Max Gap(%)':>10} {'Avg Time(s)':>12}")
    print("-" * 80)
    for label, valid, avg_vars, avg_cons, avg_gap, max_gap, avg_time in rows:
        print(f"{label:<12} {valid:>5} {avg_vars:>9.0f} {avg_cons:>9.0f} "
              f"{avg_gap:>10.3f} {max_gap:>10.3f} {avg_time:>12.3f}")
    print("=" * 80)

    # CSV 저장
    import csv
    csv_path = '/home/user/V9/root_gap_results.csv'
    with open(csv_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Scenario','ValidRuns','AvgVars','AvgCons',
                    'AvgGapPct','MaxGapPct','AvgTimeSec'])
        for row in rows:
            w.writerow([f"{v:.4f}" if isinstance(v, float) else v for v in row])
    print(f"\n결과 저장: {csv_path}")


if __name__ == '__main__':
    main()
