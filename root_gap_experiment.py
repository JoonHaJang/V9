#!/usr/bin/env python3
"""
Root Node Gap 측정 실험 (Rolling Horizon 전 구간)

측정 방식:
  - 경량 롤링 호라이즌 루프를 직접 구현 (매 OPT_INTERVAL 초마다 MILP 풀이)
  - 각 최적화 단계에서 Root Node Gap 측정
  - 시나리오 시작~종료 전 구간의 gap을 수집하여 평균/최대 보고

Root Node Gap = |Z* - Z_LP_root| / (|Z*| + ε) × 100%
"""
import sys, statistics
sys.path.insert(0, '/home/user/V9')

from config_mip import mip_config
from nonlinear_mip_optimizer import NonLinearMIPOptimizer, Asset, InterceptorSystem, Threat
from scenario_dwta_balanced import ScenarioManager

# ── 설정 ─────────────────────────────────────────────────────────────────────
SCENARIOS = [
    ("SMALL3",     "SMALL_3"),
    ("SMALL5",     "SMALL_5"),
    ("SMALL8",     "SMALL_8"),
    ("MEDIUM10",   "MEDIUM_10"),
    ("BASELINE15", "BASELINE_15"),
    ("MEDIUM20",   "MEDIUM_20"),
    ("LARGE40",    "LARGE_40"),
    ("STRESS100",  "STRESS_100"),
]

N_RUNS        = 35   # 시나리오당 독립 반복 횟수 (30구간 × 35회 ≈ 1,000 샘플, MC 1,000회와 통일)
N_SAMPLES     = 30   # 시나리오 전체 기간을 N등분하여 각 구간 중간에서 gap 측정
MAX_DURATION  = 700  # 시뮬레이션 최대 지속 시간 (초)


# ── 경량 롤링 호라이즌 루프 ────────────────────────────────────────────────────
def build_optimizer_inputs(scenario_data, current_time, intercepted_ids):
    """현재 시점의 활성 위협 + 포대 상태로 optimizer 입력 구성"""
    assets_raw    = scenario_data.get('assets', [])
    batteries_raw = scenario_data.get('batteries', [])
    threats_raw   = scenario_data.get('threats', [])

    assets = [
        Asset(id=a['id'], position=tuple(a.get('position', (0, 0))),
              value=a.get('value', 1.0), priority=a.get('priority', 1),
              estimated_threat_missiles=[])
        for a in assets_raw
    ]

    systems = []
    for b in batteries_raw:
        ammo = b.get('available_missiles', 0)
        if ammo <= 0:
            continue
        specs = b.get('specs', {}).get('ballistic_missile_specs', {})
        pk    = specs.get('intercept_probability_single') or specs.get('intercept_probability', 0.85)
        rng   = specs.get('engagement_range_km', {}).get('max', 200.0)
        simul = b.get('specs', {}).get('battery_config', {}).get('simultaneous_engagements', 3)
        systems.append(InterceptorSystem(
            id=b['id'], system_type=b.get('system_type', 'LSAM'),
            position=tuple(b.get('position', (0, 0))),
            available_missiles=ammo,
            max_missiles_per_target=min(simul, ammo),
            intercept_probability=pk, engagement_range=rng,
        ))

    active_threats = []
    for t in threats_raw:
        tid = t.get('id') or t.get('name', '')
        if tid in intercepted_ids:
            continue
        launch_t = t.get('launch_time', 0.0)
        flight_t = t.get('flight_time', 300.0)
        if launch_t > current_time:
            continue  # 아직 발사 전
        elapsed = current_time - launch_t
        progress = min(elapsed / flight_t, 1.0)
        if progress >= 1.0:
            continue  # 이미 도달 (미요격)
        remaining = flight_t - elapsed

        lp = t.get('launch_position', [0, 0])
        alt = 30000.0 * (1.0 - progress)  # 단순 고도 근사
        active_threats.append(Threat(
            id=tid,
            target_asset_id=t.get('target_asset_id') or t.get('target_asset', ''),
            current_position=(float(lp[0]), float(lp[1]), alt),
            estimated_impact_time=remaining,
            launch_position=tuple(lp),
            flight_time=flight_t,
            specs=t.get('specs', {}),
            launch_time=launch_t,
            trajectory_type=t.get('trajectory_type', 'BALLISTIC'),
            rcs=t.get('rcs', 0.1),
        ))

    return assets, systems, active_threats, batteries_raw


