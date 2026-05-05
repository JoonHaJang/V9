# DWTA 상세 Event Flow

## 1. GUI Event Flow (전체 구조)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GUI Event Flow                                      │
│  Purpose: User interaction flow and multi-threaded simulation execution     │
│  Key: Separation of Main Thread (UI) and Simulation Thread (computation)    │
└─────────────────────────────────────────────────────────────────────────────┘

User          ControlPanel         GUI            SimThread        Tracker        Optimizer
  │                │                │                 │               │               │
  │  Click Start   │                │                 │               │               │
  ├───────────────>│                │                 │               │               │
  │                │   Update UI    │                 │               │               │
  │                ├───────────────>│                 │               │               │
  │                │  Create Thread │                 │               │               │
  │                ├────────────────┼────────────────>│               │               │
  │                │                │   Initialize    │               │               │
  │                │                │<────────────────┤               │               │
  │                │                │      Ready      │               │               │
  │                │                │<────────────────┤               │               │
  │                │                │                 │               │               │
  │                │                │   Run DWTA      │   Optimize    │   Assignments │
  │                │                │<────────────────┼──────────────>┼──────────────>│
  │                │                │  Status Update  │               │   Complete    │
  │                │                │<────────────────┤               │<──────────────┤
  │                │                │                 │ Display Status│               │
  │                │                │                 ├──────────────>│               │
  │                │                │                 │               │ Display Status│
  │                │                │                 │               ├──────────────>│
  │                │                │                 │               │               │
  │  Pause         │                │                 │               │               │
  ├───────────────>│                │                 │               │               │
  │                │                │  Set Paused     │               │               │
  │                │                ├────────────────>│               │               │
  │                │                │                 │ Change Speed  │               │
  │                │                │                 ├──────────────>│               │
  │                │                │                 │               │ Update Speed  │
  │                │                │                 │               ├──────────────>│
  │                │                │                 │               │               │
  │  Click Stop    │                │                 │               │     Stop      │
  ├───────────────>│                │                 │               │<──────────────┤
  │                │                │                 │               │      Exit     │
  │                │                │                 │               ├──────────────>│
  │                │                │                 │               │ Show Summary  │
  │                │                │                 │               ├──────────────>│

┌──────────────────────────────────────────────────────────────────────────────┐
│ Key Points:                                                                   │
│ • 4 Main Sections: Start → Main Loop → User Controls → Stop (color-coded)   │
│ • Multi-threading: Main Thread (UI) and Simulation Thread (computation)     │
│ • Main Loop: Repeats every 0.1s - DWTA optimization → Physics update → GUI  │
│ • User controls: Pause/Resume and Speed adjustment don't interrupt thread    │
│ • Thread-safe updates: All GUI updates go through ControlPanel to Main Thread│
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Run DWTA 상세 Event Flow (핵심 프로세스)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Run DWTA Detailed Event Flow                              │
│  Purpose: Complete process from assignment to interception to scenario end   │
│  Scope: T=0 (Start) → T=800 (End), including all engagement cycles          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Initialization (T=0)                                                │
└─────────────────────────────────────────────────────────────────────────────┘

start_scenario()
    │
    ├─> Load 15 threats (T01~T15)
    │   ├─> Nodong: 8 missiles (480s flight time)
    │   └─> Scud-B: 7 missiles (240s flight time)
    │
    ├─> Load 10 assets (A01~A10)
    │   └─> Values: 520~1500
    │
    ├─> Load 10 batteries
    │   ├─> LSAM: 5 batteries (20 missiles each)
    │   └─> MSAM: 5 batteries (30 missiles each)
    │
    └─> Calculate trajectories for all threats
        └─> 100 waypoints per trajectory


┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Main Simulation Loop (T=0 ~ T=800, every 5 seconds)                │
└─────────────────────────────────────────────────────────────────────────────┘

