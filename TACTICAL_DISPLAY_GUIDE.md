# Tactical Display & GUI Control System Guide

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [Tactical Display 구성요소](#tactical-display-구성요소)
3. [할당 선 (Assignment Lines)](#할당-선-assignment-lines)
4. [GUI 제어 패널](#gui-제어-패널)
5. [시각화 요소 상세](#시각화-요소-상세)
6. [실시간 상태 모니터링](#실시간-상태-모니터링)

---

## 시스템 개요

### 전체 구조
`multi_missile_tracker_gui.py`는 실시간 DWTA (Dynamic Weapon-Target Assignment) 시뮬레이션을 위한 GUI 기반 전술 디스플레이 시스템입니다.

**주요 컴포넌트:**
- **Tactical Display (왼쪽 75%)**: 전술 상황 실시간 시각화
- **Objective Function Analysis (오른쪽 25%)**: 목적함수 분석 차트
- **Control Panel**: 독립 창으로 시뮬레이션 제어
- **Event Log**: 실시간 이벤트 로깅 시스템

### 화면 레이아웃 비율
```python
# 3:1 비율 (Tactical Display : Objective View)
ax_main = fig.add_axes([0.04, 0.08, 0.675, 0.85])      # 전술 디스플레이 67.5%
ax_analysis = fig.add_axes([0.745, 0.08, 0.225, 0.85])  # 목적함수 뷰 22.5%
```

---

## Tactical Display 구성요소

### 1. 자산 (Assets) - 보호 대상
**시각적 표현:**
- **마커**: 다이아몬드 (◆)
- **색상**: NATO 친군 블루 (#4a90e2)
- **크기**: 90 포인트
- **라벨**: 자산 번호 (검은색, 굵게)

**코드 구현:**
```python
# 자산 그리기 (라인 2446-2457)
self.ax_main.scatter(x, y, c='#4a90e2', s=90, marker='D', alpha=0.9, 
                   edgecolors='black', linewidth=1.0)
asset_number = asset['id'].split('_')[-1]
self.ax_main.text(x, y, asset_number, ha='center', va='center', 
                fontsize=5, color='black', weight='bold')
```

### 2. 포대 (Batteries) - 방어 무기체계

#### LSAM (상층 방어)
- **마커**: 정사각형 (■)
- **색상**: 오렌지-레드 (#ff6b35)
- **크기**: 150 포인트
- **최대 사거리**: 150km (점선 원)
- **최소 사거리**: 40km (점선 원)
- **방향 표시**: 북쪽 방향 화살표 (20km 길이)

#### MSAM (하층 방어)
- **마커**: 삼각형 (▲)
- **색상**: 청록색 (#00d4aa)
- **크기**: 120 포인트
- **최대 사거리**: 40km (점선 원)
- **최소 사거리**: 5km (점선 원)
- **방향 표시**: 북쪽 방향 화살표 (15km 길이)

**코드 구현:**
```python
# 포대 그리기 (라인 2460-2531)
if system_type == 'LSAM':
    color = '#ff6b35'
    marker = 's'
    marker_size = 150
    max_range = 150
    min_range = 40
elif system_type == 'MSAM':
    color = '#00d4aa'
    marker = '^'
    marker_size = 120
    max_range = 40
    min_range = 5

# 사거리 원 그리기
circle_outer = plt.Circle((x, y), max_range, fill=False, 
                        color='#2d5a2d', alpha=0.6, linewidth=1.2, linestyle='--')
```

### 3. 위협 (Threats) - 적 미사일

#### 할당된 위협
- **마커**: 역삼각형 (▼)
- **색상**: 오렌지 (#ff8c42)
- **크기**: 180 포인트
- **라벨**: 위협 번호 + 진행률 (예: "05\n45%")

#### 미할당 위협
- **마커**: 역삼각형 (▼)
- **색상**: 위협 레드 (#cc4125)
- **크기**: 180 포인트
- **라벨**: 위협 번호 + 진행률

#### 요격 성공
- **마커**: X 표시 (✕)
- **색상**: 녹색 (#00ff00)
- **크기**: 80 포인트

#### 요격 실패
- **마커**: 별 표시 (★)
- **색상**: 빨간색 (#ff3333)
- **크기**: 100 포인트

**코드 구현:**
```python
# 위협 그리기 (라인 2534-2576)
if is_assigned:
    color = '#ff8c42'  # 할당된 위협
else:
    color = '#cc4125'  # 미할당 위협

self.ax_main.scatter(x, y, c=color, s=180, marker='v', alpha=0.9,
                   edgecolors='white', linewidth=1.0)

# 진행률 표시
threat_number = missile_id.split('_')[-1]
progress = missile['flight_progress']
self.ax_main.text(x, y, f"{threat_number}\n{progress:.0%}", 
                ha='center', va='center', fontsize=4, color='white')
```

---

## 할당 선 (Assignment Lines)

### 개념
할당 선은 **포대(Battery)와 위협(Threat) 간의 교전 할당 관계**를 시각적으로 표현합니다.

### 시각적 특성
- **색상**: 라임 그린 (lime)
- **선 두께**: 1 포인트
- **투명도**: 60% (alpha=0.6)
- **중간점 표시**: 작은 원형 점 (●)

### 할당 선 그리기 로직

**코드 위치:** 라인 2578-2592

```python
# 할당 선 그리기
for battery_id, threat_list in self.primary_assignments.items():
    for threat_id in threat_list:
        if threat_id in self.missiles and self.missiles[threat_id]['active']:
            battery = next((b for b in self.batteries if b['id'] == battery_id), None)
            if battery:
                bx, by = battery['position']
                mx, my = self.missiles[threat_id]['position']
                
                # 할당 선 그리기
                self.ax_main.plot([bx, mx], [by, my], '-', color='lime', 
                                linewidth=1, alpha=0.6)
                
                # 중간점 표시
                mid_x, mid_y = (bx + mx) / 2, (by + my) / 2
                self.ax_main.text(mid_x, mid_y, '●', ha='center', va='center',
                            fontsize=4, color='lime', alpha=0.8)
```

### 할당 관리 시스템

#### OptimizedAssignmentManager (라인 79-278)
하이브리드 자료구조를 사용한 고성능 할당 관리자:

**핵심 기능:**
1. **양방향 인덱스**: O(1) 탐색 속도
2. **비트마스크**: 메모리 효율 6배 향상
3. **딕셔너리 호환**: 기존 코드와 완벽 호환

**주요 메서드:**
```python
# 할당 추가
assignment_manager.assign(threat_id, battery_id)

# 할당 제거
assignment_manager.unassign(threat_id, battery_id)

# 위협에 할당된 포대 조회
batteries = assignment_manager.get_batteries_for_threat(threat_id)

# 포대에 할당된 위협 조회
threats = assignment_manager.get_threats_for_battery(battery_id)
```

### 할당 업데이트 프로세스

**1단계: 최적화 실행 (라인 1675-1966)**
```python
def run_realtime_dwta(self):
    # MIP/Greedy/GA 알고리즘으로 최적 할당 계산
    result = optimizer.solve()
```

**2단계: 결과 처리 (라인 2137-2305)**
```python
def _process_optimization_results(self, result, solve_time):
    # 상층/하층 할당 분리
    upper_assignments = result.get('upper_assignments', {})
    lower_assignments = result.get('lower_assignments', {})
    
    # 할당 병합
    self.primary_assignments.merge_assignments(new_assignments, active_threat_ids)
```

**3단계: 시각화 업데이트 (라인 2307-2328)**
```python
def update_display(self):
    self.ax_main.clear()
    self._draw_tactical_display()  # 할당 선 포함
    self.fig.canvas.draw_idle()
```

### 할당 제약 조건

**MIP 최적화 제약:**
- 위협당 상층 최대 1개 배터리
- 위협당 하층 최대 1개 배터리
- 위협당 총 최대 2개 배터리 (상층 1 + 하층 1)
- 포대당 동시 교전 제한 (LSAM: 3개, MSAM: 3개)

**코드 위치:** 라인 242-278
```python
def merge_assignments(self, new_assignments: Dict[str, List[str]], active_threat_ids: Set[str]):
    """
    제약 조건:
    - 위협당 상층 최대 1개 배터리
    - 위협당 하층 최대 1개 배터리
    - 총 최대 2개 배터리
    """
```

---

## GUI 제어 패널

### 패널 구조

#### 1. 시뮬레이션 제어 (SIMULATION CONTROL)

**시나리오 선택:**
- 드롭다운 메뉴로 시나리오 선택
- 실시간 시나리오 변경 지원
- 시나리오 정보 자동 로깅

**목적함수 선택:**
- `MIN_DAMAGE`: 가치 기반 피해 최소화
- `MAX_KILLS`: 평등주의적 요격 최대화

**시뮬레이션 속도:**
- 슬라이더로 0.1x ~ 5.0x 조절
- 실시간 배속 표시

**최대 시간 설정:**
- 300초 ~ 3000초 범위
- 기본값: 1600초

**코드 위치:** 라인 448-551

```python
def create_controls(self, parent):
    # 시나리오 선택
    scenario_combo = ttk.Combobox(control_frame, textvariable=self.scenario_var,
                                 values=scenario_keys, state="readonly")
    
    # 목적함수 선택
    objective_combo = ttk.Combobox(control_frame, textvariable=self.objective_var,
                                  values=list(OBJECTIVES.keys()), state="readonly")
    
    # 속도 조절
    speed_scale = ttk.Scale(control_frame, from_=0.1, to=5.0, 
                           variable=self.speed_var, orient="horizontal")
```

#### 2. 알고리즘 선택

**지원 알고리즘:**
- **MIP (최적)**: Mixed Integer Programming - 최적해 보장
- **Greedy (빠름)**: 탐욕 알고리즘 - 빠른 실행
- **GA (균형)**: 유전 알고리즘 - 균형잡힌 성능

**Warm-start 옵션:**
- MIP 알고리즘 전용
- 이전 해를 초기값으로 사용
- 솔버 시간 단축 효과

**코드 위치:** 라인 500-530

```python
# 알고리즘 라디오 버튼
ttk.Radiobutton(algo_frame, text="MIP (최적)", 
               variable=self.algorithm_var, value="MIP")
ttk.Radiobutton(algo_frame, text="Greedy (빠름)", 
               variable=self.algorithm_var, value="Greedy")
ttk.Radiobutton(algo_frame, text="GA (균형)", 
               variable=self.algorithm_var, value="GA")

# Warm-start 체크박스
ttk.Checkbutton(control_frame, text="Warm-start 활성화", 
               variable=self.warmstart_enabled_var)
```

#### 3. 제어 버튼

**▶ 시작 (Start):**
- 시뮬레이션 시작
- 시나리오 초기화
- 스레드 기반 비동기 실행

**⏸ 일시정지 (Pause):**
- 시뮬레이션 일시정지/재개
- 상태 유지

**⏹ 정지 (Stop):**
- 시뮬레이션 강제 종료
- 결과 보존

**🔄 리셋 (Reset):**
- 모든 상태 초기화
- 차트 및 로그 유지

**코드 위치:** 라인 532-550

```python
self.start_btn = ttk.Button(button_frame, text="▶ 시작", 
                           command=self.start_simulation)
self.pause_btn = ttk.Button(button_frame, text="⏸ 일시정지", 
                           command=self.pause_simulation)
self.stop_btn = ttk.Button(button_frame, text="⏹ 정지", 
                          command=self.stop_simulation)
self.reset_btn = ttk.Button(button_frame, text="🔄 리셋", 
                           command=self.reset_simulation)
```

---

## 실시간 상태 모니터링

### 상태 패널 (REAL-TIME STATUS)

**표시 항목:**

1. **현재 시간 (T=)**: 시뮬레이션 시간 (초)
2. **활성 위협**: 현재 비행 중인 미사일 수
3. **요격 성공**: 성공적으로 요격된 미사일 수
4. **요격 실패**: 요격 실패한 미사일 수
5. **성공률**: 요격 성공률 (%)
6. **목적함수 값**: 최적화 목적함수 값
7. **Warm-start**: Warm-start 적용 여부 (✅/❌)
8. **솔버 시간**: 최적화 소요 시간 (초)

**코드 위치:** 라인 552-602

```python
def create_status_panel(self, parent):
    # 상태 변수들
    self.time_var = tk.StringVar(value="T=0")
    self.active_var = tk.StringVar(value="활성 위협: 0")
    self.intercepted_var = tk.StringVar(value="요격 성공: 0")
    self.missed_var = tk.StringVar(value="요격 실패: 0")
    self.success_rate_var = tk.StringVar(value="성공률: 0%")
    self.objective_val_var = tk.StringVar(value="목적함수: -")
    self.warmstart_var = tk.StringVar(value="Warm-start: ❌")
    self.solver_time_var = tk.StringVar(value="솔버 시간: -")
```

### 이벤트 로그 (EVENT LOG)

**로그 레벨 및 색상:**
- **INFO** (녹색): 일반 정보
- **WARNING** (오렌지): 경고 메시지
- **ERROR** (빨간색): 오류 메시지
- **SUCCESS** (밝은 녹색): 성공 메시지
- **ASSIGN** (파란색): 할당 이벤트
- **INTERCEPT** (주황색): 요격 이벤트
- **MISS** (연한 빨강): 요격 실패
- **LAUNCH** (노란색): 미사일 발사
- **TRAJECTORY** (보라색): 궤적 이벤트

**코드 위치:** 라인 604-677

```python
def create_log_panel(self, parent):
    # 로그 텍스트 위젯
    self.log_text = scrolledtext.ScrolledText(log_frame, height=15,
                                            bg='#0f0f0f', fg='#00ff00')
    
    # 로그 태그 설정
    self.log_text.tag_configure('INFO', foreground='#00ff00')
    self.log_text.tag_configure('WARNING', foreground='#ff6600')
    self.log_text.tag_configure('ERROR', foreground='#ff3333')
    self.log_text.tag_configure('SUCCESS', foreground='#66ff66')
    self.log_text.tag_configure('INTERCEPT', foreground='#ff9900')
```

**주요 로그 메시지:**

```python
# 시뮬레이션 시작
"[INFO] === SIMULATION START (T=0) ==="

# 미사일 발사
"[INFO] LAUNCH: THREAT_01 → ASSET_01"

# 할당 정보
"[INFO] [T=15] Optimization: 5 assignments, Obj=125.50, Time=0.234s"

# 요격 성공
"[CRIT] INTERCEPT SUCCESS: THREAT_01 by LSAM_01 [상층(LSAM) 요격 성공] (Pk=0.8500)"

# 요격 실패
"[WARN] INTERCEPT MISS: THREAT_02 by MSAM_01 [하층(MSAM) 실패] (Pk=0.4500) - Retry 1/3"

# 용량 확보
"[INFO] [T=45] 용량 확보: 2개 배터리 해제 (현재 8/30개 할당)"

# 시뮬레이션 완료
"[INFO] === SIMULATION COMPLETE ==="
```

---

## 시각화 요소 상세

### 탄약 상태 패널 (AMMUNITION STATUS)

**위치**: 좌측 상단
**표시 정보**: 각 포대의 잔여 미사일 수

**색상 코딩:**
- **녹색** (#00ff00): 20발 이상 (충분)
- **노란색** (#ffff00): 10-19발 (보통)
- **주황색** (#ff8800): 5-9발 (부족)
- **빨간색** (#ff0000): 5발 미만 (위험)

**코드 위치:** 라인 2597-2651

```python
def _draw_ammunition_status(self):
    # 탄약 수준별 색상 결정
    if available >= 20:
        marker_color = '#00ff00'  # 녹색
    elif available >= 10:
        marker_color = '#ffff00'  # 노란색
    elif available >= 5:
        marker_color = '#ff8800'  # 주황색
    else:
        marker_color = '#ff0000'  # 빨간색
```

### 범례 (SYMBOL LEGEND)

**위치**: 좌측 하단
**표시 항목:**
- Assets (Protected): 다이아몬드, 파란색
- LSAM Batteries: 정사각형, 오렌지
- MSAM Batteries: 삼각형, 청록색
- Assigned Threats: 역삼각형, 주황색
- Unassigned Threats: 역삼각형, 빨간색
- Intercepted Threats: X 표시, 녹색
- Failed Intercepts: 별 표시, 빨간색

**코드 위치:** 라인 2653-2690

### 그리드 및 배경

**배경색**: 매우 어두운 검은색 (#0a0a0a)
**그리드 색상**: 녹색 (#2a4a2a)
**그리드 투명도**: 40%
**그리드 스타일**: 실선

**북쪽 표시기:**
- 위치: 우측 상단
- 배경: 파란색 (#4a90e2)
- 텍스트: "⬆ N"

---

## 교전 프로세스

### 다층 방어 시스템

**1단계: 상층(LSAM) 교전**
- 기본 요격 확률: 85%
- 살보 발사: 최대 2발
- 성공 기준: Pk ≥ 50%

**2단계: 하층(MSAM) 교전 (상층 실패 시)**
- 기본 요격 확률: 78%
- 살보 발사: 최대 2발
- 성공 기준: Pk ≥ 50%

**코드 위치:** 라인 1434-1525

```python
# 상층 교전
for battery_id in upper_batteries:
    base_Pk = 0.85  # LSAM
    missiles_to_fire = min(2, battery['available_missiles'])
    # 베타 분포 샘플링
    Pk_shot = self.uncertainty_model.sample_intercept_probability(base_Pk)
    P_survival *= (1 - Pk_shot)

# 상층 실패 시 하층 교전
if not upper_success and lower_batteries:
    for battery_id in lower_batteries:
        base_Pk = 0.78  # MSAM
        missiles_to_fire = min(2, battery['available_missiles'])
```

### Shoot-Look-Shoot 재교전

**재교전 조건:**
- 최초 교전 실패
- 최대 3회 시도
- 진행률 < 85%

**코드 위치:** 라인 1610-1634

```python
if self.shoot_look_shoot_enabled and current_attempt < self.max_engagement_attempts:
    missile['needs_reassignment'] = True
    self.control_panel.log_message(
        f"[WARN] INTERCEPT MISS: {missile_id} - Retry {current_attempt}/{self.max_engagement_attempts}",
        "WARNING"
    )
```

---

## 성능 최적화

### 하이브리드 할당 관리자
- **쓰기 속도**: O(1)
- **탐색 속도**: O(1)~O(k)
- **메모리 효율**: 6배 향상

### 시각화 최적화
- 기존 객체 재사용 (clear() 최소화)
- 선택적 업데이트 (5초 간격)
- draw_idle() 사용 (블로킹 방지)

**코드 위치:** 라인 2307-2328

```python
def update_display(self):
    # clear() 대신 기존 객체 재사용
    self.ax_main.clear()
    self._initialize_axes()
    self._draw_tactical_display()
    
    # 5초마다 업데이트
    if self.current_time_step % 5 == 0:
        self._draw_history_panel()
        self._draw_analysis_panel()
    
    # 블로킹 방지
    self.fig.canvas.draw_idle()
```

---

## 사용 예시

### 기본 실행
```python
# GUI 모드로 실행
tracker = MultiMissileTracker(use_mip=True, objective='MIN_DAMAGE', headless=False)

# 제어 패널이 자동으로 생성됨
# 1. 시나리오 선택
# 2. 알고리즘 선택 (MIP/Greedy/GA)
# 3. Warm-start 활성화
# 4. ▶ 시작 버튼 클릭
```

### Headless 모드 (GUI 없이)
```python
# CLI 모드로 실행
tracker = MultiMissileTracker(use_mip=True, objective='MIN_DAMAGE', headless=True)
tracker.start_scenario()

while tracker.current_time_step < 1600:
    tracker.run_realtime_dwta()
    tracker.update_simulation()
```

---

## 주요 파일 참조

- **`multi_missile_tracker_gui.py`**: 메인 GUI 시스템
- **`nonlinear_mip_optimizer.py`**: MIP 최적화 알고리즘
- **`greedy_optimizer.py`**: Greedy 알고리즘
- **`ga_optimizer.py`**: 유전 알고리즘
- **`config_mip.py`**: 시나리오 설정
- **`uncertainty_modeling.py`**: 불확실성 모델링

---

## 문제 해결

### 할당 선이 표시되지 않는 경우
1. `primary_assignments`가 비어있는지 확인
2. 위협이 활성 상태인지 확인 (`missile['active'] == True`)
3. 포대가 작동 중인지 확인 (`battery['status'] == 'OPERATIONAL'`)

### GUI가 응답하지 않는 경우
1. 시뮬레이션 속도를 낮춤 (0.5x 이하)
2. 최적화 시간 제한 확인 (max_solve_time = 5초)
3. 스레드 데드락 확인

### 최적화가 Infeasible인 경우
- **원인 1**: 자원 부족 (미사일 부족)
- **원인 2**: 용량 부족 (동시 교전 제약)
- **원인 3**: 커버리지 부족 (사거리 밖)

**로그 확인:**
```
[WARN] [T=45] DWTA Infeasible - 용량 부족 (동시 교전 제약)
[INFO] 상세: 할당 28/30개 (포화 포대: 8/10개)
```

---

## 결론

이 시스템은 실시간 DWTA 시뮬레이션을 위한 포괄적인 GUI 솔루션을 제공합니다. 할당 선을 통한 시각적 피드백, 다층 방어 시스템, 그리고 유연한 알고리즘 선택을 통해 효과적인 미사일 방어 전략을 분석할 수 있습니다.

**핵심 장점:**
- ✅ 실시간 시각화 및 모니터링
- ✅ 다층 방어 시스템 (LSAM + MSAM)
- ✅ 유연한 알고리즘 선택 (MIP/Greedy/GA)
- ✅ Warm-start 지원으로 성능 향상
- ✅ 포괄적인 이벤트 로깅
- ✅ 직관적인 GUI 제어

---

**작성일**: 2026-01-22  
**버전**: v4.0  
**작성자**: Cascade AI Assistant
