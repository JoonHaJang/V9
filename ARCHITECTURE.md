# Multi-Missile Tracker GUI - 시스템 아키텍처

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [모듈 의존성 구조](#모듈-의존성-구조)
3. [핵심 클래스 구조](#핵심-클래스-구조)
4. [데이터 흐름](#데이터-흐름)
5. [외부 라이브러리](#외부-라이브러리)

---

## 시스템 개요

**Multi-Missile Tracker GUI**는 실시간 DWTA(Dynamic Weapon Target Assignment) 최적화 시뮬레이터입니다.

### 주요 기능
- ✅ 실시간 탄도 미사일 추적 및 시각화
- ✅ 다층 방어 체계 최적화 (LSAM/MSAM)
- ✅ 3가지 최적화 알고리즘 비교 (MIP, Greedy, GA)
- ✅ 불확실성 모델링 (베타 분포 기반)
- ✅ GUI 제어 패널 및 실시간 로깅

---

## 모듈 의존성 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                  multi_missile_tracker_gui.py                   │
│                                                                 │
│  GUI 및 전체 시뮬레이션 제어하는 최상위 모듈                      │
│  - 실시간 DWTA 최적화 실행                                       │
│  - 시각화 및 로깅 관리                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ import
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────────┐
│  config_mip.py│    │nonlinear_mip   │    │uncertainty_      │
│               │    │_optimizer.py   │    │modeling.py       │
│ 시나리오 데이터│    │                │    │                  │
│ 및 모델 파라  │    │ 시스템의 두뇌,  │    │ 불확실성 모델링 및│
│ 미터를 정의   │    │ McCormick 선형화│    │ 로직을 포함한 핵심│
│ 하는 설정 파일│    │ 로직을 최적화 엔진│    │ 최적화 엔진      │
└───────────────┘    └────────────────┘    └──────────────────┘
        │                     │                     │
        │                     │ uses                │ uses
        │                     ▼                     ▼
        │            ┌─────────────────────────────────┐
        │            │   외부 라이브러리                │
        │            ├─────────────────────────────────┤
        │            │ • PuLP (Nanum Myeongjo Regular) │
        │            │ • numpy (Nanum Myeongjo Regular)│
        │            │ • tkinter (Nanum Myeongjo Reg.) │
        │            └─────────────────────────────────┘
        │
        └──────────────────┐
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  greedy_optimizer.py                 │
        │  ga_optimizer.py                     │
        │                                      │
        │  대안 최적화 알고리즘                 │
        │  - Greedy: 탐욕적 할당               │
        │  - GA: 유전 알고리즘                 │
        └──────────────────────────────────────┘
                           │
                           │ uses
                           ▼
        ┌──────────────────────────────────────┐
        │  performance_logger.py               │
        │  stress_test_metrics.py              │
        │                                      │
        │  성능 측정 및 벤치마크 도구           │
        └──────────────────────────────────────┘
```

---

## 핵심 클래스 구조

### 1️⃣ **MultiMissileTracker** (메인 시뮬레이터)

```python
class MultiMissileTracker:
    """실시간 DWTA 분석 시뮬레이터 - GUI 지원 버전"""
```

**역할:**
- 전체 시뮬레이션 제어 및 상태 관리
- 실시간 미사일 추적 및 궤적 계산
- DWTA 최적화 실행 및 결과 처리
- GUI 업데이트 및 시각화

**주요 속성:**
```python
# 시뮬레이션 상태
self.current_time_step: int              # 현재 시간 단계
self.missiles: Dict[str, Dict]           # 미사일 객체 저장소
self.assets: List[Dict]                  # 방어 자산 목록
self.batteries: List[Dict]               # 포대 목록

# 최적화 관리
self.primary_assignments: OptimizedAssignmentManager  # 할당 관리자
self.optimization_history: List[Tuple]   # 최적화 이력
self.current_algorithm: str              # 'MIP', 'Greedy', 'GA'

# 불확실성 모델링
self.uncertainty_model: UncertaintyModeling  # 확률 샘플링
self.enhanced_engagement_matrix: EnhancedEngagementMatrix  # 교전 매트릭스
```

**주요 메서드:**
```python
def run_realtime_dwta(self) -> None:
    """실시간 DWTA 최적화 실행"""
    
def _run_dwta_optimization(self) -> Dict:
    """DWTA 최적화 수행 및 결과 반환"""
    
def update_missile_positions(self) -> None:
    """미사일 위치 업데이트 (탄도 궤적 계산)"""
    
def _process_optimization_results(self, result: Dict) -> None:
    """최적화 결과 처리 및 할당 적용"""
```

---

### 2️⃣ **OptimizedAssignmentManager** (할당 관리자)

```python
class OptimizedAssignmentManager:
    """하이브리드 자료구조: 빠른 쓰기 O(1) + 빠른 탐색 O(1)~O(k)"""
```

**역할:**
- 배터리-위협 할당 관계 관리
- 양방향 인덱스 + 비트마스크 최적화
- 메모리 효율성 6배 향상

**주요 속성:**
```python
self.battery_to_threats: List[List[int]]  # 배터리 → 위협 인덱스
self.threat_to_batteries: List[List[int]] # 위협 → 배터리 인덱스
self.battery_masks: np.ndarray[uint64]    # 비트마스크 (초고속 존재 확인)
self.threat_id_to_idx: Dict[str, int]     # ID → 인덱스 매핑
self.battery_id_to_idx: Dict[str, int]    # ID → 인덱스 매핑
```

**주요 메서드:**
```python
def assign(self, threat_id: str, battery_id: str) -> None:
    """할당 추가 (O(1))"""
    
def remove(self, threat_id: str, battery_id: str) -> None:
    """할당 제거 (O(k))"""
    
def get_threats_for_battery(self, battery_id: str) -> List[str]:
    """배터리에 할당된 위협 조회 (O(k))"""
    
def has_assignment(self, threat_id: str, battery_id: str) -> bool:
    """할당 존재 확인 (O(1) 비트마스크)"""
```

---

### 3️⃣ **ControlPanel** (GUI 제어 패널)

```python
class ControlPanel:
    """GUI 제어 패널"""
```

**역할:**
- 시뮬레이션 제어 (시작/일시정지/재시작)
- 실시간 로그 출력
- 상태 모니터링 (요격률, 배터리 활용률)
- 알고리즘 선택 및 설정

**주요 속성:**
```python
self.tracker: MultiMissileTracker        # 시뮬레이터 참조
self.control_window: tk.Tk               # Tkinter 윈도우
self.log_text: scrolledtext.ScrolledText # 로그 출력 영역
self.status_vars: Dict[str, tk.StringVar] # 상태 변수들
```

**주요 메서드:**
```python
def start_simulation(self) -> None:
    """시뮬레이션 시작"""
    
def pause_simulation(self) -> None:
    """일시정지"""
    
def log_message(self, message: str, level: str = "INFO") -> None:
    """로그 메시지 출력 (색상 코딩)"""
    
def update_status(self) -> None:
    """상태 패널 업데이트 (1초마다)"""
```

---

## 데이터 흐름

### 🔄 실시간 시뮬레이션 루프

```
┌─────────────────────────────────────────────────────────┐
│ 1. 시간 단계 증가 (current_time_step += 1)              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 2. 미사일 위치 업데이트 (update_missile_positions)      │
│    - 탄도 궤적 계산 (포물선 근사)                       │
│    - 3D 위치 (x, y, altitude) 갱신                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 3. 새로운 위협 발사 체크 (launch_time == current_time) │
│    - missiles 딕셔너리에 추가                           │
│    - GUI에 "LAUNCH" 로그 출력                           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 4. DWTA 최적화 실행 (run_realtime_dwta)                │
│    ├─ 최적화 간격 체크 (optimization_interval)         │
│    ├─ 입력 데이터 준비 (assets, batteries, threats)    │
│    ├─ 확률 샘플링 (uncertainty_model)                  │
│    └─ 알고리즘 실행 (MIP/Greedy/GA)                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 5. 최적화 결과 처리 (_process_optimization_results)    │
│    ├─ 할당 업데이트 (primary_assignments)              │
│    ├─ 배터리 용량 차감                                 │
│    └─ 요격 미사일 발사                                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 6. 요격 판정 (check_intercepts)                        │
│    ├─ 요격 성공 확률 계산 (Pk)                         │
│    ├─ 몬테카를로 시뮬레이션                            │
│    └─ 성공/실패 로그 출력                              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 7. GUI 업데이트 (draw_tactical_display)                │
│    ├─ 미사일 궤적 시각화                               │
│    ├─ 배터리 상태 표시                                 │
│    ├─ 할당 관계 선 그리기                              │
│    └─ 분석 패널 업데이트 (그래프)                      │
└─────────────────────────────────────────────────────────┘
                        ↓
                  [반복 또는 종료]
```

---

### 📊 DWTA 최적화 상세 흐름

```
[run_realtime_dwta 호출]
         │
         ├─ 1. 활성 위협 체크 (active_threats_count > 0)
         │
         ├─ 2. 최적화 간격 체크 (current_time - last_optimization >= interval)
         │      └─ 예외: capacity_freed 또는 needs_reassignment 플래그 시 즉시 실행
         │
         ├─ 3. 입력 데이터 준비 (_prepare_optimizer_inputs)
         │      ├─ assets_opt: List[Asset]
         │      ├─ systems_opt: List[InterceptorSystem]
         │      └─ threats_opt: List[Threat]
         │
         ├─ 4. 확률 샘플링 (uncertainty_model.sample_intercept_probability)
         │      └─ 베타 분포 (α=9, β=1) 기반 Pk 샘플링
         │
         ├─ 5. 알고리즘 선택 및 실행
         │      ├─ MIP: NonLinearMIPOptimizer
         │      │      ├─ create_model() - 변수 및 제약 생성
         │      │      ├─ McCormick 선형화 적용
         │      │      └─ PuLP 솔버 실행
         │      │
         │      ├─ Greedy: GreedyOptimizer
         │      │      └─ 가치 기반 탐욕적 할당
         │      │
         │      └─ GA: GeneticAlgorithmOptimizer
         │             └─ 유전 알고리즘 진화
         │
         ├─ 6. 결과 검증 (feasible 여부)
         │      ├─ Feasible → _process_optimization_results 호출
         │      └─ Infeasible → "DWTA Infeasible" 로그 출력
         │
         └─ 7. 최적화 이력 기록 (optimization_history)
                └─ (time_step, objective_value, solve_time)
```

---

## 외부 라이브러리

### 🔧 최적화 엔진
```python
from pulp import *  # Nanum Myeongjo Regular, #496067
```
- **역할:** 선형 계획법 (LP) 및 혼합 정수 계획법 (MIP) 솔버
- **사용:** NonLinearMIPOptimizer에서 DWTA 문제 해결

### 📊 수치 계산
```python
import numpy as np  # Nanum Myeongjo Regular, #496067
```
- **역할:** 고속 배열 연산 및 수치 계산
- **사용:** 비트마스크, 궤적 계산, 확률 샘플링

### 🖼️ GUI 프레임워크
```python
import tkinter as tk  # Nanum Myeongjo Regular, #496067
from tkinter import ttk, scrolledtext, messagebox
```
- **역할:** GUI 제어 패널 및 로그 출력
- **사용:** ControlPanel 클래스

### 📈 시각화
```python
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
```
- **역할:** 실시간 전술 디스플레이 및 분석 그래프
- **사용:** draw_tactical_display, _draw_analysis_panel

---

## 모듈별 상세 설명

### 📄 **config_mip.py**
**시나리오 데이터 및 모델 파라미터를 정의하는 설정 파일**

**주요 클래스:**
- `MIPConfig`: 시뮬레이션 설정 (시간, 시나리오 타입)
- `AssetConfig`: 자산 스펙 (위치, 가치, 우선순위)
- `InterceptorSystemConfig`: 포대 스펙 (LSAM/MSAM)
- `EnhancedEngagementMatrix`: 교전 가능성 매트릭스 (정적 + 동적)
- `KFactorCache`: K-factor 캐싱 (성능 최적화)

**주요 메서드:**
```python
def create_realistic_scenario(self) -> Dict:
    """현실적인 시나리오 생성"""
    
def can_engage_trajectory(self, battery, threat) -> List[Tuple]:
    """탄도 궤적 교전 가능 구간 계산"""
```

---

### 📄 **nonlinear_mip_optimizer.py**
**시스템의 두뇌, McCormick 선형화 로직을 포함한 핵심 최적화 엔진**

**주요 클래스:**
- `NonLinearMIPOptimizer`: MIP 기반 DWTA 최적화

**주요 메서드:**
```python
def create_model(self, assets, interceptor_systems, threats, 
                 batteries, engagement_matrix) -> None:
    """최적화 모델 생성 (변수, 제약, 목적함수)"""
    
def solve(self) -> Dict:
    """PuLP 솔버 실행 및 결과 반환"""
    
def _create_decision_variables(self) -> None:
    """결정 변수 생성 (x_ij, k_ij)"""
    
def _add_mccormick_constraints(self) -> None:
    """McCormick 선형화 제약 추가"""
```

**McCormick 선형화:**
```
비선형: z = x * k  (x: 이진, k: 연속)
선형화:
  z ≥ k_min * x
  z ≥ k + k_max * (x - 1)
  z ≤ k - k_min * (1 - x)
  z ≤ k_max * x
```

---

### 📄 **uncertainty_modeling.py**
**불확실성 모델링 및 로직을 포함한 핵심 최적화 엔진**

**주요 클래스:**
- `UncertaintyConfig`: 불확실성 설정 (분포 타입, 파라미터)
- `UncertaintyModeling`: 확률 샘플링 및 시나리오 생성

**주요 메서드:**
```python
def sample_intercept_probability(self, base_prob: float) -> float:
    """베타 분포 기반 요격 확률 샘플링"""
    # α=9, β=1 → 높은 확률 편향
    
def generate_scenarios(self, num_scenarios: int) -> List[Dict]:
    """몬테카를로 시나리오 생성"""
```

**베타 분포 특성:**
- α=9, β=1: 평균 0.9, 높은 확률 편향
- 불확실성 반영: 매 최적화마다 다른 Pk 샘플링

---

### 📄 **greedy_optimizer.py / ga_optimizer.py**
**대안 최적화 알고리즘**

**Greedy Optimizer:**
```python
def solve(self) -> Dict:
    """탐욕적 할당 (가치 기반 정렬)"""
    # 1. 자산을 가치 순으로 정렬
    # 2. 높은 가치 자산부터 위협 할당
    # 3. 배터리 용량 소진 시 종료
```

**GA Optimizer:**
```python
def solve(self) -> Dict:
    """유전 알고리즘 진화"""
    # 1. 초기 개체군 생성
    # 2. 적합도 평가 (목적함수)
    # 3. 선택, 교차, 돌연변이
    # 4. 세대 반복 (100세대)
```

---

### 📄 **performance_logger.py / stress_test_metrics.py**
**성능 측정 및 벤치마크 도구**

**PerformanceLogger:**
```python
def log_optimization(self, algorithm: str, solve_time: float, 
                     objective: float, variables: int) -> None:
    """최적화 성능 로깅"""
```

**StressTestMetrics:**
```python
def record_intercept(self, success: bool, layer: str) -> None:
    """요격 결과 기록"""
    
def generate_report(self) -> Dict:
    """스트레스 테스트 보고서 생성"""
```

---

## 주요 알고리즘 비교

| 알고리즘 | 시간 복잡도 | 최적성 | 확장성 | 특징 |
|---------|-----------|--------|--------|------|
| **MIP** | O(2^n) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 전역 최적해, McCormick 선형화 |
| **Greedy** | O(n log n) | ⭐⭐ | ⭐⭐⭐⭐⭐ | 빠른 속도, 근사해 |
| **GA** | O(g × p × n) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 진화 기반, 지역 최적 탈출 |

*(n: 위협 수, g: 세대 수, p: 개체군 크기)*

---

## 성능 최적화 기법

### 1️⃣ **하이브리드 자료구조 (OptimizedAssignmentManager)**
- 양방향 인덱스 + 비트마스크
- 메모리: 6배 절감
- 탐색: O(1) 비트마스크

### 2️⃣ **Warm-start (MIP)**
- 이전 해를 초기값으로 사용
- 솔버 시간: 30-50% 단축

### 3️⃣ **K-factor 캐싱**
- 교전 윈도우 품질 사전 계산
- 중복 계산 제거

### 4️⃣ **교전 매트릭스 Precompute**
- 정적 교전 가능성 사전 계산
- 실시간 체크: 거리/고도만 확인

---

## 시뮬레이션 파라미터

### ⏱️ 시간 설정
```python
simulation_duration_sec = 1600  # 총 시뮬레이션 시간
optimization_interval = 1       # 최적화 간격 (초)
time_step_duration = 1          # 시간 단계 (초)
```

### 🎯 최적화 목적
```python
OBJECTIVES = {
    'MIN_DAMAGE': '기대 피해 최소화 (가치 기반)',
    'MAX_KILLS': '요격 수 최대화 (평등주의)',
}
```

### 🚀 배터리 스펙
```python
LSAM (상층 방어):
  - 고도: 40-70km
  - 사거리: 150-300km
  - 동시 교전: 10발
  - Pk: 0.85

MSAM (하층 방어):
  - 고도: 0-50km (확장)
  - 사거리: 5-50km
  - 동시 교전: 8발
  - Pk: 0.80
```

---

## 파일 구조 요약

```
V9/
├── multi_missile_tracker_gui.py    # 메인 시뮬레이터 (3867 lines)
├── config_mip.py                   # 설정 및 시나리오 (1892 lines)
├── nonlinear_mip_optimizer.py      # MIP 최적화 엔진
├── greedy_optimizer.py             # Greedy 알고리즘
├── ga_optimizer.py                 # 유전 알고리즘
├── uncertainty_modeling.py         # 불확실성 모델링
├── performance_logger.py           # 성능 로깅
├── stress_test_metrics.py          # 스트레스 테스트
├── scenario_dwta_balanced.py       # 균형 시나리오
├── k_factor_theory.py              # K-factor 이론
└── ARCHITECTURE.md                 # 본 문서
```

---

## 실행 흐름 예시

### 🎬 시뮬레이션 시작
```python
# 1. 시뮬레이터 초기화
tracker = MultiMissileTracker(use_mip=True, objective='MIN_DAMAGE')

# 2. GUI 제어 패널 생성
control_panel = ControlPanel(tracker)

# 3. 시뮬레이션 시작
tracker.run_simulation()
```

### 📝 로그 출력 예시
```
[23:30:40] [INFO] === SIMULATION START (T=0) ===
[23:30:40] [INFO] Scenario: DWTA_BALANCED, Batteries: 6, Assets: 10
[23:30:40] [INFO] LAUNCH: T01 → A01
[23:30:41] [INFO] [T=5] Optimization: Obj=899.6, Time=0.087s, Vars=15
[23:30:41] [INFO] [T=5] 할당 가능: 1개 신규 할당 (총 1/18, 포대: 1/6)
[23:31:07] [CRIT] INTERCEPT SUCCESS: T01 by LSAM_03 (Pk=0.9914)
[23:31:24] [INFO] === SIMULATION COMPLETE ===
[23:31:24] [INFO] Intercept Rate: 95.0% (19/20)
```

---

## 참고 문서

- `SIMULATOR_CHARACTERISTICS.md`: 시뮬레이터 특성 상세 설명
- `TACTICAL_DISPLAY_GUIDE.md`: 전술 디스플레이 가이드
- `IMPROVEMENTS_SUMMARY.md`: 개선 사항 요약
- `SLS_2층방어_분석보고서.md`: 2층 방어 분석 보고서

---

**작성일:** 2026-01-23  
**버전:** V9  
**작성자:** Cascade AI Assistant