LOOP: while current_time_step < 800
    │
    ├─> [Step 2.1] run_realtime_dwta()  ◄─── DWTA 최적화
    │   │
    │   ├─> Check active threats count
    │   │   └─> If 0 threats: skip optimization
    │   │
    │   ├─> Check optimization interval (1 second)
    │   │   └─> If too soon: check reassignment needs
    │   │       ├─> If no reassignment needed: skip
    │   │       └─> If reassignment needed: continue
    │   │
    │   ├─> _prepare_optimizer_inputs()
    │   │   ├─> Collect active threats
    │   │   ├─> Collect operational batteries (ammo > 0)
    │   │   ├─> Collect assets with threats
    │   │   └─> Return: (assets_opt, systems_opt, threats_opt)
    │   │
    │   ├─> Create MIP model
    │   │   ├─> Decision variables: x_upper, x_lower
    │   │   ├─> Objective function:
    │   │   │   ├─> MIN_DAMAGE: Minimize Σ(asset_value × P_loss)
    │   │   │   └─> MAX_KILLS: Maximize Σ(P_kill)
    │   │   ├─> Constraints:
    │   │   │   ├─> Battery ammo limits
    │   │   │   ├─> **포대별 동시 교전 제한 (simultaneous_engagements)**
    │   │   │   │   └─> LSAM/MSAM: 최대 3개 표적 동시 교전
    │   │   │   ├─> Engagement feasibility (거리, 고도)
    │   │   │   ├─> Asset coverage
    │   │   │   └─> Layer coordination (upper/lower)
    │   │   └─> Solve (max 15 seconds)
    │   │
    │   └─> _process_optimization_results(result)
    │       ├─> Extract assignments
    │       │   ├─> upper_assignments: {A05_T08: LSAM_03}
    │       │   └─> lower_assignments: {A05_T08: MSAM_05}
    │       │
    │       ├─> Validate assignments
    │       │   ├─> Check threat still active
    │       │   ├─> Check battery operational
    │       │   └─> Check battery has ammo
    │       │
    │       └─> Update primary_assignments
    │           ├─> **CRITICAL: 완전히 새로운 할당으로 덮어씀!**
    │           ├─> 이전 할당은 보존되지 않음 (동적 재할당 발생)
    │           └─> {LSAM_03: T08, MSAM_05: T08}
    │
    │
    ├─> [Step 2.2] update_simulation()  ◄─── 물리 시뮬레이션
    │   │
    │   ├─> current_time_step += 5
    │   │
    │   ├─> _simulate_dynamic_events()
    │   │   └─> For each active missile:
    │   │       ├─> Check trajectory deviation (0.2% chance)
    │   │       │   └─> If deviated:
    │   │       │       ├─> Change target to EMPTY_AREA
    │   │       │       ├─> Release battery assignments
    │   │       │       ├─> Deactivate missile
    │   │       │       └─> stats['deviated'] += 1
    │   │       └─> Continue
    │   │
    │   ├─> For each missile:
    │   │   │
    │   │   ├─> Check launch time
    │   │   │   └─> If current_time >= launch_time:
    │   │   │       └─> missile['active'] = True
    │   │   │
    │   │   ├─> If active:
    │   │   │   ├─> Update flight_progress
    │   │   │   │   └─> progress = (current_time - launch_time) / flight_time
    │   │   │   │
    │   │   │   ├─> Update position
    │   │   │   │   └─> position = trajectory[progress_idx]
    │   │   │   │
    │   │   │   └─> Check engagement range (progress >= 0.60)
    │   │   │       └─> If in range: _process_impact(missile_id)
    │   │   │
    │   │   └─> Update stats['active']
    │   │
    │   └─> Update GUI status
    │
    │
    ├─> [Step 2.3] _process_impact(missile_id)  ◄─── 요격 실행
    │   │
    │   ├─> Track engagement attempts
    │   │   └─> engagement_attempts[missile_id] += 1
    │   │
    │   ├─> Find assigned batteries
    │   │   └─> assigned_batteries = [battery for battery, threat in assignments if threat == missile_id]
    │   │
    │   ├─> Check if unassigned
    │   │   └─> If no batteries assigned:
    │   │       ├─> Set needs_reassignment = True
    │   │       ├─> Roll back flight_progress (for re-engagement)
    │   │       └─> Return (wait for next DWTA)
    │   │
    │   ├─> Execute engagement
    │   │   └─> For each assigned battery:
    │   │       ├─> Check operational status
    │   │       ├─> Check ammo > 0
    │   │       │   └─> If OK:
    │   │       │       ├─> Fire missile: ammo -= 1
    │   │       │       ├─> Get Pk (intercept probability)
    │   │       │       └─> Calculate: P_survival *= (1 - Pk)
    │   │       │   └─> If NOT OK:
    │   │       │       ├─> Release assignment
    │   │       │       ├─> Set needs_reassignment = True
    │   │       │       └─> launch_failures += 1
    │   │
    │   ├─> Calculate kill probability
    │   │   └─> P_kill = 1 - P_survival
    │   │
    │   ├─> Stochastic outcome
    │   │   └─> If random() < P_kill:
    │   │       ├─> Result: INTERCEPTED ✓
    │   │       ├─> missile['active'] = False
    │   │       ├─> stats['intercepted'] += 1
    │   │       └─> kill_results[missile_id] = ('INTERCEPTED', time)
    │   │   └─> Else:
    │   │       ├─> Result: MISSED ✗
    │   │       ├─> stats['missed'] += 1
    │   │       └─> Check Shoot-Look-Shoot
    │   │           └─> If enabled AND attempts < 3:
    │   │               ├─> Keep missile active
    │   │               ├─> Roll back flight_progress -= 0.2
    │   │               ├─> Set needs_reassignment = True
    │   │               └─> Log: "Re-engagement opportunity"
    │   │           └─> Else:
    │   │               ├─> missile['active'] = False
    │   │               └─> kill_results[missile_id] = ('MISSED', time)
    │   │
    │   └─> Update statistics
    │
    │
    └─> [Step 2.4] update_display()  ◄─── GUI 업데이트
        │
        ├─> Draw main battlefield
        │   ├─> Assets (circles)
        │   ├─> Batteries (triangles)
        │   ├─> Active missiles (red dots)
        │   └─> Assignment lines (green/blue)
        │
        ├─> Draw history panel
        │   ├─> Current time
        │   ├─> Active threats
        │   ├─> Intercepted count
        │   ├─> Missed count
        │   └─> Recent events (last 15)
        │
        └─> plt.pause(0.1)


┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 3: 동적 재할당 및 Shoot-Look-Shoot 사이클                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 3-1. 포대별 동시 교전 제한 (Simultaneous Engagement Limit)                   │
└─────────────────────────────────────────────────────────────────────────────┘

시나리오: LSAM_01이 동시에 3개 표적만 교전 가능

T=200: [5개 활성 위협 존재]
    │
    ├─> 활성 위협: T01, T02, T03, T04, T05
    ├─> LSAM_01이 모두 교전 가능 (거리, 고도 조건 만족)
    │
    └─> DWTA 최적화 실행

T=200: [MIP 제약조건 적용]
    │
    ├─> 포대별 동시 교전 제한:
    │   └─> Σ(LSAM_01 할당) ≤ 3  ← **핵심 제약!**
    │
    ├─> 최적화 결과:
    │   ├─> LSAM_01 → T01 ✓ (고가치 자산)
    │   ├─> LSAM_01 → T02 ✓ (고가치 자산)
    │   ├─> LSAM_01 → T03 ✓ (고가치 자산)
    │   ├─> LSAM_01 → T04 ✗ (제한 초과, 다른 포대로)
    │   └─> LSAM_01 → T05 ✗ (제한 초과, 다른 포대로)
    │
    └─> 최종 할당:
        ├─> LSAM_01: T01, T02, T03 (3개 - 최대치)
        ├─> LSAM_02: T04 (대체 할당)
        └─> LSAM_03: T05 (대체 할당)

**의미**:
- 한 포대가 아무리 유리해도 최대 3개까지만 할당
- 나머지는 다른 포대로 분산
- 현실적인 포대 운용 능력 반영


┌─────────────────────────────────────────────────────────────────────────────┐
│ 3-2. 동적 재할당 시나리오 (Dynamic Re-assignment)                            │
└─────────────────────────────────────────────────────────────────────────────┘

시나리오 A: 포대 탄약 고갈로 인한 재할당

T=100: [초기 할당]
    │
    ├─> DWTA 최적화 실행
    ├─> 결과: T01 → LSAM_02 할당
    └─> primary_assignments = {LSAM_02: T01}

