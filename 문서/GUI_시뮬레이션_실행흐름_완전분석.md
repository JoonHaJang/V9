# DWTA GUI 시뮬레이션 실행 흐름 완전 분석
**GUI 버튼 클릭 → 시나리오 종료까지의 완전한 코드 흐름**

---

## 📋 목차
1. [문서 개요](#문서-개요)
2. [시뮬레이션 실행 시작 (Start Button Click)](#시뮬레이션-실행-시작)
3. [메인 시뮬레이션 루프 (Main Loop)](#메인-시뮬레이션-루프)
4. [시나리오 종료 처리 (Termination)](#시나리오-종료-처리)
5. [코드 실행 타임라인](#코드-실행-타임라인)
6. [스레드 안전성 및 GUI 업데이트](#스레드-안전성-및-gui-업데이트)

---

## 문서 개요

### 목적
이 문서는 `multi_missile_tracker_gui.py`에서 사용자가 "시작" 버튼을 클릭한 순간부터 시뮬레이션이 종료될 때까지의 **전체 코드 실행 흐름**을 라인 단위로 추적하여 설명합니다.

### 핵심 구성 요소
- **ControlPanel**: GUI 제어 패널 (버튼, 상태 표시)
- **MultiMissileTracker**: 시뮬레이션 엔진
- **NonLinearMIPOptimizer**: 최적화 엔진
- **Simulation Thread**: 백그라운드 시뮬레이션 실행 스레드

### 실행 환경
- **Main Thread**: Tkinter GUI 이벤트 루프
- **Simulation Thread**: 백그라운드 시뮬레이션 계산
- **시간 단위**: 5초 간격 (current_time_step += 5)
- **최적화 주기**: 1초 간격 (필요시)

---

## 시뮬레이션 실행 시작

### 1단계: 사용자 버튼 클릭

```
📍 위치: multi_missile_tracker_gui.py, Line 244-246
```

사용자가 제어 패널에서 "▶ 시작" 버튼을 클릭합니다.

```python
# ControlPanel.create_controls()
# GUI 버튼 생성: 사용자가 클릭할 수 있는 \"시작\" 버튼을 만듭니다
# ttk.Button: Tkinter themed button (윈도우 네이티브 스타일)
self.start_btn = ttk.Button(
    button_frame,                      # 버튼이 표시될 부모 컨테이너
    text=\"▶ 시작\",                    # 버튼에 표시될 텍스트
    command=self.start_simulation,     # 클릭 시 실행할 함수
    style='Military.TButton'           # 적용할 스타일 (사전 정의됨)
)
```

**이벤트**: 
- Tkinter 이벤트 핸들러가 `ControlPanel.start_simulation()` 메서드 호출

---

### 2단계: start_simulation() 메서드 실행

```
📍 위치: multi_missile_tracker_gui.py, Line 393-413
```

```python
def start_simulation(self):
    """시뮬레이션 시작
    
    Main Thread(GUI)에서 호출되는 버튼 핸들러
    실제 시뮬레이션은 별도의 Simulation Thread에서 실행됨
    """
    # [Line 395-396] 중복 시작 방지
    # 이미 실행 중이면 함수 종료 (중복 클릭 방지)
    if self.running:
        return
    
    # [Line 398-399] 상태 플래그 설정
    # running: 시뮬레이션이 진행 중인지 여부
    # paused: 현재 일시정지 중인지 여부
    self.running = True   # ← 시뮬레이션 시작
    self.paused = False   # ← 일시정지 아님
    
    # [Line 401-404] 버튼 상태 변경
    # 사용자 입력 제어: 이미 시작했으므로 "시작" 버튼 비활성화
    self.start_btn.config(state="disabled")      # "시작" 버튼 비활성화 (회색 표시)
    self.pause_btn.config(state="normal")        # "일시정지" 버튼 활성화 (클릭 가능)
    self.stop_btn.config(state="normal")         # "정지" 버튼 활성화
    
    # [Line 406-407] 목적함수 설정 적용
    # GUI에서 선택한 목적함수를 최적화기에 전달
    # 'MIN_DAMAGE': 손실 최소화 (보호 우선)
    # 'MAX_KILLS': 요격 최대화 (공격 우선)
    self.tracker.objective = self.objective_var.get()  # 'MIN_DAMAGE' 또는 'MAX_KILLS'
    
    # [Line 409] 로그 메시지 출력
    # 시작 로그를 GUI의 로그 패널에 표시
    self.log_message(f"시뮬레이션 시작 - {OBJECTIVES[self.tracker.objective]}", "SUCCESS")
    
    # [Line 411-413] 시뮬레이션 스레드 생성 및 시작 ★ (핵심!)
    # 1. 새 Thread 객체 생성
    #    - target=self.run_simulation_thread: 실행할 함수
    #    - daemon=True: 메인 프로그램이 종료되면 이 스레드도 함께 종료
    # 2. self.sim_thread.start() 호출
    #    - Thread.start() 메서드가 run_simulation_thread()를 별도 스레드에서 실행
    #    - Main Thread는 계속 GUI 이벤트 처리 (블로킹 안 됨)
    self.sim_thread = threading.Thread(
        target=self.run_simulation_thread,  # 이 함수를 별도 스레드에서 실행
        daemon=True                         # 데몬 스레드 (메인이 종료되면 자동 종료)
    )
    self.sim_thread.start()  # ← 실제로 스레드 시작!
```

**핵심 동작**:
1. 상태 플래그 설정 (`running=True`, `paused=False`)
2. GUI 버튼 상태 업데이트
3. **별도 스레드 생성 및 시작** → `run_simulation_thread()` 실행

**스레드 분리 이유**:
- Main Thread: GUI 이벤트 처리 (버튼 클릭, 화면 업데이트)
- Simulation Thread: 계산 집약적 작업 (최적화, 물리 시뮬레이션)

---

### 3단계: run_simulation_thread() 실행 (Simulation Thread)

```
📍 위치: multi_missile_tracker_gui.py, Line 415-442
```

이제 **별도 스레드**에서 시뮬레이션이 실행됩니다.

```python
def run_simulation_thread(self):
    """시뮬레이션 실행 스레드
    
    이 함수는 별도의 Simulation Thread에서 실행됩니다.
    Main Thread와 분리되어 있으므로 GUI가 먹통되지 않습니다.
    """
    try:
        # [Line 418-419] ★ 시나리오 초기화
        # 시뮬레이션에 필요한 모든 데이터 구조 생성
        # - 미사일 객체 생성 (활성화 전)
        # - 포대 상태 초기화
        # - 통계 초기화
        self.tracker.start_scenario()
        
        # 이전 통계를 저장해서 나중에 변화를 감지
        prev_stats = self.tracker.stats.copy()
        
        # [Line 421-442] ★ 메인 시뮬레이션 루프
        # 시뮬레이션이 실행 중(self.running=True)의 동안 계속 반복
        while self.running:
            # 일시정지 중이 아닐 때만 시뮬레이션 진행
            if not self.paused:
                # [Step 1] DWTA 최적화 실행
                # 활성 미사일과 포대의 최적 할당 계산
                # (MIP 솔버로 0.8초 정도 걸림)
                self.tracker.run_realtime_dwta()
                
                # [Step 2] 물리 시뮬레이션 업데이트
                # 시간 진행 (T += 5초)
                # 미사일 발사 및 비행 진행
                # 요격 판정 및 결과 반영
                self.tracker.update_simulation()
                
                # [Step 3] 이벤트 체크 및 로깅
                # 통계 변화 감지 (새 미사일 발사, 요격 성공/실패 등)
                # GUI 로그 패널에 메시지 표시
                self.check_events(prev_stats, self.tracker.stats)
                
                # 이번 루프의 통계를 다음 루프 비교용으로 저장
                prev_stats = self.tracker.stats.copy()
                
                # [Step 4] 종료 조건 확인
                # 모든 미사일 처리, 시간 제한 등으로 종료 판정
                # 종료하면 while 루프 탈출
                if self.should_terminate():
                    break
            
            # [Step 5] 시뮬레이션 속도 조절
            # 루프 반복 간격을 조절해서 전체 시뮬레이션 속도 제어
            # speed_var=1.0: 0.1초 대기 (1배속)
            # speed_var=2.0: 0.05초 대기 (2배속)
            # speed_var=0.5: 0.2초 대기 (0.5배속)
            time.sleep(0.1 / self.speed_var.get())
                
    except Exception as e:
        # 예기치 않은 오류 발생 시 처리
        self.log_message(f"시뮬레이션 오류: {e}", "ERROR")
    finally:
        # [Line 442] 시뮬레이션 종료 처리 (정상/오류 종료 모두 실행)
        # after(0, ...): Main Thread에서 GUI 업데이트를 안전하게 수행
        # (Simulation Thread에서 직접 GUI 접근 불가)
        self.control_window.after(0, self.simulation_finished)
```

**메인 루프 구조**:
```
Loop Iteration (0.1초마다):
  ├─> [조건 체크] running=True, paused=False
  ├─> [Step 1] run_realtime_dwta()       (최적화)
  ├─> [Step 2] update_simulation()       (물리 엔진)
  ├─> [Step 3] check_events()            (이벤트)
  ├─> [Step 4] should_terminate()        (종료 체크)
  └─> [Step 5] time.sleep()              (속도 제어)
```

---

### 4단계: start_scenario() - 시나리오 초기화

```
📍 위치: multi_missile_tracker_gui.py, Line 748-771
```

시뮬레이션 데이터 구조를 초기화합니다.

```python
def start_scenario(self):
    """Initialize the fixed scenario threats."""
    print("\nStarting scenario simulation...")
    
    # [Line 751] 시간 초기화
    self.current_time_step = 0
    
    # [Line 753-771] 각 위협 미사일 초기화
    for threat in self.initial_threats_config:
        target_asset = next((a for a in self.assets 
                            if a['id'] == threat['target_asset_id']), None)
        
        if target_asset:
            self.missiles[threat['id']] = {
                'id': threat['id'],
                'position': threat['launch_position'],
                'launch_position': threat['launch_position'],
                'target_asset': threat['target_asset_id'],
                'target_position': target_asset['position'],
                'launch_time': threat.get('launch_time', 0),      # 발사 시간
                'flight_time': threat.get('flight_time', 300),    # 비행 시간
                'active': False,                                  # 아직 발사 전
                'flight_progress': 0.0,
                'trajectory': self._calculate_trajectory(         # 궤적 계산
                    threat['launch_position'], 
                    target_asset['position']
                ),
                'target_changed': 0,
                'can_retarget': True,
                'retarget_probability': 0.002
            }
    
    # [Line 771] 총 위협 수 기록
    self.stats['total'] = len(self.missiles)
```

**초기화 완료 상태**:
```python
self.missiles = {
    'T08': {
        'id': 'T08',
        'position': (0, 0),           # 발사 위치
        'target_asset': 'A05',        # 목표 자산
        'launch_time': 5,             # T=5초에 발사
        'flight_time': 480,           # 비행 시간 480초
        'active': False,              # 아직 미발사
        'trajectory': [(0,0), (1,1), ...],  # 100개 waypoint
        ...
    },
    ...
}
```

---

## 메인 시뮬레이션 루프

### 루프 반복 주기

```
시간 진행: T=0 → T=5 → T=10 → T=15 → ... → T=800
│
└─> 각 5초마다:
      ├─> run_realtime_dwta()      (1초 간격으로 필요시 실행)
      ├─> update_simulation()       (매 5초마다 실행)
      └─> 0.1초 대기 (속도 조절)
```

### Step 1: run_realtime_dwta() - DWTA 최적화

```
📍 위치: multi_missile_tracker_gui.py, Line 988-1108
```

#### 1-1. 최적화 필요성 판단

```python
def run_realtime_dwta(self):
    """Perform real-time optimization (DWTA) with comprehensive logic."""
    
    # [Line 991] 활성 위협 수 계산
    active_threats_count = len([m for m in self.missiles.values() if m['active']])
    
    # [Line 993-997] 최적화 불필요 조건 체크
    if not self.use_mip or active_threats_count == 0:
        return  # 최적화 생략
    
    # [Line 1000-1005] 데드락 방지: 같은 타임스텝에서 최대 횟수 제한
    if self.current_time_step == self.last_optimization_step:
        if self.optimization_count >= self.max_optimizations_per_timestep:
            return
    else:
        self.optimization_count = 0  # 새 타임스텝이면 카운터 리셋
    
    # [Line 1008-1022] 최적화 간격 체크 (1초 간격)
    if self.current_time_step - self.last_optimization_step < 1:
        # 재할당이 필요한 미사일이 있는지 체크
        missiles_needing_reassignment = [
            missile_id for missile_id, missile in self.missiles.items()
            if missile['active'] and missile.get('needs_reassignment', False)
        ]
        
        if not missiles_needing_reassignment:
            return  # 재할당 불필요하면 최적화 생략
```

**최적화 실행 조건**:
1. `use_mip=True` (MIP 사용 설정)
2. `active_threats_count > 0` (활성 위협 존재)
3. 마지막 최적화로부터 1초 경과 OR 재할당 필요

#### 1-2. 최적화 입력 준비

```python
# [Line 1034] ★ 최적화 입력 준비
assets_opt, systems_opt, threats_opt = self._prepare_optimizer_inputs()

if not systems_opt or not threats_opt:
    return  # 입력 데이터 없으면 종료
```

```
📍 _prepare_optimizer_inputs() 위치: Line 1110-1228
```

```python
def _prepare_optimizer_inputs(self):
    """Prepare comprehensive optimizer inputs"""
    
    # [Step 1] 활성 위협 매핑 구축
    active_threats = {}
    threat_to_asset_map = {}
    
    for missile in self.missiles.values():
        if missile['active']:
            target_asset_id = missile['target_asset'] #'A05'
            threat_to_asset_map[missile['id']] = target_asset_id
            #{'T08':'A05'}
            if target_asset_id not in active_threats: #'A05'가 처음 당증 시 
                active_threats[target_asset_id] = []
            # active_threats = {'A05': []}
            active_threats[target_asset_id].append(missile['id'])
            # active_threats = {'A05': ['T08']}

    # [Step 2] 자산 정보 준비
    assets_opt = []
# -----------------------------------------------------------------------------
# 모든 자산(10개)을 순회하며 Asset 객체로 변환
# self.assets는 GUI 시뮬레이션에서 관리하는 원본 자산 데이터 (딕셔너리 리스트)
# 예: [{'id': 'A01', 'position': (10,20,0), 'value': 520, ...}, ...]
# -----------------------------------------------------------------------------
    for asset in self.assets:
        # 목적함수에 따른 가치 가중치 적용
        if self.objective == 'MAX_KILLS':
            value = 1.0  # 평등주의적 접근
        else:  # MIN_DAMAGE

            value = asset.get('weighted_value', asset.get('value', 0))
        #             └─────┬─────┘  └────────┬────────┘  └┬┘
        #                  1순위             2순위        기본값
    # =========================================================================
    # active_threats는 Step 1에서 생성한 딕셔너리
    # 구조: {'A05': ['T08', 'T02', 'T06'], 'A03': ['T09', 'T11'], ...}
    # 
    # .get(asset['id'], []) 설명:
    # -------------------------------------------------------------------------
    # active_threats.get(asset['id'], [])
    # 
    # [경우 1] asset['id']가 active_threats에 있는 경우
    #   - 예: asset['id'] = 'A05'
    #   - active_threats['A05'] = ['T08', 'T02', 'T06']
    #   - 반환: ['T08', 'T02', 'T06']
    #   - 의미: A05를 위협하는 3개 미사일 리스트
    # 
    # [경우 2] asset['id']가 active_threats에 없는 경우
    #   - 예: asset['id'] = 'A06'
    #   - active_threats에 'A06' 키가 없음 (위협하는 미사일이 없음)
    #   - 반환: [] (빈 리스트)
    #   - 의미: A06은 현재 위협받지 않음
    # 
    # 왜 기본값이 []인가?
    #   - 위협이 없더라도 자산 객체는 생성해야 함
    #   - 최적화기는 모든 자산 정보를 필요로 함
    #   - 빈 리스트 → 최적화기가 "이 자산은 할당 불필요" 판단
    # -------------------------------------------------------------------------
        estimated_threat_missiles = active_threats.get(asset['id'], [])
        
        assets_opt.append(Asset(
            id=asset['id'],
            position=asset['position'],
            value=value,
            priority=asset.get('priority', 1),
            estimated_threat_missiles=estimated_threat_missiles
        ))
    
    # [Step 3] 요격 시스템 정보 준비
    systems_opt = []
    for battery in self.batteries:
        # 작동 가능하고 탄약이 있는 포대만 포함
        if battery.get('status') != 'OPERATIONAL' or \
           battery.get('available_missiles', 0) <= 0:
            continue
        
        # 시스템 사양 추출
        if battery['system_type'] == 'LSAM':
            specs = battery['specs']['ballistic_missile_specs']
            Pk = specs['intercept_probability']  # 예: 0.95
            Range = specs['engagement_range_km']['max']  # 예: 150km
            max_missiles = battery['specs']['battery_config']\
                          .get('simultaneous_engagements', 2)
        
        # ... MSAM 등 다른 시스템도 동일 처리
        # ---------------------------------------------------------------------
        # id: 포대 식별자 (문자열)
        # ---------------------------------------------------------------------
        # 예: 'LSAM_03', 'MSAM_01'
        # 용도:
        #   - 최적화 변수 이름: x_upper_A05_T08_LSAM_03
        #   - 할당 결과 매핑: {'LSAM_03': 'T08'}
        #   - 로그 출력: "LSAM_03 assigned to T08"
        # ---------------------------------------------------------------------
        # ---------------------------------------------------------------------
        # system_type: 시스템 유형 (문자열)
        # ---------------------------------------------------------------------
        # 예: 'LSAM', 'MSAM', 'PATRIOT'
        # 용도:
        #   - 상층/하층 구분
        #     - 'LSAM' → upper_systems 리스트에 포함
        #     - 'MSAM' → lower_systems 리스트에 포함
        #   - 변수 이름 prefix
        #     - x_upper (LSAM)
        #     - x_lower (MSAM)
        # 
        # 최적화기 내부:
        #   if system.system_type in ['LSAM', 'PATRIOT']:
        #       upper_systems.append(system)
        #   elif system.system_type in ['MSAM', 'IRON_DOME']:
        #       lower_systems.append(system)
        # 
        # max_missiles_per_target: 표적당 최대 미사일 수 (정수)
---------------------------------------------------------------------
        systems_opt.append(InterceptorSystem(
            id=battery['id'],
            system_type=battery['system_type'],
            position=battery['position'],
            available_missiles=battery['available_missiles'],
            max_missiles_per_target=min(max_missiles, 
                                       battery['available_missiles']),
            intercept_probability=Pk,
            engagement_range=Range
        ))
    
    # [Step 4] 위협 정보 준비
    threats_opt = []
# -----------------------------------------------------------------------------
# 모든 미사일을 순회하며 활성(비행 중) 미사일만 추출
# self.missiles.values(): 딕셔너리의 값들만 순회 (키는 무시)
# -----------------------------------------------------------------------------
    for missile in self.missiles.values():
        if missile['active']:
            # 남은 비행 시간 계산
            remaining_time = max(0.1, 
                missile['flight_time'] * (1.0 - missile['flight_progress']))
        # 
        # max(0.1, ...) 의미: - 계산 결과와 0.1 중 큰 값 선택
            current_pos = missile['position']
            altitude = 10000.0 * (1.0 - missile['flight_progress'])
            
            threats_opt.append(Threat(
                id=missile['id'],
                target_asset_id=missile['target_asset'],
                current_position=(current_pos[0], current_pos[1], altitude),
                estimated_impact_time=remaining_time
            ))
    
    return assets_opt, systems_opt, threats_opt
#모든 자산 + 각자 받는 위협 정보
#교전 가능한 포대만 (필터링)
#활성화된 위협만 (필터링)
```

**예시 데이터**:
```python
# T=375초 시점
assets_opt = [
    Asset(id='A05', position=(10,10), value=720, priority=1,
          estimated_threat_missiles=['T08'])
]

systems_opt = [
    InterceptorSystem(id='LSAM_03', system_type='LSAM',
                     position=(0,0), available_missiles=18,
                     intercept_probability=0.95, engagement_range=150.0)
]

threats_opt = [
    Threat(id='T08', target_asset_id='A05',
          current_position=(25.0, 50.0, 5000.0),
          estimated_impact_time=105.0)
]
```

#### 1-3. 최적화 모델 생성 및 실행

```python
# [Line 1040-1047] MIP 최적화 모델 생성
# NonLinearMIPOptimizer: McCormick 선형화를 사용한 비선형 MIP 최적화기 클래스
#   - 위치: nonlinear_mip_optimizer.py
#   - 역할: 비선형 DWTA 문제를 선형 MIP로 변환하여 해결
# 
# self.config: 설정 객체
#   - 타입: MIPConfig (config_mip.py에서 정의)
#   - 포함 내용:
#     * 솔버 설정: time_limit, gap_tolerance, threads
#     * k 파라미터 범위: k_min=0.6, k_max=1.0
#     * 미사일 발수: missiles_per_engagement=2 (살보 발사)
#     * 제약조건 플래그: enable_capacity_constraints, enable_multi_layer_defense
# 
# optimizer 객체 생성 시 초기화:
#   - self.model = None (PuLP 모델, 아직 생성 안 됨)
#   - self.variables = {} (결정 변수들, 비어있음)
#   - self.constraints = {} (제약조건들, 비어있음)
#   - self.k_min = 0.6, self.k_max = 1.0 (교전 윈도우 품질 범위)
#   - self.missiles_per_engagement = 2 (2발 살보)
# 
# 왜 매번 새로 생성?
#   - 각 최적화는 독립적 (이전 결과 영향 없음)
#   - 상태 초기화 (변수, 제약조건 등)
#   - 메모리 관리 (사용 후 GC로 자동 해제)
# -----------------------------------------------------------------------------
optimizer = NonLinearMIPOptimizer(self.config)
optimizer.create_model(
    assets=assets_opt,
    interceptor_systems=systems_opt,
    threats=threats_opt,
    batteries=self.batteries,
    engagement_matrix=self.engagement_matrix
)
    # =========================================================================
    # engagement_matrix: 교전 가능성 매트릭스
    # =========================================================================
    # 타입: Dict[(battery_id, threat_id), bool]
    # 크기: 최대 10×15 = 150개 항목
    # 
    # 구조:
    #   {
    #       ('LSAM_03', 'T08'): True,   # LSAM_03이 T08 교전 가능 ✓
    #       ('LSAM_03', 'T10'): False,  # 거리 초과 ✗
    #       ('MSAM_03', 'T08'): True,   # MSAM_03이 T08 교전 가능 ✓
    #       ...
    #   }
    # 
    # 생성 시점: 시뮬레이션 초기화 시 (start_scenario())
    # 계산 기준:
    #   1. 거리 제약: distance(battery, threat) ≤ engagement_range
    #   2. 고도 제약: threat_altitude ∈ [alt_min, alt_max]
    #   3. 각도 제약: 방위각, 고각 범위 내
    # 
    # 예시:
    #   LSAM_03 (0,0) vs T08 (발사→50,60):
    #     - 최대 거리: sqrt(50² + 60²) = 78.1km
    #     - LSAM range: 150km
    #     - 78.1 < 150 → True ✓
    # 
    #   MSAM_05 (40,45) vs T08:
    #     - 거리: sqrt((50-40)² + (60-45)²) = 18km
    #     - MSAM range: 120km
    #     - 18 < 120 → True ✓
    # 
    # optimizer에서 사용:
    #   1. 변수 생성 필터링
    #      - engagement_matrix[(battery_id, threat_id)] == True인 경우만
    #      - x_upper[(asset, threat, system)] 생성
    # 내부 저장:
    #   self.engagement_matrix = engagement_matrix
    # 
    # 중요: 이 매트릭스는 "물리적 교전 가능성"만 판단
    #       실제 할당 여부는 최적화 결과로 결정
    # -------------------------------------------------------------------------
# [Line 1050] 최적화 실행 (최대 15초 타임아웃)
result = optimizer.solve()
# # solve() 메서드 (nonlinear_mip_optimizer.py, Line 1233-1287):
# solve() 메서드 상세:
#============================================================================
# 
# [1] 모델 존재 확인:
#     if not self.model:
#         raise ValueError("Model not created")
# 
# [2] CBC 솔버 설정:
#     solver = pulp.PULP_CBC_CMD(
#         msg=0,          # 로그 출력 비활성화 (GUI용)
#         timeLimit=5,    # 최대 5초 (대부분 0.8초 해결)
#         gapRel=0.1,     # 10% 최적성 갭 허용 (실용적)
#         threads=1       # 단일 스레드 (모델 작아서 충분)
#     )
#     
#     파라미터 의미:
#     - timeLimit: 타임아웃 시 현재 최선해 반환 (실패 아님)
#     - gapRel: gap = (상한-하한)/상한 < 10% → 종료
#     - threads: 멀티스레드 오버헤드 방지
# 
# [3] CBC 솔버 실행 (0.8초):
#     self.model.solve(solver)
#     
#     내부 알고리즘:
#     [0.00초] 전처리: 중복 제거, 변수 축소 (340→300)
#     [0.05초] LP Relaxation: x∈{0,1}→x∈[0,1], Z_LP=25.2 (하한)
#     [0.2초]  Branch & Bound: 이진 분기, ~45개 노드 탐색
#     [0.5초]  Cut Generation: Gomory/Cover/Clique 절단평면 ~25개
#     [0.8초]  최적해 발견: Z*=27.3, Gap=7.7%<10% → 종료 ✓
# 
# [4] 결과 분석 및 추출:
#     feasible = (model.status == LpStatusOptimal)
#     objective_value = model.objective.value()  # 27.3
#     
#     if feasible:
#         upper_assignments = _extract_assignments('x_upper')
#         # x=1인 변수만 추출: {'A05_T08': 'LSAM_03'}
#         
#         lower_assignments = _extract_assignments('x_lower')
#         # {'A05_T08': 'MSAM_03'}
#         
#         upper_k_values = _extract_k_values('k_upper')
#         # {'A05_T08': 0.95} (교전 윈도우 품질)
#         
#         asset_survival_probs = _extract_survival_probabilities()
#         # {'A05': 0.00156} (0.156% 손실 확률)
# 
# [5] result 반환
# =============================================================================

result = optimizer.solve()

solve_time = time.time() - start_time
```

**optimizer.solve() 내부 동작** (nonlinear_mip_optimizer.py):
```
1. McCormick 선형화 (w = x × k × P)
   ├─> 이진 변수 생성 (할당 여부)
   ├─> 연속 변수 생성 (교전 원도우)
   └─> 보조 변수 생성 (생존 확률)

2. 제약 조건 추가
   ├─> McCormick 4개 부등식
   ├─> 탄약 제약
   ├─> 동시 교전 제약
   ├─> 거리/고도 제약
   └─> Binary Tree 제약

3. 목적 함수 설정
   └─> minimize Σ B_i × (1 - E_i)
       (자산 가치 × 생존 확률)

4. CBC 솔버 실행 (0.8초)
   └─> 최적 할당 결정
```

**result 구조**:
```python
result = {
    'feasible': True,
    'objective_value': 27.3,
    'upper_assignments': {
        'A05_T08': 'LSAM_03',     # LSAM layer
    },
    'lower_assignments': {
        'A05_T08': 'MSAM_03',     # MSAM layer
    },
    'solve_time': 0.8
}
```

#### 1-4. 최적화 결과 처리

```python
# [Line 1062-1082] 목적함수 값 추적
if result and result.get('feasible', False):
    obj_val = result.get('objective_value', 0.0)
    if obj_val != float('inf') and obj_val is not None:
        self.last_objective_value = obj_val

# [Line 1085-1097] 결과 처리
if result and result.get('feasible', False):
    self._process_optimization_results(result, solve_time)
    # 재할당 플래그 초기화
    for missile_id in self.missiles:
        if self.missiles[missile_id].get('needs_reassignment', False):
            self.missiles[missile_id]['needs_reassignment'] = False
else:
    # 최적화 실패 - 재할당 플래그 유지
    self.log_message("DWTA Infeasible - retrying next optimization", "WARNING")

self.last_optimization_step = self.current_time_step
```

```
📍 _process_optimization_results() 위치: Line 1230-1341
```

```python
def _process_optimization_results(self, result, solve_time):
    """Process comprehensive optimization results"""
    
    objective_value = result.get('objective_value', 0.0)
    
    # [Step 1] 최적화 히스토리 추적
    self.optimization_history.append(
        (self.current_time_step, objective_value, solve_time)
    )
    
    new_assignments = {}
    
    # [Step 2] 할당 결과 추출
    upper_assignments = result.get('upper_assignments', {})
    lower_assignments = result.get('lower_assignments', {})
    
    # Layer 접두사를 붙여서 통합
    all_assignments = {}
    for key, system_id in upper_assignments.items():
        all_assignments[f"upper_{key}"] = system_id
    for key, system_id in lower_assignments.items():
        all_assignments[f"lower_{key}"] = system_id
    
    # [Step 3] 각 할당 검증 및 처리
    assignment_count = 0
    invalid_assignments = 0
    
    for assignment_key, system_id in all_assignments.items():
        # Layer prefix 제거
        if assignment_key.startswith('upper_') or \
           assignment_key.startswith('lower_'):
            actual_key = assignment_key.split('_', 1)[1]
            layer_type = assignment_key.split('_', 1)[0]
        else:
            actual_key = assignment_key
            layer_type = "unknown"
        
        # 'asset_threat' 형식에서 분리
        parts = actual_key.split('_', 1)
        if len(parts) != 2:
            invalid_assignments += 1
            continue
        
        asset_id, threat_id = parts
        
        # 검증 1: 위협이 여전히 활성 상태인가?
        threat_exists = threat_id in self.missiles and \
                       self.missiles[threat_id]['active']
        
        # 검증 2: 시스템이 작동 가능한가?
        system_exists = any(b['id'] == system_id for b in self.batteries 
                           if b.get('status') == 'OPERATIONAL')
        
        if not threat_exists or not system_exists:
            invalid_assignments += 1
            continue
        
        # 유효한 할당 저장
        new_assignments[system_id] = threat_id
        assignment_count += 1
        
        # 로그 출력
        self.log_message(
            f"ASSIGN [{layer_type.upper()}]: {system_id} → {threat_id} "
            f"(targeting {asset_id})", "INFO"
        )
    
    # [Step 4] primary_assignments 업데이트
    self.primary_assignments = new_assignments
    
    # 요약 로그
    summary_msg = (f"[T={self.current_time_step}] Optimization complete: "
                  f"{assignment_count} assignments, {invalid_assignments} invalid, "
                  f"Obj={objective_value:.2f}, Time={solve_time:.2f}s")
    self.log_message(summary_msg, "INFO")
```

**할당 결과**:
```python
# 최적화 전
self.primary_assignments = {}

# 최적화 후
self.primary_assignments = {
    'LSAM_03': 'T08',  # LSAM_03 포대가 T08 위협 담당
    'MSAM_03': 'T08'   # MSAM_03 포대도 T08 위협 담당 (2층 방어)
}
```

---

### Step 2: update_simulation() - 물리 시뮬레이션 업데이트

```
📍 위치: multi_missile_tracker_gui.py, Line 773-807
```

```python
def update_simulation(self):
    """Advance simulation by one time step.
    
    시뮬레이션의 물리 엔진 부분입니다.
    매 루프마다:
    1. 시간 5초 진행
    2. 새로운 미사일 발사 여부 확인
    3. 비행 중인 미사일 위치 업데이트
    4. 요격 가능 범위에 도달한 미사일 처리
    """
    
    # [Line 775] ★ 시간 5초 진행
    # 시뮬레이션 시간을 매 루프마다 5초씩 증가
    # T=0 → T=5 → T=10 → ... → T=800
    self.current_time_step += 5
    
    # [Line 777] 동적 이벤트 시뮬레이션
    # 궤적 이탈 등 확률적 이벤트 처리
    self._simulate_dynamic_events()
    
    # [Line 779-807] 각 미사일 상태 업데이트
    # 모든 미사일을 순회하며 상태 업데이트
    active_count = 0  # 현재 비행 중인 미사일 개수
    for missile_id, missile in self.missiles.items():
        
        # [Line 782-785] ★ 미사일 발사 체크
        # 다음 조건을 모두 만족할 때 미사일 발사
        # 1. 아직 발사되지 않음 (active=False)
        # 2. 발사 시간에 도달 (current_time_step >= launch_time)
        # 3. 이미 처리되지 않음 (kill_results에 없음)
        if not missile['active'] and \
           self.current_time_step >= missile['launch_time'] and \
           missile_id not in self.kill_results:
            
            missile['active'] = True  # ← 미사일 활성화 (비행 시작!)
            self.log_message(f\"LAUNCH: {missile_id} → {missile['target_asset']}\")
        
        # [Line 787-807] 활성 미사일 처리
        # 비행 중인 미사일만 업데이트
        if missile['active']:
            active_count += 1
            
            # [Line 790-794] 비행 진행률 계산
            # 진행률: 0.0 (발사) ~ 1.0 (도착)
            time_in_flight = self.current_time_step - missile['launch_time']
            if missile['flight_time'] > 0:
                # 진행률 = 경과 시간 / 전체 비행 시간
                # min(..., 1.0): 1.0을 넘지 않도록 제한
                missile['flight_progress'] = min(
                    time_in_flight / missile['flight_time'],
                    1.0  # 최대값 1.0
                )
            else:
                missile['flight_progress'] = 1.0
            
            # [Line 796-797] 현재 위치 업데이트
            # 궤적은 100개의 waypoint로 이루어져 있음
            # 진행률에 따라 해당 waypoint를 현재 위치로 설정
            # 예: 진행률 0.5 → 궤적[50]이 현재 위치
            progress_idx = int(
                missile['flight_progress'] * (len(missile['trajectory']) - 1)
            )
            missile['position'] = missile['trajectory'][progress_idx]
            
            # [Line 799-801] ★ 교전 범위 진입 체크 (60% 이상)
            # 미사일이 비행 거리의 60% 지점에 도달하면 요격 범위 진입
            # 여기서부터 포대가 요격 시도 가능
            if missile['flight_progress'] >= 0.60:
                self._process_impact(missile_id, missile)
    
    # [Line 803] 활성 위협 수 업데이트
    # 통계에 현재 비행 중인 미사일 개수 저장
    self.stats['active'] = active_count
    
    # [Line 805-807] GUI 상태 업데이트
    # 화면에 현재 시간, 미사일 위치 등을 표시
    if self.control_panel:
        self.control_panel.update_status(self)
```

**시간 진행 예시**:
```
T=0:   T08 미사일 생성 (active=False, launch_time=5)
       
T=5:   T08 발사! (active=True, flight_progress=0.0)
       └─> 위치: trajectory[0] (발사 위치)
       
T=10:  flight_progress = (10-5)/480 = 0.0104 (1.04%)
       └─> 위치: trajectory[1]
       
T=290: flight_progress = (290-5)/480 = 0.594 (59.4%)
       └─> 위치: trajectory[59]
       
T=295: flight_progress = (295-5)/480 = 0.604 (60.4%)  ★ 교전 범위!
       └─> _process_impact() 호출!
```

#### 2-1. _simulate_dynamic_events() - 동적 이벤트 처리

```
📍 위치: Line 809-862
```

```python
def _simulate_dynamic_events(self):
    """Handles dynamic scenario changes including controlled retargeting events.
    
    시나리오의 동적 변화를 시뮬레이션합니다.
    현실적인 작전 환경을 반영하기 위해 확률적 이벤트를 처리합니다.
    """
    
    # 궤적 이탈 이벤트 (확률적)
    # 비행 중인 미사일이 실제 탄도 변화, ECM 등으로 인해
    # 원래 목표를 이탈하는 상황을 시뮬레이션
    for missile_id, missile in self.missiles.items():
        # 활성 미사일 중 재표적 가능한 미사일만 처리
        if missile['active'] and missile.get('can_retarget', True):
            # 비행 중반부(30-60%)에서만 궤적 이탈 가능
            # - 30%: 이른 단계 (탐지 어려움)
            # - 60%: 늦은 단계 (포대 요격 시간 불충분)
            # → 30-60% 구간이 이탈 가능 구간
            if 0.3 <= missile['flight_progress'] <= 0.6:
                # 매우 낮은 확률 (0.2%) 이탈 시뮬레이션
                # 대부분의 경우 정상 궤도 유지
                if random.random() < missile.get('retarget_probability', 0.002):
                    old_target = missile['target_asset']
                    
                    # 빈 공간으로 이탈 (목표 자산에서 ±20km)
                    # 목표를 완전히 회피하는 것이 아니라
                    # 근처의 빈 공간으로 이탈 → 요격 불가
                    deviation_x = missile['target_position'][0] + \
                                 random.uniform(-20, 20)  # -20~+20km 범위
                    deviation_y = missile['target_position'][1] + \
                                 random.uniform(-20, 20)
                    
                    # 목표 변경
                    missile['target_asset'] = 'EMPTY_AREA'  # 자산 아닌 빈 지역
                    missile['target_position'] = (deviation_x, deviation_y)
                    missile['target_changed'] += 1  # 재표적 횟수 증가
                    
                    # 새로운 목표로의 궤적 재계산
                    # 이탈 지점 → 빈 공간 위치로의 새 궤적
                    missile['trajectory'] = self._calculate_trajectory(
                        missile['position'], 
                        (deviation_x, deviation_y)
                    )
                    
                    # 할당 해제
                    for battery_id, threat_id in \
                        list(self.primary_assignments.items()):
                        if threat_id == missile_id:
                            del self.primary_assignments[battery_id]
                            self.log_message(
                                f"ABANDON: Battery {battery_id} abandons "
                                f"{missile_id} (trajectory deviation)", 
                                "WARNING"
                            )
                            break
                    
                    # 비활성화
                    missile['needs_reassignment'] = False
                    missile['active'] = False
                    self.stats['retargeted'] += 1
                    
                    self.log_message(
                        f"TRAJECTORY DEVIATION: {missile_id} veered off "
                        f"from {old_target} to empty area", "INFO"
                    )
```

**궤적 이탈 효과**:
```
Before:
  T08: target_asset='A05', active=True
  primary_assignments = {'LSAM_03': 'T08'}

After (0.2% 확률):
  T08: target_asset='EMPTY_AREA', active=False
  primary_assignments = {}  (할당 해제됨)
  stats['retargeted'] = 1
```

#### 2-2. _process_impact() - 요격 실행 및 결과 판정

```
📍 위치: Line 864-987
```

```python
def _process_impact(self, missile_id, missile):
    """Process missile impact with comprehensive shoot-look-shoot logic."""
    
    # [Line 867-870] 교전 시도 횟수 추적
    if missile_id not in self.engagement_attempts:
        self.engagement_attempts[missile_id] = 1
    else:
        self.engagement_attempts[missile_id] += 1
    
    current_attempt = self.engagement_attempts[missile_id]
    launch_failures = 0
    
    # [Line 876-879] ★ 할당된 포대 찾기
    assigned_batteries = []
    for battery_id, threat_id in self.primary_assignments.items():
        if threat_id == missile_id:
            assigned_batteries.append(battery_id)
    
    # [Line 882-888] 할당 없음 처리
    if not assigned_batteries:
        if missile['flight_progress'] < 0.75:  # 아직 교전 가능
            missile['needs_reassignment'] = True
            if self.shoot_look_shoot_enabled and \
               current_attempt < self.max_engagement_attempts:
                # 진행률 되돌려서 재교전 기회 제공
                missile['flight_progress'] = max(0.3, 
                    missile['flight_progress'] - 0.2)
                return
    
    # [Line 890-892] 생존 확률 초기화
    P_survival = 1.0
    missiles_fired = 0
    operational_batteries = 0
    
    # [Line 894-940] ★ 각 포대의 요격 시도
    for battery_id in assigned_batteries:
        battery = next((b for b in self.batteries 
                       if b['id'] == battery_id), None)
        
        if battery:
            # 포대 상태 확인
            battery_status = battery.get('status', 'UNKNOWN')
            battery_ammo = battery.get('available_missiles', 0)
            
            # 작동 가능하고 탄약 있으면 요격 시도
            if battery_status == 'OPERATIONAL' and battery_ammo > 0:
                operational_batteries += 1
                
                # [Line 915-916] ★ 탄약 소비
                battery['available_missiles'] -= 1
                missiles_fired += 1
                
                # [Line 918-924] 요격 확률 적용
                battery_specs = battery.get('specs', {})
                ballistic_specs = battery_specs.get(
                    'ballistic_missile_specs', {}
                )
                Pk_single = ballistic_specs.get(
                    'intercept_probability', 0.95
                )
                
                # 생존 확률 누적
                P_survival *= (1.0 - Pk_single)
                
                # [Line 932-940] 탄약 고갈 시 할당 해제
                if battery['available_missiles'] <= 0:
                    if battery_id in self.primary_assignments:
                        del self.primary_assignments[battery_id]
                    missile['needs_reassignment'] = True
                    self.log_message(
                        f"Battery {battery_id} OUT OF AMMO - "
                        f"reassignment needed for {missile_id}", 
                        "WARNING"
                    )
    
    # [Line 942-943] ★ 요격 성공 확률 계산
    P_kill = 1.0 - P_survival
    
    # [Line 945-987] ★ 확률적 결과 판정
    if missiles_fired > 0:
        # 랜덤 판정
        if random.random() < P_kill:
            # ═══════════════════════════════════════
            # ★ 요격 성공!
            # ═══════════════════════════════════════
            result = 'INTERCEPTED'
            missile['active'] = False
            
            # 통계 업데이트 (중복 방지)
            if missile_id not in [kr[0] for kr in self.kill_results.values()]:
                self.stats['intercepted'] += 1
            
            # 결과 기록
            self.kill_results[missile_id] = (result, self.current_time_step)
            
            self.log_message(
                f"IMPACT: {missile_id} INTERCEPTED (Pk={P_kill:.2f}, "
                f"Fired={missiles_fired}, Attempt={current_attempt})", 
                "SUCCESS"
            )
        
        else:
            # ═══════════════════════════════════════
            # ★ 요격 실패!
            # ═══════════════════════════════════════
            result = 'MISSED'
            
            # Shoot-Look-Shoot 재시도 가능?
            if self.shoot_look_shoot_enabled and \
               current_attempt < self.max_engagement_attempts:
                # 진행률 되돌려서 재교전
                missile['flight_progress'] = max(0.4, 
                    missile['flight_progress'] - 0.2)
                missile['needs_reassignment'] = False
                
                self.log_message(
                    f"IMPACT: {missile_id} MISSED - Shoot-Look-Shoot "
                    f"retry {current_attempt+1}/{self.max_engagement_attempts}", 
                    "WARNING"
                )
                return  # 재교전 준비
            
            else:
                # 최종 실패
                missile['active'] = False
                self.kill_results[missile_id] = (result, self.current_time_step)
                
                # 통계 업데이트 (중복 방지)
                if missile_id not in self.stats['tracked_misses']:
                    self.stats['missed'] += 1
                    self.stats['tracked_misses'].append(missile_id)
                
                self.log_message(
                    f"IMPACT: {missile_id} MISSED (Pk={P_kill:.2f}, "
                    f"Fired={missiles_fired}, Attempt={current_attempt}) "
                    f"-> Hit {missile['target_asset']}", 
                    "ERROR"
                )
```

**요격 확률 계산 예시**:
```python
# 예시 1: LSAM_03만 할당
P_survival = 1.0
P_survival *= (1 - 0.95)  # LSAM_03 요격 시도
P_survival = 0.05
P_kill = 1 - 0.05 = 0.95 (95%)

# 예시 2: LSAM_03 + MSAM_03 모두 할당 (2층 방어)
P_survival = 1.0
P_survival *= (1 - 0.95)  # LSAM_03 요격 시도
P_survival *= (1 - 0.97)  # MSAM_03 요격 시도
P_survival = 0.05 × 0.03 = 0.0015
P_kill = 1 - 0.0015 = 0.9985 (99.85%)
```

**Shoot-Look-Shoot 예시**:
```
시도 1 (T=295):
  ├─> flight_progress = 0.604
  ├─> 요격 시도: P_kill = 0.95
  ├─> 판정: random() = 0.97 > 0.95 → MISS!
  └─> flight_progress = 0.4 (되돌림) → 재교전 준비

시도 2 (T=390):
  ├─> flight_progress = 0.604 (다시 도달)
  ├─> 요격 시도: P_kill = 0.95
  ├─> 판정: random() = 0.32 < 0.95 → SUCCESS!
  └─> missile['active'] = False (위협 제거)
```

---

### Step 3: check_events() - 이벤트 확인 및 로깅

```
📍 위치: Line 444-454
```

```python
def check_events(self, prev_stats, current_stats):
    """이벤트 확인 및 로깅"""
    
    # 요격 성공 이벤트
    if current_stats['intercepted'] > prev_stats['intercepted']:
        self.control_window.after(0, lambda: 
            self.log_message("요격 성공!", "INTERCEPT")
        )
    
    # 요격 실패 이벤트
    if current_stats['missed'] > prev_stats['missed']:
        self.control_window.after(0, lambda: 
            self.log_message("요격 실패", "WARNING")
        )
    
    # 새 위협 감지 이벤트
    if current_stats['active'] > prev_stats['active']:
        new_threats = current_stats['active'] - prev_stats['active']
        self.control_window.after(0, lambda: 
            self.log_message(f"{new_threats}개 새로운 위협 발견", "INFO")
        )
```

**스레드 안전성**:
- `control_window.after(0, ...)`: Main Thread에서 GUI 업데이트 예약
- Simulation Thread에서 직접 GUI 접근 금지

---

### Step 4: should_terminate() - 종료 조건 확인

```
📍 위치: Line 456-466
```

```python
def should_terminate(self):
    """종료 조건 확인"""
    
    # [조건 1] 최대 시간 도달
    if self.tracker.current_time_step >= self.max_duration_var.get():
        return True
    
    # [조건 2] 모든 위협이 발사됨
    all_threats_launched = all(
        missile['launch_time'] <= self.tracker.current_time_step 
        for missile in self.tracker.missiles.values()
    )
    
    # [조건 3] 모든 위협이 처리됨
    all_threats_resolved = \
        len(self.tracker.kill_results) == self.tracker.stats['total']
    
    # [조건 4] 활성 위협 없음
    no_active_threats = self.tracker.stats['active'] == 0
    
    # 모든 조건 만족 시 종료
    return all_threats_launched and all_threats_resolved and no_active_threats
```

**종료 조건 예시**:
```
T=795:
  ├─> all_threats_launched = True  (모든 미사일 발사됨)
  ├─> all_threats_resolved = True  (15/15 처리 완료)
  ├─> no_active_threats = True     (active=0)
  └─> should_terminate() = True → 시뮬레이션 종료!
```

---

### Step 5: 속도 조절 및 루프 반복

```python
# [Line 437] 시뮬레이션 속도 조절
time.sleep(0.1 / self.speed_var.get())
```

**속도 예시**:
```
speed_var = 1.0:  sleep(0.1) → 1배속
speed_var = 2.0:  sleep(0.05) → 2배속
speed_var = 0.5:  sleep(0.2) → 0.5배속
```

---

## 시나리오 종료 처리

### 1단계: simulation_finished() 호출

```
📍 위치: Line 442, 511-532
```

```python
# run_simulation_thread() finally 블록
finally:
    self.control_window.after(0, self.simulation_finished)
```

```python
def simulation_finished(self):
    """시뮬레이션 완료"""
    
    # [Line 513] 상태 플래그 업데이트
    self.running = False
    
    # [Line 515-517] 버튼 상태 복원
    self.start_btn.config(state="normal")
    self.pause_btn.config(state="disabled", text="일시정지")
    self.stop_btn.config(state="disabled")
    
    # [Line 519-522] 최종 통계 계산
    stats = self.tracker.stats
    total = stats['total']
    success_rate = (stats['intercepted'] / total * 100) if total > 0 else 0
    
    # [Line 524-529] 결과 다이얼로그 표시
    result_msg = f"""시뮬레이션 완료!
    
총 위협: {total}
요격 성공: {stats['intercepted']}
요격 실패: {stats['missed']}
성공률: {success_rate:.1f}%"""
    
    messagebox.showinfo("시뮬레이션 완료", result_msg)
    self.log_message("시뮬레이션 완료", "SUCCESS")
```

**최종 결과 예시**:
```
┌─────────────────────────────┐
│   시뮬레이션 완료!          │
│                              │
│ 총 위협: 15                  │
│ 요격 성공: 13                │
│ 요격 실패: 1                 │
│ 궤적 이탈: 1                 │
│ 성공률: 86.7%                │
└─────────────────────────────┘
```

---

## 코드 실행 타임라인

### 전체 타임라인 (T=0 ~ T=800)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Timeline: GUI Button Click → Scenario End                                  │
└────────────────────────────────────────────────────────────────────────────┘

[T=-1초] 사용자 버튼 클릭
   ├─> start_simulation()
   │     ├─> running = True
   │     ├─> start_btn.config(state="disabled")
   │     └─> threading.Thread.start()
   │           └─> run_simulation_thread() 시작 (별도 스레드)
   │
   └─> Main Thread: Tkinter 이벤트 루프 계속 실행
       └─> GUI 반응성 유지

[T=0초] 시나리오 초기화
   └─> start_scenario()
       ├─> self.current_time_step = 0
       ├─> self.missiles 초기화 (15개)
       │     ├─> T01~T08: Nodong (launch_time=5~95, flight_time=480s)
       │     └─> T09~T15: Scud-B (launch_time=5~95, flight_time=240s)
       └─> self.stats = {total:15, active:0, intercepted:0, missed:0}

[T=5초] 첫 미사일 발사 + 첫 최적화
   ├─> update_simulation()
   │     └─> T08['active'] = True (발사!)
   │           └─> LOG: "LAUNCH: T08 → A05"
   │
   └─> run_realtime_dwta()
       ├─> _prepare_optimizer_inputs()
       │     ├─> assets_opt = [A05(value=720)]
       │     ├─> systems_opt = [LSAM_03, MSAM_03, ...]
       │     └─> threats_opt = [T08]
       │
       ├─> optimizer.solve() (0.8초)
       │     └─> result = {'upper_assignments': {'A05_T08': 'LSAM_03'},
       │                   'lower_assignments': {'A05_T08': 'MSAM_03'}}
       │
       └─> _process_optimization_results()
             └─> self.primary_assignments = {
                   'LSAM_03': 'T08',
                   'MSAM_03': 'T08'
                 }
                 └─> LOG: "ASSIGN [UPPER]: LSAM_03 → T08 (targeting A05)"
                 └─> LOG: "ASSIGN [LOWER]: MSAM_03 → T08 (targeting A05)"

[T=10초~T=290초] 미사일 비행 + 주기적 최적화
   └─> (매 5초마다 반복)
       ├─> update_simulation()
       │     ├─> T08['flight_progress'] 증가
       │     └─> T08['position'] 업데이트 (궤적 추적)
       │
       └─> run_realtime_dwta() (필요시)
             └─> 새 위협 발사 시 재최적화

[T=295초] 교전 범위 진입 (flight_progress=60.4%)
   └─> _process_impact(T08)
       ├─> assigned_batteries = ['LSAM_03', 'MSAM_03']
       │
       ├─> LSAM_03 요격 시도:
       │     ├─> available_missiles: 20 → 19
       │     └─> P_survival *= (1 - 0.95) = 0.05
       │
       ├─> MSAM_03 요격 시도:
       │     ├─> available_missiles: 30 → 29
       │     └─> P_survival *= (1 - 0.97) = 0.0015
       │
       ├─> P_kill = 1 - 0.0015 = 0.9985 (99.85%)
       │
       └─> 확률 판정:
             ├─> random.random() = 0.3421 < 0.9985
             ├─> result = 'INTERCEPTED' ✓
             ├─> T08['active'] = False
             ├─> stats['intercepted'] += 1
             └─> LOG: "IMPACT: T08 INTERCEPTED (Pk=0.9985, Fired=2)"

[T=300초~T=795초] 나머지 위협 처리
   └─> 동일 프로세스 반복
       ├─> T09~T15 순차적 발사
       ├─> 주기적 DWTA 최적화
       ├─> 교전 및 요격 판정
       └─> 일부 실패 시 Shoot-Look-Shoot 재시도

[T=800초] 시나리오 종료
   ├─> should_terminate()
   │     ├─> all_threats_launched = True
   │     ├─> all_threats_resolved = True
   │     └─> no_active_threats = True
   │           └─> return True
   │
   └─> run_simulation_thread() 종료
       └─> finally: simulation_finished()
             ├─> running = False
             ├─> messagebox.showinfo("시뮬레이션 완료")
             │     └─> 총 위협: 15
             │         요격 성공: 13
             │         요격 실패: 1
             │         궤적 이탈: 1
             │         성공률: 86.7%
             │
             └─> GUI 버튼 상태 복원
```

---

## 스레드 안전성 및 GUI 업데이트

### 스레드 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│ Main Thread (Tkinter)                                                │
├─────────────────────────────────────────────────────────────────────┤
│ • GUI 이벤트 루프 (버튼 클릭, 위젯 업데이트)                       │
│ • control_panel.update_status()                                     │
│ • control_panel.log_message()                                       │
│ • messagebox.showinfo()                                             │
└─────────────────────────────────────────────────────────────────────┘
         ↕ (control_window.after() 사용)
┌─────────────────────────────────────────────────────────────────────┐
│ Simulation Thread (Background)                                       │
├─────────────────────────────────────────────────────────────────────┤
│ • run_simulation_thread()                                           │
│   ├─> run_realtime_dwta()                                           │
│   ├─> update_simulation()                                           │
│   └─> check_events()                                                │
│                                                                      │
│ • NonLinearMIPOptimizer.solve() (CPU 집약적)                        │
│ • 물리 계산, 궤적 업데이트                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### GUI 업데이트 메커니즘

```python
# ❌ 잘못된 방법: Simulation Thread에서 직접 GUI 접근
def update_simulation(self):
    ...
    self.control_panel.log_text.insert(tk.END, "메시지")  # 오류 발생!

# ✓ 올바른 방법: after()로 Main Thread에 작업 예약
def update_simulation(self):
    ...
    self.control_panel.control_window.after(0, lambda:
        self.control_panel.log_message("메시지")
    )
```

**after() 동작 원리**:
```
Simulation Thread:
  └─> control_window.after(0, callback)
        └─> Main Thread의 이벤트 큐에 추가
              └─> Main Thread가 다음 이벤트 루프에서 실행
                    └─> callback() 실행 (안전!)
```

### 상태 변수 동기화

```python
# 스레드 간 공유 변수
self.running = True/False       # 시뮬레이션 실행 여부
self.paused = True/False        # 일시정지 여부
self.speed_var.get()           # 시뮬레이션 속도

# Main Thread에서 변경
def pause_simulation(self):
    self.paused = not self.paused  # ← Main Thread

# Simulation Thread에서 읽기
def run_simulation_thread(self):
    while self.running:
        if not self.paused:  # ← Simulation Thread
            ...
```

**변경 안전성**:
- Python GIL(Global Interpreter Lock)로 기본적인 스레드 안전성 보장
- 단순 bool 변수는 안전하게 읽기/쓰기 가능
- 복잡한 데이터 구조는 Lock 필요 (여기서는 불필요)

---

## 주요 데이터 구조 스냅샷

### T=0 (초기화 완료)
```python
self.missiles = {
    'T08': {
        'id': 'T08',
        'position': (0, 0),
        'target_asset': 'A05',
        'launch_time': 5,
        'flight_time': 480,
        'active': False,
        'flight_progress': 0.0,
        'needs_reassignment': False
    },
    # ... T01~T15
}

self.primary_assignments = {}

self.stats = {
    'total': 15,
    'active': 0,
    'intercepted': 0,
    'missed': 0,
    'retargeted': 0,
    'tracked_misses': []
}
```

### T=5 (첫 최적화 후)
```python
self.missiles = {
    'T08': {
        'active': True,  # ← 변경
        'flight_progress': 0.0,
        # ... 나머지 동일
    }
}

self.primary_assignments = {
    'LSAM_03': 'T08',  # ← 추가
    'MSAM_03': 'T08'   # ← 추가
}

self.stats = {
    'total': 15,
    'active': 1,  # ← 증가
    'intercepted': 0,
    'missed': 0
}
```

### T=295 (요격 성공 후)
```python
self.missiles = {
    'T08': {
        'active': False,  # ← 변경 (위협 제거)
        'flight_progress': 0.604,
        # ...
    }
}

self.kill_results = {
    'T08': ('INTERCEPTED', 295)  # ← 추가
}

self.batteries = [
    {
        'id': 'LSAM_03',
        'available_missiles': 19,  # ← 20에서 감소
        # ...
    },
    {
        'id': 'MSAM_03',
        'available_missiles': 29,  # ← 30에서 감소
        # ...
    }
]

self.stats = {
    'total': 15,
    'active': 0,  # ← 감소
    'intercepted': 1,  # ← 증가
    'missed': 0
}
```

---

## 성능 및 최적화 고려사항

### 계산 병목 지점

```
전체 루프 시간 = 0.1초

├─> run_realtime_dwta(): ~0.8초 (병목!)
│     ├─> _prepare_optimizer_inputs(): ~0.01초
│     ├─> optimizer.solve(): ~0.8초 ★ 주요 병목
│     └─> _process_optimization_results(): ~0.01초
│
├─> update_simulation(): ~0.001초
│     ├─> _simulate_dynamic_events(): ~0.0001초
│     └─> _process_impact(): ~0.0001초
│
└─> check_events(): ~0.0001초
```

**최적화 전략**:
1. **최적화 간격**: 1초마다만 실행 (매 루프 아님)
2. **타임아웃**: 15초 초과 시 중단
3. **데드락 방지**: 같은 타임스텝에서 최대 횟수 제한

### 메모리 사용

```python
# 시나리오 규모
missiles: 15개 × ~500 bytes = ~7.5 KB
batteries: 10개 × ~2 KB = ~20 KB
assets: 10개 × ~500 bytes = ~5 KB
trajectories: 15개 × 100 waypoints × 16 bytes = ~24 KB
optimization_history: ~800 entries × ~50 bytes = ~40 KB

총 메모리: ~100 KB (매우 경량)
```

---

## 문제 해결 가이드

### 1. 시뮬레이션이 멈춤 (데드락)

**증상**:
- GUI는 반응하지만 시간이 진행 안 됨
- 로그가 멈춤

**원인**:
- 최적화가 무한 루프에 빠짐

**해결**:
- 15초 타임아웃 작동 확인
- `max_optimizations_per_timestep` 설정 확인

### 2. 요격이 안 됨

**증상**:
- 미사일이 발사되지만 요격 시도 없음

**원인**:
- 할당이 안 됨 (`primary_assignments` 비어있음)

**체크리스트**:
```python
# 1. 최적화 실행 확인
run_realtime_dwta() 호출 확인

# 2. 포대 상태 확인
battery['status'] == 'OPERATIONAL'
battery['available_missiles'] > 0

# 3. 할당 결과 확인
self.primary_assignments != {}
```

### 3. GUI가 응답 없음

**증상**:
- 버튼 클릭 안 됨
- 창 움직임 안 됨

**원인**:
- Main Thread가 블록됨
- Simulation Thread에서 GUI 직접 접근

**해결**:
```python
# ❌ 잘못
self.control_panel.log_text.insert(...)

# ✓ 올바름
self.control_panel.control_window.after(0, lambda:
    self.control_panel.log_message(...)
)
```

---

## 결론

이 문서는 DWTA GUI 시뮬레이션의 **완전한 실행 흐름**을 다음과 같이 추적했습니다:

1. **시작**: 버튼 클릭 → 스레드 생성 → 시나리오 초기화
2. **메인 루프**: DWTA 최적화 → 물리 업데이트 → 이벤트 처리
3. **종료**: 조건 만족 → 스레드 종료 → 결과 표시

**핵심 설계 원칙**:
- ✓ 스레드 분리로 GUI 반응성 유지
- ✓ 실시간 최적화로 동적 상황 대응
- ✓ Shoot-Look-Shoot로 재교전 기회 제공
- ✓ 확률적 판정으로 현실성 반영

**코드 품질**:
- 명확한 함수 분리 (단일 책임 원칙)
- 스레드 안전성 보장 (after() 사용)
- 강력한 오류 처리 (try-except-finally)
- 상세한 로깅 (디버깅 용이)

이 시스템은 실제 미사일 방어 작전의 핵심 요소들을 충실히 시뮬레이션하며, 교육 및 연구 목적으로 활용 가능합니다.
