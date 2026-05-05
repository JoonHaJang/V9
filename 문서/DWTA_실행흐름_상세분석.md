# DWTA 실시간 미사일 방어 시스템 - 실행 흐름 상세 분석

## 📋 목차
1. [개요](#개요)
2. [미사일 방어 체계의 자연어 프로세스](#미사일-방어-체계의-자연어-프로세스)
3. [코드 구조와 실행 흐름](#코드-구조와-실행-흐름)
4. [핵심 메서드 상세 분석](#핵심-메서드-상세-분석)
5. [데이터 흐름 다이어그램](#데이터-흐름-다이어그램)

---

## 개요

이 문서는 `multi_missile_tracker_gui.py`의 실시간 DWTA(Dynamic Weapon-Target Assignment) 시스템이 어떻게 미사일 방어 작전을 시뮬레이션하는지 자연어 프로세스와 코드 구현을 매핑하여 설명합니다.

**핵심 목표**: 다수의 적 미사일 위협에 대해 제한된 요격 미사일을 **최적으로 할당**하여 **피해를 최소화**하거나 **요격 성공률을 최대화**하는 것

---

## 미사일 방어 체계의 자연어 프로세스

### 1단계: 작전 준비 (Pre-Mission Setup)
**자연어 설명**:
- 방어해야 할 중요 자산(도시, 군사 시설 등) 식별
- 사용 가능한 요격 포대(LSAM, MSAM) 배치 및 탄약 확인
- 예상되는 적 미사일 위협 정보 수집
- 각 포대의 교전 가능 범위와 요격 확률 파악

**코드 매핑**:
```python
MultiMissileTracker.__init__()
  └─> _load_scenario()  # config_mip.py에서 시나리오 데이터 로드
      ├─> self.assets: 보호 대상 자산 리스트
      ├─> self.batteries: 요격 포대 리스트 (위치, 탄약, 성능)
      ├─> self.initial_threats_config: 초기 위협 정보
      └─> self.engagement_matrix: 포대-위협 간 교전 가능 여부
```

---

### 2단계: 시나리오 시작 (Mission Start)
**자연어 설명**:
- 작전 시작 시간(T=0) 설정
- 각 적 미사일의 발사 예정 시간과 목표 설정
- 미사일 궤적 계산 (발사 위치 → 목표 자산)
- 모든 위협을 추적 시스템에 등록

**코드 매핑**:
```python
tracker.start_scenario()
  ├─> self.current_time_step = 0  # 시간 초기화
  ├─> for threat in self.initial_threats_config:
  │     └─> self.missiles[threat_id] = {
  │           'id': 위협 ID,
  │           'launch_position': 발사 위치,
  │           'target_asset': 목표 자산,
  │           'launch_time': 발사 시간,
  │           'flight_time': 비행 시간,
  │           'active': False,  # 아직 발사 전
  │           'trajectory': 계산된 궤적,
  │           'needs_reassignment': False
  │         }
  └─> self.stats['total'] = 총 위협 수
```

---

### 3단계: 실시간 작전 루프 (Real-Time Operations)
**자연어 설명**:
작전이 진행되는 동안 다음 과정을 **반복**:

#### 3-1. 상황 인식 (Situation Awareness)
- 현재 시간 진행 (5초 단위)
- 새로운 미사일 발사 감지
- 비행 중인 미사일 위치 추적
- 궤적 이탈 등 동적 이벤트 처리

**코드 매핑**:
```python
tracker.update_simulation()
  ├─> self.current_time_step += 5  # 시간 5초 진행
  ├─> _simulate_dynamic_events()
  │     └─> 궤적 이탈 처리: 미사일이 목표에서 벗어나는 경우
  │           - 할당 해제 (ABANDON)
  │           - 재할당 필요 플래그 해제
  │
  └─> for missile in self.missiles:
        ├─> if 발사 시간 도달 and not active:
        │     └─> missile['active'] = True  # 미사일 활성화
        │
        ├─> if active:
        │     ├─> 비행 진행률 계산: flight_progress = 경과시간 / 총비행시간
        │     ├─> 현재 위치 업데이트: trajectory[progress_idx]
        │     └─> if flight_progress >= 0.60:  # 교전 범위 진입
        │           └─> _process_impact()  # 요격 처리
        │
        └─> self.stats['active'] = 활성 위협 수
```

#### 3-2. 최적 할당 결정 (Optimal Assignment Decision)
**자연어 설명**:
- 현재 활성화된 모든 위협 파악
- 사용 가능한 요격 포대와 탄약 확인
- MIP(Mixed Integer Programming) 최적화 실행
  - **MIN_DAMAGE**: 자산 가치 기반 피해 최소화
  - **MAX_KILLS**: 평등주의적 요격 최대화
- 각 포대에 어떤 위협을 할당할지 결정

**코드 매핑**:
```python
tracker.run_realtime_dwta()
  ├─> 활성 위협 수 계산
  ├─> if 최적화 간격 도달 (1초마다):
  │
  ├─> _prepare_optimizer_inputs()
  │     ├─> assets_opt: 보호 대상 자산 리스트
  │     │     └─> 목적함수에 따라 가치 가중치 적용
  │     │         - MIN_DAMAGE: 실제 자산 가치 사용
  │     │         - MAX_KILLS: 모든 자산 동일 가치(1.0)
  │     │
  │     ├─> systems_opt: 사용 가능한 요격 시스템
  │     │     └─> 작동 중이고 탄약이 있는 포대만 포함
  │     │         - 위치, 탄약 수, 교전 범위, 요격 확률
  │     │
  │     └─> threats_opt: 활성 위협 리스트
  │           └─> 현재 위치, 남은 비행 시간, 목표 자산
  │
  ├─> NonLinearMIPOptimizer 실행
  │     ├─> optimizer.create_model()  # 최적화 모델 생성
  │     │     - 결정 변수: 어떤 포대가 어떤 위협을 요격할지
  │     │     - 제약 조건: 탄약 제한, 범위 제한, 동시 교전 제한
  │     │     - 목적 함수: 피해 최소화 또는 요격 최대화
  │     │
  │     └─> optimizer.solve()  # 최적해 계산 (최대 15초)
  │           └─> result = {
  │                 'feasible': True/False,
  │                 'objective_value': 목적함수 값,
  │                 'upper_assignments': {(asset, threat): battery},
  │                 'lower_assignments': {(asset, threat): battery}
  │               }
  │
  └─> _process_optimization_results(result)
        ├─> 할당 결과 검증
        │     - 위협이 여전히 활성 상태인가?
        │     - 포대가 작동 가능한가?
        │
        ├─> self.primary_assignments 업데이트
        │     └─> {battery_id: threat_id}
        │
        └─> 재할당 플래그 초기화
              └─> missile['needs_reassignment'] = False
```

#### 3-3. 요격 실행 및 결과 판정 (Engagement Execution)
**자연어 설명**:
- 미사일이 교전 범위(비행 진행률 60% 이상)에 진입하면 요격 시도
- 할당된 포대에서 요격 미사일 발사
- 각 포대의 요격 확률을 기반으로 성공/실패 판정
- **Shoot-Look-Shoot 전략**: 실패 시 재교전 시도 (최대 3회)

**코드 매핑**:
```python
_process_impact(missile_id, missile)
  ├─> 교전 시도 횟수 추적
  │     └─> self.engagement_attempts[missile_id] += 1
  │
  ├─> 할당된 포대 찾기
  │     └─> for battery_id, threat_id in self.primary_assignments:
  │           if threat_id == missile_id:
  │               assigned_batteries.append(battery_id)
  │
  ├─> if 할당된 포대 없음:
  │     └─> if flight_progress < 0.75:  # 아직 교전 가능
  │           └─> missile['needs_reassignment'] = True  # 재할당 요청
  │
  ├─> 요격 실행 및 생존 확률 계산
  │     └─> for battery in assigned_batteries:
  │           if 작동 가능 and 탄약 있음:
  │               ├─> battery['available_missiles'] -= 1  # 탄약 소비
  │               ├─> Pk = 포대의 요격 확률 (예: 0.95)
  │               └─> P_survival *= (1 - Pk)  # 누적 생존 확률
  │
  ├─> P_kill = 1 - P_survival  # 요격 성공 확률
  │
  ├─> 확률적 결과 판정
  │     └─> if random.random() < P_kill:
  │           ├─> result = 'INTERCEPTED'  # 요격 성공
  │           ├─> self.stats['intercepted'] += 1
  │           ├─> missile['active'] = False  # 위협 제거
  │           └─> self.kill_results[missile_id] = ('INTERCEPTED', time)
  │         else:
  │           ├─> result = 'MISSED'  # 요격 실패
  │           ├─> self.stats['missed'] += 1
  │           │
  │           └─> if Shoot-Look-Shoot 활성화 and 시도 횟수 < 3:
  │                 ├─> missile['flight_progress'] = 0.4  # 진행률 리셋
  │                 └─> 재교전 준비 (할당 유지)
  │               else:
  │                 ├─> missile['active'] = False  # 최종 실패
  │                 └─> 목표 자산 피해 발생
  │
  └─> 탄약 고갈 처리
        └─> if battery['available_missiles'] <= 0:
              ├─> del self.primary_assignments[battery_id]  # 할당 해제
              └─> missile['needs_reassignment'] = True  # 재할당 필요
```

#### 3-4. 시각화 업데이트 (Visualization Update)
**자연어 설명**:
- 전술 상황판에 현재 상황 표시
- 자산, 포대, 미사일 위치 시각화
- 할당 관계를 선으로 연결
- 통계 및 목적함수 값 그래프 업데이트

**코드 매핑**:
```python
tracker.update_display()
  ├─> _draw_tactical_display()
  │     ├─> 자산 표시 (파란색 다이아몬드)
  │     ├─> 포대 표시 (초록색 사각형, 탄약 수 표시)
  │     ├─> 미사일 표시 (빨간색 원, 궤적 선)
  │     └─> 할당 관계 표시 (포대-미사일 연결선)
  │
  ├─> _draw_analysis_panel()
  │     └─> 목적함수 값 변화 그래프
  │
  └─> control_panel.update_status()
        ├─> 현재 시간: T=xxx
        ├─> 활성 위협: x개
        ├─> 요격 성공: x개
        ├─> 요격 실패: x개
        └─> 성공률: xx%
```

---

### 4단계: 작전 종료 (Mission Completion)
**자연어 설명**:
- 모든 위협 발사 완료
- 모든 위협 처리 완료 (요격 성공 또는 실패)
- 최종 통계 집계 및 보고
- 시각화 결과 저장

**코드 매핑**:
```python
# run_simulation() 내부 종료 조건
if all_threats_launched and all_threats_resolved and no_active_threats:
    ├─> 최종 통계 출력
    │     ├─> 총 위협 수
    │     ├─> 요격 성공 수 및 비율
    │     └─> 요격 실패 수 및 비율
    │
    ├─> plt.savefig("dwta_analysis.png")  # 시각화 저장
    └─> 시뮬레이션 종료
```

---

## 코드 구조와 실행 흐름

### 전체 실행 흐름도

```
main()
  │
  ├─> [1] MultiMissileTracker.__init__()
  │     │
  │     ├─> _load_scenario()
  │     │     ├─> config_mip.create_realistic_scenario()
  │     │     └─> 자산, 포대, 위협 데이터 로드
  │     │
  │     └─> _setup_gui_visualization()
  │           ├─> matplotlib 창 생성
  │           └─> ControlPanel 생성
  │
  └─> [2] tracker.run_simulation(max_duration=1600)
        │
        ├─> [GUI 모드]
        │     └─> 제어 패널에서 사용자가 시작 버튼 클릭
        │           └─> run_simulation_thread()
        │
        └─> [자동 모드]
              │
              ├─> [3] start_scenario()
              │     └─> 위협 미사일 초기화
              │
              └─> while 작전 진행 중:
                    │
                    ├─> [4] run_realtime_dwta()
                    │     ├─> _prepare_optimizer_inputs()
                    │     ├─> NonLinearMIPOptimizer.solve()
                    │     └─> _process_optimization_results()
                    │
                    ├─> [5] update_simulation()
                    │     ├─> current_time_step += 5
                    │     ├─> _simulate_dynamic_events()
                    │     └─> _process_impact()
                    │
                    ├─> [6] update_display()
                    │     ├─> _draw_tactical_display()
                    │     └─> _draw_analysis_panel()
                    │
                    └─> if 종료 조건 만족:
                          └─> break
```

---

## 핵심 메서드 상세 분석

### 1. `MultiMissileTracker.__init__()`
**자연어 의미**: "작전 지휘소 설치 및 초기 정보 수집"

**주요 작업**:
- 작전 목표 설정 (피해 최소화 vs 요격 최대화)
- 시나리오 데이터 로드 (자산, 포대, 위협)
- 시뮬레이션 상태 변수 초기화
- GUI 시각화 시스템 구축

**핵심 데이터 구조**:
```python
self.missiles = {
    'threat_001': {
        'id': 'threat_001',
        'position': (x, y),
        'target_asset': 'asset_A',
        'launch_time': 5,
        'flight_time': 300,
        'active': False,
        'flight_progress': 0.0,
        'needs_reassignment': False
    }
}

self.primary_assignments = {
    'battery_A': 'threat_001',
    'battery_B': 'threat_002'
}

self.stats = {
    'total': 0,
    'active': 0,
    'intercepted': 0,
    'missed': 0,
    'retargeted': 0
}
```

---

### 2. `start_scenario()`
**자연어 의미**: "작전 개시 - 모든 위협 정보를 레이더에 등록"

**주요 작업**:
- 시간을 T=0으로 설정
- 각 위협 미사일 객체 생성
- 발사 위치에서 목표까지 궤적 계산
- 총 위협 수 집계

**궤적 계산 예시**:
```python
# 발사 위치 (0, 0)에서 목표 (100, 100)까지
trajectory = [
    (0, 0),      # t=0
    (10, 10),    # t=10%
    (20, 20),    # t=20%
    ...
    (100, 100)   # t=100% (도착)
]
```

---

### 3. `run_realtime_dwta()`
**자연어 의미**: "실시간 최적 할당 계산 - 어떤 포대가 어떤 위협을 맡을지 결정"

**최적화 문제 정의**:
```
목적함수 (MIN_DAMAGE):
  minimize Σ (자산 가치 × 미요격 확률)

제약 조건:
  1. 각 포대의 탄약 제한
  2. 각 포대의 교전 범위 제한
  3. 각 포대의 동시 교전 제한
  4. 각 위협은 최대 N개 포대에 할당 가능

결정 변수:
  x[battery][threat] ∈ {0, 1}
  (포대 i가 위협 j를 요격하면 1, 아니면 0)
```

**할당 예시**:
```
입력:
  - 활성 위협: [threat_001, threat_002, threat_003]
  - 사용 가능 포대: [battery_A(탄약 5발), battery_B(탄약 3발)]
  - 자산: [asset_A(가치 100), asset_B(가치 50)]

출력:
  - battery_A → threat_001 (asset_A 방어)
  - battery_A → threat_002 (asset_A 방어)
  - battery_B → threat_003 (asset_B 방어)
```

---

### 4. `update_simulation()`
**자연어 의미**: "시간 진행 및 상황 업데이트 - 미사일 추적 및 이벤트 처리"

**시간 진행 시뮬레이션**:
```
T=0   → T=5   → T=10  → T=15  → ...
│       │       │       │
│       │       │       └─> threat_003 발사
│       │       └─> threat_002 발사
│       └─> threat_001 발사
└─> 작전 시작
```

**비행 진행률 계산**:
```python
# 예: 발사 후 150초 경과, 총 비행 시간 300초
time_in_flight = 150
flight_time = 300
flight_progress = 150 / 300 = 0.5 (50%)

# 교전 범위 진입 판정
if flight_progress >= 0.60:  # 60% 이상
    _process_impact()  # 요격 시도
```

---

### 5. `_process_impact()`
**자연어 의미**: "요격 실행 및 결과 판정 - 미사일 발사하고 성공/실패 확인"

**요격 확률 계산**:
```
단일 포대 요격 확률: Pk = 0.95

2개 포대 동시 요격:
  P_survival = (1 - 0.95) × (1 - 0.95) = 0.0025
  P_kill = 1 - 0.0025 = 0.9975 (99.75%)

3개 포대 동시 요격:
  P_survival = (1 - 0.95)³ = 0.000125
  P_kill = 1 - 0.000125 = 0.999875 (99.99%)
```

**Shoot-Look-Shoot 전략**:
```
시도 1: 요격 실패 (5% 확률)
  └─> flight_progress를 0.4로 리셋
      └─> 재할당 없이 동일 포대로 재교전

시도 2: 요격 실패 (5% 확률)
  └─> flight_progress를 0.4로 리셋
      └─> 재교전

시도 3: 요격 실패 (5% 확률)
  └─> 최종 실패 처리
      └─> 목표 자산 피해 발생
```

---

### 6. `_prepare_optimizer_inputs()`
**자연어 의미**: "최적화에 필요한 현재 상황 정보 정리"

**데이터 변환**:
```python
# 시뮬레이션 데이터 → 최적화 입력 형식

# 자산 정보
assets_opt = [
    Asset(
        id='asset_A',
        position=(50, 100),
        value=100,  # MIN_DAMAGE 모드
        priority=1,
        estimated_threat_missiles=['threat_001', 'threat_002']
    )
]

# 포대 정보
systems_opt = [
    InterceptorSystem(
        id='battery_A',
        system_type='LSAM',
        position=(0, 0),
        available_missiles=5,
        max_missiles_per_target=2,
        intercept_probability=0.95,
        engagement_range=150.0
    )
]

# 위협 정보
threats_opt = [
    Threat(
        id='threat_001',
        target_asset_id='asset_A',
        current_position=(25, 50),
        estimated_impact_time=150.0
    )
]
```

---

### 7. `_process_optimization_results()`
**자연어 의미**: "최적화 결과를 실제 할당 명령으로 변환"

**할당 검증 프로세스**:
```python
# 최적화 결과
result = {
    'upper_assignments': {
        'asset_A_threat_001': 'battery_A',
        'asset_B_threat_002': 'battery_B'
    }
}

# 검증 및 변환
for key, battery_id in result['upper_assignments'].items():
    asset_id, threat_id = key.split('_', 1)
    
    # 검증 1: 위협이 여전히 활성 상태인가?
    if threat_id not in self.missiles or not self.missiles[threat_id]['active']:
        continue  # 무효 할당
    
    # 검증 2: 포대가 작동 가능한가?
    battery = find_battery(battery_id)
    if battery['status'] != 'OPERATIONAL' or battery['available_missiles'] <= 0:
        continue  # 무효 할당
    
    # 유효한 할당 저장
    self.primary_assignments[battery_id] = threat_id
```

---

### 8. `_simulate_dynamic_events()`
**자연어 의미**: "예상치 못한 상황 처리 - 미사일 궤적 이탈 등"

**동적 이벤트 예시**:
```python
# 궤적 이탈 (1% 확률)
if 0.3 <= flight_progress <= 0.6:  # 비행 중반부
    if random.random() < 0.01:
        # 미사일이 목표에서 벗어남
        missile['target_asset'] = 'EMPTY_AREA'
        missile['active'] = False
        
        # 할당 해제
        del self.primary_assignments[battery_id]
        
        # 통계 업데이트
        self.stats['deviated'] += 1
```

---

## 데이터 흐름 다이어그램

### 시간에 따른 데이터 변화

```
T=0 (작전 시작)
├─ missiles: {threat_001: {active: False, launch_time: 5}}
├─ primary_assignments: {}
└─ stats: {total: 1, active: 0, intercepted: 0, missed: 0}

T=5 (threat_001 발사)
├─ missiles: {threat_001: {active: True, flight_progress: 0.0}}
├─ run_realtime_dwta() 실행
│    └─ primary_assignments: {battery_A: threat_001}
└─ stats: {total: 1, active: 1, intercepted: 0, missed: 0}

T=10 (비행 진행)
├─ missiles: {threat_001: {active: True, flight_progress: 0.33}}
└─ stats: {total: 1, active: 1, intercepted: 0, missed: 0}

T=180 (교전 범위 진입, flight_progress = 0.60)
├─ _process_impact() 실행
│    ├─ battery_A 미사일 발사
│    ├─ battery_A['available_missiles'] -= 1
│    └─ P_kill = 0.95 계산
│
├─ 확률적 판정: random.random() < 0.95 → 성공
│
├─ missiles: {threat_001: {active: False}}
├─ kill_results: {threat_001: ('INTERCEPTED', 180)}
└─ stats: {total: 1, active: 0, intercepted: 1, missed: 0}

T=300 (작전 종료)
└─ 최종 통계: 성공률 100%
```

---

## 핵심 알고리즘 요약

### 1. 최적 할당 알고리즘 (MIP)
```
입력: 활성 위협, 사용 가능 포대, 보호 자산
출력: 포대-위협 할당 매핑

알고리즘:
1. 목적함수 정의 (MIN_DAMAGE 또는 MAX_KILLS)
2. 제약 조건 설정 (탄약, 범위, 동시 교전)
3. MIP 솔버 실행 (Gurobi/CBC)
4. 최적 할당 반환
```

### 2. 요격 판정 알고리즘 (확률적)
```
입력: 할당된 포대 리스트, 각 포대의 요격 확률
출력: 요격 성공/실패

알고리즘:
1. P_survival = 1.0
2. for 각 포대:
     P_survival *= (1 - Pk)
3. P_kill = 1 - P_survival
4. if random() < P_kill:
     return INTERCEPTED
   else:
     return MISSED
```

### 3. Shoot-Look-Shoot 알고리즘
```
입력: 요격 결과, 시도 횟수
출력: 재교전 여부

알고리즘:
1. if 요격 성공:
     위협 제거
2. else if 시도 횟수 < 3:
     flight_progress 리셋
     재교전 준비
3. else:
     최종 실패 처리
```

---

## 주요 설계 원칙

### 1. 실시간성 (Real-Time)
- 1초 간격으로 최적화 수행
- 15초 타임아웃으로 데드락 방지
- 5초 단위 시간 진행

### 2. 동적 적응성 (Dynamic Adaptation)
- 궤적 이탈 시 할당 자동 해제
- 탄약 고갈 시 재할당 요청
- 요격 실패 시 자동 재교전

### 3. 확률적 현실성 (Stochastic Realism)
- 요격 확률 기반 성공/실패 판정
- 다중 포대 동시 교전 시 확률 누적
- 궤적 이탈 등 예상치 못한 이벤트

### 4. 최적성 (Optimality)
- MIP 기반 수학적 최적 할당
- 목적함수 선택 가능 (피해 최소화 vs 요격 최대화)
- 제약 조건 엄격 준수

---

## 결론

이 시스템은 **실제 미사일 방어 작전의 핵심 프로세스**를 충실히 시뮬레이션합니다:

1. **상황 인식** → `update_simulation()`
2. **최적 의사결정** → `run_realtime_dwta()`
3. **실행 및 평가** → `_process_impact()`
4. **적응 및 재계획** → Shoot-Look-Shoot, 재할당

각 메서드는 실제 방어 작전의 특정 단계를 구현하며, 자연어 프로세스와 코드가 **1:1로 매핑**되어 있습니다.