T=105: [요격 실행]
    │
    ├─> LSAM_02가 T01 요격
    ├─> 미사일 발사: ammo 20 → 18
    └─> 요격 성공 ✓

T=110: [새로운 위협 등장]
    │
    ├─> T09 발사 (Scud-B)
    └─> 활성 위협: T02, T03, T09

T=115: [DWTA 재최적화 - 동적 재할당 발생!]
    │
    ├─> 전체 위협 재평가
    ├─> LSAM_02 탄약 감소 (18발) 고려
    ├─> 새로운 최적 할당 계산
    │
    ├─> **재할당 발생:**
    │   ├─> T02: LSAM_02 → LSAM_04 변경! ✓
    │   ├─> T03: LSAM_03 → LSAM_01 변경! ✓
    │   └─> T09: 신규 → MSAM_03 할당
    │
    └─> primary_assignments = {LSAM_04: T02, LSAM_01: T03, MSAM_03: T09}
        └─> **이전 할당 완전히 덮어씀!**


시나리오 B: 포대 비작동으로 인한 긴급 재할당

T=200: [초기 할당]
    │
    ├─> T05 → LSAM_03 할당
    └─> primary_assignments = {LSAM_03: T05}

T=205: [포대 고장]
    │
    ├─> LSAM_03 상태 변경: OPERATIONAL → MALFUNCTION
    └─> available_missiles = 0

T=210: [요격 시도 실패]
    │
    ├─> _process_impact(T05) 호출
    ├─> LSAM_03 비작동 확인
    ├─> 미사일 발사 실패
    ├─> needs_reassignment = True 설정
    └─> launch_failures += 1

T=215: [긴급 재할당]
    │
    ├─> DWTA 재최적화 (needs_reassignment 감지)
    ├─> LSAM_03 제외 (비작동)
    │
    ├─> **긴급 재할당:**
    │   └─> T05: LSAM_03 → LSAM_05 변경! ✓
    │
    └─> primary_assignments = {LSAM_05: T05}


시나리오 C: 자산 가치 기반 우선순위 재조정

T=300: [초기 할당]
    │
    ├─> 활성 위협: T07 (→ A10, value=1500), T11 (→ A03, value=800)
    ├─> 할당: T07 → LSAM_01, T11 → LSAM_02
    └─> primary_assignments = {LSAM_01: T07, LSAM_02: T11}

T=305: [새로운 고가치 위협 등장]
    │
    ├─> T12 발사 (→ A01, value=1200)
    └─> 활성 위협: T07, T11, T12

T=310: [우선순위 재조정 - 동적 재할당]
    │
    ├─> DWTA 재최적화
    ├─> 자산 가치 기반 우선순위 재계산
    │   ├─> A10 (1500) - 최우선
    │   ├─> A01 (1200) - 2순위
    │   └─> A03 (800) - 3순위
    │
    ├─> **우선순위 재할당:**
    │   ├─> T07 (A10): LSAM_01 유지 ✓
    │   ├─> T12 (A01): LSAM_02 신규 할당 ✓ (고가치)
    │   └─> T11 (A03): LSAM_02 → MSAM_01 변경! ✓ (우선순위 하락)
    │
    └─> primary_assignments = {LSAM_01: T07, LSAM_02: T12, MSAM_01: T11}
        └─> **T11의 할당이 LSAM → MSAM으로 변경됨!**


┌─────────────────────────────────────────────────────────────────────────────┐
│ 3-3. Shoot-Look-Shoot Re-engagement Cycle (위협별 재교전 제한)               │
└─────────────────────────────────────────────────────────────────────────────┘

Example: T08 engagement with 3 attempts (각 시도마다 다른 포대 할당)

**핵심**: engagement_attempts[T08] ≤ 3 (위협별 제한)

T=375: [Attempt 1 - 초기 할당]
    │
    ├─> DWTA assigns: LSAM_03, MSAM_05 → T08
    ├─> primary_assignments = {LSAM_03: T08, MSAM_05: T08}
    │
    ├─> T08 reaches 60% flight progress
    ├─> _process_impact(T08)
    │   ├─> Fire 2 missiles (LSAM_03, MSAM_05)
    │   ├─> P_kill = 0.9996
    │   └─> Random outcome: MISSED ✗
    │
    ├─> Shoot-Look-Shoot triggered
    │   ├─> engagement_attempts[T08] = 1 < 3 ✓
    │   ├─> Keep T08 active
    │   ├─> Roll back: flight_progress = 0.40
    │   └─> Set needs_reassignment = True
    │
    └─> Wait for next DWTA cycle...

