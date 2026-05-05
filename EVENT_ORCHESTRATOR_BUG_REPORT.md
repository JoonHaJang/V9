# 🚨 Event-driven Orchestrator 미통합 버그 보고서

**발견일:** 2026-02-06
**심각도:** 🔴 **HIGH** - 자원 활용 비효율
**상태:** 🔴 미통합 (설계만 완료)

---

## 📋 문제 요약

**증상:**
- 각 배터리의 할당량(3개)을 100% 사용하지 못함
- 미할당 위협 61개가 있는데도 재할당이 안 됨
- 용량 확보 로그는 나오지만 실제 재할당은 안 됨

**근본 원인:**
- Event-driven Orchestrator 설계는 완료했지만 **실제로 통합하지 않음**
- `dwta_orchestration_fix.py` 파일만 생성하고 `multi_missile_tracker_gui.py`에 적용 안 함

---

## 🔍 현재 상태 분석

### 문제 로그 분석

```
[16:57:25] [INFO] [T=220] 미할당 위협 61개에 대해 재할당 플래그 설정
→ needs_reassignment 플래그는 설정됨
→ 하지만 최적화가 실행 안 됨!

[16:58:13] INFO: T52 reassignment completed - flag cleared
[16:58:13] INFO: T53 reassignment completed - flag cleared
→ 나중에 일부만 할당됨 (61개 중 2개만!)
```

### 현재 코드 문제점

#### 1️⃣ capacity_freed 플래그 즉시 리셋
**파일:** `multi_missile_tracker_gui.py:1859-1862`

```python
# 🆕 용량 확보 시 즉시 최적화 실행
if getattr(self, 'capacity_freed', False):
    self.capacity_freed = False  # ⚠️ 즉시 리셋!
    if self.control_panel:
        self.control_panel.log_message(f"[INFO] [T={self.current_time_step}] 용량 확보 감지 - 즉시 최적화 실행", "INFO")
```

**문제:**
- 플래그를 체크하자마자 False로 리셋
- optimization_interval 체크 전에 리셋됨
- 실제 최적화가 실행 안 되고 플래그만 클리어

#### 2️⃣ needs_reassignment 플래그만 의존
**파일:** `multi_missile_tracker_gui.py:1864-1877`

```python
else:
    # Check for missiles needing reassignment
    missiles_needing_reassignment = []
    for missile_id, missile in self.missiles.items():
        if missile['active'] and missile.get('needs_reassignment', False):
            missiles_needing_reassignment.append(missile_id)

    # Skip optimization if no missiles need reassignment
    if not missiles_needing_reassignment:
        return  # ⚠️ 여기서 리턴!
    else:
        # Log reassignment need
        if self.control_panel:
            self.control_panel.log_message(f"Missiles needing reassignment: {', '.join(missiles_needing_reassignment)} - Running optimization")
```

**문제:**
- needs_reassignment 플래그가 있는 미사일만 체크
- **슬롯이 확보되었는지는 체크하지 않음**
- 미할당 위협이 있어도 플래그가 없으면 최적화 안 함

#### 3️⃣ Orchestrator 미통합
**확인:** `multi_missile_tracker_gui.py`에서 검색

```bash
# dwta_orchestrator 검색 결과: 0건
# DWTAOrchestrator 검색 결과: 0건
# on_capacity_freed 검색 결과: 0건
```

**문제:**
- `dwta_orchestration_fix.py`만 만들고 실제 통합 안 함
- Event-driven 로직이 전혀 작동하지 않음

---

## 📊 시나리오 분석

### 시나리오: 용량 확보 후 재할당 실패

```
T=220초 시점

상황:
- 미할당 위협: 61개
- 배터리 A: 0/3 할당 (3개 슬롯 여유)
- 배터리 B: 1/3 할당 (2개 슬롯 여유)
- 배터리 C: 2/3 할당 (1개 슬롯 여유)
- 총 가용 슬롯: 6개

현재 동작:
1. update_missile_assignments()에서 용량 확보 감지
   → capacity_freed = True
   → 미할당 61개에 needs_reassignment 플래그 설정

2. run_realtime_dwta() 호출
   → optimization_interval 체크 (line 1857)
   → T=220 - last_optimization=215 < 0.5초? NO
   → capacity_freed 체크 (line 1859)
   → capacity_freed = False로 리셋 (line 1860)
   → needs_reassignment 체크 (line 1864)
   → 61개 미사일에 플래그 있음
   → 최적화 실행 시도

3. 최적화 실행
   → 그런데 왜 2개만 할당?

문제:
- 최적화는 실행되는데 61개가 아니라 2개만 할당됨
- 배터리 용량은 충분한데 왜?
```

### 가설: MIP Infeasible 문제