def run_one_rolling(scenario_data):
    """시나리오 1회 롤링 호라이즌 → 각 최적화 단계의 gap 목록 반환"""
    # 포대 미사일 재고 초기화
    batteries = []
    for b in scenario_data.get('batteries', []):
        b = dict(b)
        try:
            b['available_missiles'] = b['specs']['battery_config']['total_missiles']
        except (KeyError, TypeError):
            b['available_missiles'] = 20
        batteries.append(b)

    sd = dict(scenario_data)
    sd['batteries'] = batteries

    threats_raw = sd.get('threats', [])
    assets_raw  = sd.get('assets', [])
    intercepted = set()
    max_flight  = max((t.get('launch_time', 0) + t.get('flight_time', 300)
                       for t in threats_raw), default=MAX_DURATION)
    end_time    = min(max_flight, MAX_DURATION)

    # 시나리오 실제 위협·포대 정보로 engagement matrix 생성 (시나리오별 1회)
    import io, contextlib as _ctx
    from config_mip import EngagementZoneConfig
    shared_matrix = {}
    with _ctx.redirect_stdout(io.StringIO()):
        for bat in batteries:
            for thr in threats_raw:
                key = (bat['id'], thr.get('id', ''))
                try:
                    result_eng = EngagementZoneConfig.can_engage_trajectory(
                        bat, thr, assets_raw)
                    shared_matrix[key] = result_eng.get('can_engage', False)
                except Exception:
                    shared_matrix[key] = False

    # 시나리오 기간을 N_SAMPLES 등분하여 샘플 시점 선택
    first_launch = min((t.get('launch_time', 0) for t in threats_raw), default=0)
    sample_times = [
        first_launch + (end_time - first_launch) * i / (N_SAMPLES - 1)
        for i in range(N_SAMPLES)
    ]

    step_gaps = []

    for t in sample_times:
        assets, systems, active, batteries_now = build_optimizer_inputs(sd, float(t), intercepted)
        if not active or not systems:
            continue

        opt = NonLinearMIPOptimizer(mip_config)
        opt.capture_root_gap = True
        opt.use_warm_start   = False
        opt.engagement_matrix = shared_matrix  # 재사용

        try:
            opt.create_model(assets=assets, interceptor_systems=systems,
                             threats=active, batteries=batteries_now,
                             engagement_matrix=shared_matrix, current_time=float(t))
            result = opt.solve()
        except Exception:
            continue

        if not result or not result.get('feasible'):
            continue

        gap = result.get('root_node_gap_pct')
        if gap is not None:
            step_gaps.append({
                'gap_pct':    gap,
                'n_vars':     result.get('diagnosis', {}).get('num_variables', 0),
                'n_cons':     result.get('diagnosis', {}).get('num_constraints', 0),
                'solve_time': result.get('solve_time', 0.0),
                'n_active':   len(active),
                't':          t,
            })

        # 이 타임스텝에서 할당된 위협을 요격으로 간주 (단순화)
        for k in (result.get('upper_assignments') or {}).values():
            intercepted.add(k)
        for k in (result.get('lower_assignments') or {}).values():
            intercepted.add(k)

    return step_gaps


# ── 메인 실험 루프 ────────────────────────────────────────────────────────────
def main():
    print("=" * 72)
    print("Root Node Gap 실험 (Rolling Horizon 전 구간)")
    print(f"시나리오당 {N_RUNS}회 반복, 전체 기간 {N_SAMPLES}구간 균등 샘플링, gapRel=1%")
    print("=" * 72)

    rows = []
    for label, key in SCENARIOS:
        all_gaps  = []
        all_times = []
        all_vars  = []
        all_cons  = []
        valid_runs = 0

        print(f"\n[{label}]", end='', flush=True)
        import time as _time; t0 = _time.time()

        for _ in range(N_RUNS):
            # 시나리오 생성 (sys.stdout 억제)
            import io, contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                sd = ScenarioManager.create_scenario(key)

            step_gaps = run_one_rolling(sd)
            if not step_gaps:
                print('x', end='', flush=True)
                continue
            valid_runs += 1
            for s in step_gaps:
                all_gaps.append(s['gap_pct'])
                all_times.append(s['solve_time'])
                all_vars.append(s['n_vars'])
                all_cons.append(s['n_cons'])
            print('.', end='', flush=True)

        elapsed = _time.time() - t0
        total_samples = len(all_gaps)
        print(f" ({valid_runs}/{N_RUNS} runs, {total_samples} samples, {elapsed:.1f}s)")

        avg_gap  = statistics.mean(all_gaps)  if all_gaps  else float('nan')
        max_gap  = max(all_gaps)              if all_gaps  else float('nan')
        avg_time = statistics.mean(all_times) if all_times else float('nan')
        avg_vars = statistics.mean(all_vars)  if all_vars  else 0
        avg_cons = statistics.mean(all_cons)  if all_cons  else 0

        rows.append((label, valid_runs, total_samples, avg_vars, avg_cons,
                     avg_gap, max_gap, avg_time))
        print(f"  avg gap={avg_gap:.4f}%, max gap={max_gap:.4f}%")

    # ── 결과 출력 ─────────────────────────────────────────────────────────────
    print("\n")
    print("=" * 90)
    print(f"{'Scenario':<12} {'Runs':>5} {'Samples':>8} {'Avg.Vars':>9} {'Avg.Cons':>9}"
          f" {'Avg Gap(%)':>11} {'Max Gap(%)':>11} {'Avg Time(s)':>12}")
    print("-" * 90)
    for label, runs, samp, avg_v, avg_c, avg_g, max_g, avg_t in rows:
        print(f"{label:<12} {runs:>5} {samp:>8} {avg_v:>9.0f} {avg_c:>9.0f}"
              f" {avg_g:>11.4f} {max_g:>11.4f} {avg_t:>12.3f}")
    print("=" * 90)

    # ── CSV 저장 ──────────────────────────────────────────────────────────────
    import csv
    csv_path = '/home/user/V9/root_gap_results.csv'
    with open(csv_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Scenario', 'ValidRuns', 'TotalSamples', 'AvgVars', 'AvgCons',
                    'AvgGapPct', 'MaxGapPct', 'AvgTimeSec'])
        for row in rows:
            w.writerow([f"{v:.4f}" if isinstance(v, float) else v for v in row])
    print(f"\n결과 저장: {csv_path}")


if __name__ == '__main__':
    main()