T=380: [Attempt 2 - 동적 재할당!]
    │
    ├─> DWTA re-optimization (needs_reassignment 감지)
    ├─> **재할당 발생: LSAM_01, MSAM_02 → T08** ✓
    ├─> primary_assignments = {LSAM_01: T08, MSAM_02: T08}
    │   └─> **이전 할당 (LSAM_03, MSAM_05) 완전히 교체됨!**
    │
    ├─> T08 reaches 60% flight progress again
    ├─> _process_impact(T08)
    │   ├─> Fire 2 missiles (LSAM_01, MSAM_02)
    │   ├─> P_kill = 0.9996
    │   └─> Random outcome: MISSED ✗
    │
    ├─> Shoot-Look-Shoot triggered
    │   ├─> engagement_attempts[T08] = 2 < 3 ✓
    │   ├─> Keep T08 active
    │   ├─> Roll back: flight_progress = 0.40
    │   └─> Set needs_reassignment = True
    │
    └─> Wait for next DWTA cycle...

T=385: [Attempt 3 - 최종 재할당]
    │
    ├─> DWTA re-optimization (needs_reassignment 감지)
    ├─> **재할당 발생: LSAM_04, MSAM_03 → T08** ✓
    ├─> primary_assignments = {LSAM_04: T08, MSAM_03: T08}
    │   └─> **또 다시 다른 포대로 교체됨! (3번째 조합)**
    │
    ├─> T08 reaches 60% flight progress again
    ├─> _process_impact(T08)
    │   ├─> Fire 2 missiles (LSAM_04, MSAM_03)
    │   ├─> P_kill = 0.9996
    │   └─> Random outcome: INTERCEPTED ✓
    │
    ├─> Success!
    │   ├─> missile['active'] = False
    │   ├─> stats['intercepted'] += 1
    │   └─> kill_results[T08] = ('INTERCEPTED', 385)
    │
    └─> T08 removed from simulation


┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Scenario Termination (T=800 or all threats resolved)                │
└─────────────────────────────────────────────────────────────────────────────┘

Check termination conditions:
    │
    ├─> Condition 1: Time limit reached
    │   └─> current_time_step >= 800
    │
    ├─> Condition 2: All threats resolved
    │   └─> active_threats == 0 AND no pending launches
    │
    └─> If termination condition met:
        │
        ├─> Calculate final statistics
        │   ├─> Total threats: 15
        │   ├─> Intercepted: 13
        │   ├─> Missed: 1
        │   ├─> Deviated: 1
        │   ├─> Success rate: 86.7%
        │   └─> Total engagements: 45
        │
        ├─> Display summary
        │   ├─> Print to console
        │   └─> Show in GUI
        │
        ├─> Save results (optional)
        │   ├─> Optimization history
        │   ├─> Engagement log
        │   └─> Final statistics
        │
        └─> Exit simulation
            └─> Close GUI window


┌─────────────────────────────────────────────────────────────────────────────┐
│ Key Metrics Tracked Throughout Simulation                                    │
└─────────────────────────────────────────────────────────────────────────────┘

stats = {
    'total': 15,              # Total threats
    'active': 0~15,           # Currently active threats (dynamic)
    'intercepted': 0~15,      # Successfully intercepted
    'missed': 0~15,           # Failed interceptions
    'deviated': 0~2,          # Trajectory deviations
    'retargeted': 0~5,        # Re-assignments
    'launch_failures': 0~10   # Battery launch failures
}

optimization_history = [
    (time_step, objective_value, solve_time),
    (0, 2.45, 0.8),
    (5, 2.31, 0.7),
    ...
]

engagement_attempts = {
    'T01': 1,  # Single attempt, success
    'T08': 3,  # Three attempts (Shoot-Look-Shoot)
    ...
}

kill_results = {
    'T01': ('INTERCEPTED', 480),
    'T08': ('INTERCEPTED', 385),
    'T15': ('MISSED', 450),
    ...
}