```
가능한 원인:
1. Engagement matrix에서 대부분의 위협이 교전 불가능 판정
2. 동시 교전 제약(simultaneous_engagements=3)이 너무 빡빡함
3. 실시간 위치 업데이트로 인해 교전 범위 벗어남
4. K-factor가 너무 낮아서 할당 안 함

확인 필요:
- 61개 위협 중 교전 가능한 쌍이 몇 개인지?
- Engagement window가 유효한지?
- MIP가 Infeasible 반환하는지?
```

---

## 🔧 해결 방안

### Phase 1: 즉시 조치 (기존 코드 수정)

#### 1️⃣ capacity_freed 플래그 로직 수정

```python
# multi_missile_tracker_gui.py:1856-1877

# Optimization interval check
if self.current_time_step - self.last_optimization_step < self.optimization_interval:
    # 🆕 용량 확보 시 즉시 최적화 실행
    if getattr(self, 'capacity_freed', False):
        # ✅ 플래그를 여기서 리셋하지 말고 아래로 이동
        if self.control_panel:
            self.control_panel.log_message(
                f"[INFO] [T={self.current_time_step}] 용량 확보 감지 - 즉시 최적화 실행",
                "INFO"
            )
        # ✅ 최적화 진행 (리턴하지 않음)
    else:
        # Check for missiles needing reassignment
        missiles_needing_reassignment = []
        for missile_id, missile in self.missiles.items():
            if missile['active'] and missile.get('needs_reassignment', False):
                missiles_needing_reassignment.append(missile_id)

        # ✅ 추가 조건: 슬롯 가용성도 체크
        total_slots = sum(
            battery['specs']['battery_config']['simultaneous_engagements'] -
            len(self.primary_assignments.get_threats_for_battery(battery['id']))
            for battery in self.batteries
        )

        # Skip optimization if no missiles need reassignment AND no slots available
        if not missiles_needing_reassignment and total_slots == 0:
            return
        elif not missiles_needing_reassignment and total_slots > 0:
            # 슬롯은 있는데 재할당 플래그 없음 → 로그
            if self.control_panel:
                self.control_panel.log_message(
                    f"[WARNING] {total_slots} slots available but no reassignment flags - "
                    f"checking unassigned threats",
                    "WARNING"
                )
            # 미할당 위협 확인
            unassigned = [
                m_id for m_id, m in self.missiles.items()
                if m['active'] and not self.primary_assignments.get_batteries_for_threat(m_id)
            ]
            if len(unassigned) > 0:
                # 미할당 위협 있으면 최적화 진행
                if self.control_panel:
                    self.control_panel.log_message(
                        f"[INFO] Found {len(unassigned)} unassigned threats - triggering optimization",
                        "INFO"
                    )
            else:
                return
        else:
            # Log reassignment need
            if self.control_panel:
                self.control_panel.log_message(
                    f"Missiles needing reassignment: {', '.join(missiles_needing_reassignment)} - Running optimization"
                )

# ✅ 최적화 실행 후 플래그 리셋 (아래로 이동)
start_time = time.time()

# 최적화 실행...

# ✅ 성공 후 플래그 리셋
if result and result.get('feasible', False):
    self._process_optimization_results(result, solve_time)
    self.capacity_freed = False  # ✅ 여기서 리셋!
```

#### 2️⃣ 슬롯 가용성 실시간 로깅

```python
# multi_missile_tracker_gui.py:1738-1760 (update_missile_assignments 끝)

# 🆕 슬롯 가용성 로그 추가
total_slots = sum(
    battery['specs']['battery_config']['simultaneous_engagements'] -
    len(self.primary_assignments.get_threats_for_battery(battery['id']))
    for battery in self.batteries
)

unassigned_threats = [
    m_id for m_id, m in self.missiles.items()
    if m['active'] and not self.primary_assignments.get_batteries_for_threat(m_id)
]

if total_slots > 0 and len(unassigned_threats) > 0:
    if self.control_panel:
        self.control_panel.log_message(
            f"[ALERT] {total_slots} slots available, {len(unassigned_threats)} unassigned threats!",
            "WARNING"
        )
```

---

### Phase 2: Event-driven Orchestrator 통합

#### 1️⃣ Orchestrator 초기화

```python
# multi_missile_tracker_gui.py:__init__()

def __init__(self, ...):
    # ... 기존 코드 ...

    # 🆕 Event-driven Orchestrator
    self.dwta_orchestrator = None  # Lazy init
```

#### 2️⃣ run_realtime_dwta() 수정