┌─────────────────────────────────────────────────────────────────────────────┐
│ Timeline Example: Complete Scenario (T=0 ~ T=800)                            │
└─────────────────────────────────────────────────────────────────────────────┘

T=0     : Initialize scenario (15 threats, 10 batteries, 10 assets)
T=0     : T01 launched (Nodong, target A01, 480s flight)
T=15    : T02 launched (Nodong, target A02, 465s flight)
T=30    : T03 launched (Nodong, target A04, 450s flight)
...
T=210   : T15 launched (Scud-B, target A08, 240s flight) - All threats launched

T=288   : T01 reaches 60% progress → DWTA assigns LSAM_01 → Engagement → INTERCEPTED ✓
T=300   : T02 reaches 60% progress → DWTA assigns LSAM_02 → Engagement → INTERCEPTED ✓
T=310   : T03 reaches 60% progress → DWTA assigns LSAM_03 → Engagement → MISSED ✗
          └─> Shoot-Look-Shoot: Re-engage T03
T=315   : T03 re-engagement → DWTA assigns LSAM_04 → Engagement → INTERCEPTED ✓

T=360   : T09 reaches 60% progress → DWTA assigns MSAM_01 → Engagement → INTERCEPTED ✓
T=375   : T10 reaches 60% progress → Trajectory deviation → Target changed to EMPTY_AREA
T=390   : T11 reaches 60% progress → DWTA assigns MSAM_02 → Engagement → INTERCEPTED ✓

...

T=565   : Last missile (T07) reaches target
          └─> All threats resolved: 13 intercepted, 1 missed, 1 deviated

T=800   : Simulation time limit reached → Display final summary → Exit


┌─────────────────────────────────────────────────────────────────────────────┐
│ Summary: Complete DWTA Event Flow                                            │
└─────────────────────────────────────────────────────────────────────────────┘

1. Initialization (T=0)
   └─> Load scenario, calculate trajectories

2. Main Loop (T=0~800, every 5s)
   ├─> Run DWTA optimization (every 1s or on reassignment)
   │   └─> **동적 재할당: primary_assignments 완전히 새로 덮어씀**
   ├─> Update physics (missile positions, activations)
   ├─> Process impacts (engagement execution)
   └─> Update GUI display

3. 동적 재할당 (Dynamic Re-assignment)
   ├─> 탄약 고갈: 포대 탄약 감소 시 다른 포대로 재할당
   ├─> 포대 고장: 비작동 포대 제외, 긴급 재할당
   ├─> 우선순위 변경: 자산 가치 기반 재조정
   └─> 매 최적화마다 전체 할당 재계산

4. Shoot-Look-Shoot (on engagement failure)
   ├─> Keep missile active
   ├─> Roll back flight progress
   ├─> Trigger re-optimization
   ├─> **동적 재할당: 매 시도마다 다른 포대 조합**
   └─> Re-engage (max 3 attempts per threat)

5. Termination (T=800 or all resolved)
   ├─> Calculate statistics
   ├─> Display summary
   └─> Exit

Key Features:
• Real-time optimization every 1 second
• **포대별 동시 교전 제한 (Simultaneous Engagement Limit)**
  - LSAM: 최대 3개 표적 동시 교전
  - MSAM: 최대 3개 표적 동시 교전
  - MIP 제약조건으로 적용: Σ(할당) ≤ 3 per battery
• **Dynamic re-assignment: 매 최적화마다 전체 할당 재계산**
  - 탄약 고갈, 포대 고장, 우선순위 변경 시 자동 재할당
  - primary_assignments 완전히 새로 덮어씀 (이전 할당 보존 안 됨)
  - 예: T01이 LSAM_02 → LSAM_04로 변경 가능
• **Shoot-Look-Shoot strategy (위협별 제한)**
  - 한 위협당 최대 3회 재교전 (engagement_attempts[threat_id] ≤ 3)
  - 각 시도마다 다른 포대 조합으로 재할당 가능
  - 포대별 제한과는 별개 (위협별 vs 포대별)
• Trajectory deviation simulation (0.2% probability)
• Multi-layer defense (LSAM upper + MSAM lower)
• Comprehensive statistics tracking