```python
def run_realtime_dwta(self):
    """Perform real-time optimization (DWTA) with Event-driven orchestration."""

    # 🆕 Orchestrator 초기화 (lazy)
    if self.dwta_orchestrator is None:
        from dwta_orchestration_fix import DWTAOrchestrator
        self.dwta_orchestrator = DWTAOrchestrator(self)
        if self.control_panel:
            self.control_panel.log_message("[INFO] DWTA Orchestrator initialized", "INFO")

    # Active threat count
    active_threats_count = len([m for m in self.missiles.values() if m['active']])

    if not self.use_mip or active_threats_count == 0:
        return

    # 🆕 1. 슬롯 가용성 업데이트
    self.dwta_orchestrator.update_slot_availability(
        self.batteries,
        self.primary_assignments
    )

    # 🆕 2. 미할당 위협 업데이트
    self.dwta_orchestrator.update_pending_threats(
        self.missiles,
        self.primary_assignments
    )

    # 🆕 3. 긴급 위협 체크
    self.dwta_orchestrator.check_urgent_threats(
        self.missiles,
        self.current_time_step
    )

    # 🆕 4. 최적화 필요 여부 판단 (event-driven)
    should_optimize, reason = self.dwta_orchestrator.should_optimize_now(
        self.current_time_step
    )

    if not should_optimize:
        return  # 최적화 불필요

    # 로깅
    if self.control_panel:
        self.control_panel.log_message(
            f"[DWTA] Optimization triggered: {reason}",
            "INFO"
        )

    # Deadlock prevention (기존 로직)
    if self.current_time_step == self.last_optimization_step:
        if self.optimization_count >= self.max_optimizations_per_timestep:
            return
    else:
        self.optimization_count = 0

    start_time = time.time()
    self.optimization_count += 1

    try:
        # ... 기존 최적화 로직 ...

        # 결과 처리
        if result and result.get('feasible', False):
            self._process_optimization_results(result, solve_time)

            # 🆕 성공 이벤트
            self.dwta_orchestrator.on_optimization_complete(True, self.current_time_step)

        else:
            # 🆕 실패 이벤트
            self.dwta_orchestrator.on_optimization_complete(False, self.current_time_step)

    except Exception as e:
        # 🆕 예외 발생 시에도 실패 이벤트
        self.dwta_orchestrator.on_optimization_complete(False, self.current_time_step)
```

#### 3️⃣ 이벤트 트리거 추가

```python
# update_missile_assignments() 끝에

def update_missile_assignments(self):
    # ... 기존 로직 ...

    # 🆕 용량 확보 이벤트 트리거
    if hasattr(self, 'dwta_orchestrator') and self.dwta_orchestrator:
        for battery in self.batteries:
            battery_id = battery['id']
            max_simul = battery['specs']['battery_config']['simultaneous_engagements']
            assigned_count = len(self.primary_assignments.get_threats_for_battery(battery_id))

            # 슬롯 확보 체크
            if assigned_count < max_simul:
                if len(self.dwta_orchestrator.pending_threats) > 0:
                    self.dwta_orchestrator.on_capacity_freed(battery_id)
```

---

## 📊 예상 효과

### Before (현재)
```
T=220: 용량 확보, 미할당 61개
→ capacity_freed = True
→ 즉시 False로 리셋
→ needs_reassignment 체크
→ 최적화 실행
→ 2개만 할당 (왜?)

결과: 6개 슬롯 중 2개만 사용 (33% 활용)
```

### After (수정 후)
```
T=220: 용량 확보, 미할당 61개
→ orchestrator.on_capacity_freed()
→ orchestrator.update_slot_availability() (6개 슬롯 확인)
→ orchestrator.update_pending_threats() (61개 확인)
→ should_optimize_now() → True (Capacity freed + pending)
→ 최적화 실행
→ 6개 슬롯 모두 사용 (교전 가능한 위협 우선)

결과: 6개 슬롯 중 6개 사용 (100% 활용)
```

---

## 🔍 추가 조사 필요

### 왜 2개만 할당되었나?

```python
# 확인 필요 사항

1. Engagement matrix feasibility
   - 61개 위협 중 교전 가능한 쌍이 몇 개?
   - 로그: "Engagement matrix: X feasible pairs"

2. MIP 결과
   - Objective value?
   - Feasible? Infeasible?
   - 로그: "DWTA Infeasible - {reason}"

3. 동시 교전 제약
   - simultaneous_engagements = 3
   - 실제 할당 수가 3보다 작은 이유?

4. K-factor 값
   - Time-based K-factor가 너무 낮아서?
   - 늦은 시간(T=220)이라 k값이 낮아져서 할당 안 됨?
```

---

## 🎯 우선순위

1. **🔴 Immediate**: capacity_freed 플래그 로직 수정
2. **🟠 High**: 슬롯 가용성 실시간 로깅
3. **🟡 Medium**: Orchestrator 통합
4. **🟢 Low**: MIP Infeasible 원인 분석

---

## 📝 다음 단계

1. ⏳ capacity_freed 플래그 로직 패치
2. ⏳ 슬롯 가용성 로깅 추가
3. ⏳ Orchestrator 통합 (선택)
4. ⏳ 실전 테스트 및 로그 분석
5. ⏳ MIP Infeasible 원인 규명

---

**보고서 작성:** Claude Code
**검증자:** User (로그 분석)
**상태:** 🔴 수정 필요
