# 🚨 K-Factor 구현 심각 버그 보고서

**발견일:** 2026-02-06
**심각도:** ⚠️ **CRITICAL** - 전체 최적화 논리에 영향
**상태:** 🔴 미수정

---

## 📋 요약

**현재 구현:** 거리 기반(Distance-based) K-factor
**요구사항:** 시간 기반(Time-based) K-factor
**불일치 정도:** 근본적 접근 방식 차이

---

## 🔍 상세 분석

### 1️⃣ Time-Based Dynamic Calculation 누락

#### ❌ 현재 구현 (config_mip.py:1736-1751)
```python
def _calculate_k_factor(self, threat, system, engagement_matrix) -> float:
    """거리 기반 확률 보정 계수"""
    distance = engagement_matrix.get_distance(system.id, threat.id)
    max_range = system.engagement_range

    # 거리 기반 보정
    range_ratio = 1.0 - (distance / max_range)
    k = self.k_min + (self.k_max - self.k_min) * max(0, range_ratio)

    return np.clip(k, self.k_min, self.k_max)
```

**문제점:**
- ❌ `t_remaining` (남은 교전 시간) 없음
- ❌ `t_window` (교전 윈도우 지속 시간) 없음
- ❌ `current_time` (현재 시간) 파라미터 없음
- ✅ 거리만 고려 (distance/max_range)

#### ✅ 올바른 구현 (요구사항)
```python
def _calculate_k_factor(self, threat, system, engagement_matrix, current_time) -> float:
    """시간 기반 교전 품질 계수"""

    # 1단계: 교전 윈도우 정보 획득
    window_info = engagement_matrix.get_engagement_window(system.id, threat.id)
    window_start = window_info['window_start_time']
    window_end = window_info['window_end_time']
    window_duration = window_end - window_start

    # 2단계: 남은 교전 시간 계산
    if current_time < window_start:
        t_remaining = window_duration  # 윈도우 시작 전
    elif current_time > window_end:
        return self.k_min  # 윈도우 종료
    else:
        t_remaining = window_end - current_time  # 윈도우 내

    # 3단계: Time-based k_base 계산
    if window_duration <= 0:
        return self.k_min

    k_base = self.k_min + (self.k_max - self.k_min) * (t_remaining / window_duration)

    # 4단계: Distance correction 적용
    distance = engagement_matrix.get_distance(system.id, threat.id)
    max_range = system.engagement_range
    distance_correction = 1.0 - 0.4 * (distance / max_range)

    # 5단계: 최종 k-factor
    k_ij = k_base * distance_correction

    return np.clip(k_ij, self.k_min, self.k_max)
```

**차이점:**
```
현재:   k = f(distance)              # 정적, 거리만
요구:   k = f(time, distance)        # 동적, 시간 우선
```

---

### 2️⃣ Distance Correction Formula 오류

#### ❌ 현재 구현
```python
range_ratio = 1.0 - (distance / max_range)
k = k_min + (k_max - k_min) * range_ratio
```

**문제:**
- 계수 없음 (0.4 누락)
- 단일 계산 (Two-stage 구조 없음)

#### ✅ 올바른 구현
```python
# Stage 1: Time-based quality
k_base = k_min + (k_max - k_min) * (t_remaining / t_window)

# Stage 2: Distance correction (0.4 계수!)
distance_correction = 1.0 - 0.4 * (distance / max_range)

# Stage 3: Multiplication
k_ij = k_base * distance_correction
```

**수식:**
```
현재: k = 0.6 + 0.4 × (1 - d/R)
요구: k = [0.6 + 0.4 × (t_rem/t_win)] × [1 - 0.4 × (d/R)]
```

---

### 3️⃣ Two-Stage Calculation Structure 누락

#### 개념적 차이

**현재 (Single-stage):**
```
┌─────────────┐
│   Distance  │
└──────┬──────┘
       │
       ▼
   ┌───────┐
   │   k   │
   └───────┘
```

**요구 (Two-stage):**
```
┌──────────────┐     ┌─────────────┐
│ Time Remaining│     │  Distance   │
└───────┬───────┘     └──────┬──────┘
        │                    │
        ▼                    ▼
    ┌───────┐           ┌────────────┐
    │ k_base│           │ dist_corr  │
    └───┬───┘           └──────┬─────┘
        │                      │
        └──────────┬───────────┘
                   ▼
               ┌───────┐
               │ k_ij  │
               └───────┘
```

**의미:**
- **k_base**: 교전 타이밍 품질 (시간 요소)
- **dist_corr**: 거리 보정 (공간 요소)
- **k_ij**: 종합 교전 품질

---

### 4️⃣ Real-Time Time Tracking 미구현

#### 문제: 현재 시간 파라미터 없음

```python
# 현재 함수 시그니처
def _calculate_k_factor(self, threat, system, engagement_matrix):
    # current_time 파라미터 없음!

# 호출 체인
optimizer.create_model(...)
  → k_cache.precompute(threats, systems, engagement_matrix)
    → _calculate_k_factor(threat, system, engagement_matrix)
      # ❌ 현재 시간 정보 전달 안 됨
```

#### 필요한 수정

```python
# 수정된 함수 시그니처
def _calculate_k_factor(self, threat, system, engagement_matrix, current_time):
    # ✅ current_time 파라미터 추가

# 수정된 호출 체인
optimizer.create_model(..., current_time=tracker.current_time_step)
  → k_cache.precompute(threats, systems, engagement_matrix, current_time)
    → _calculate_k_factor(threat, system, engagement_matrix, current_time)
      # ✅ 현재 시간 전달
```

---

## 📊 영향 분석

### 현재 동작

```python
# 시나리오: 배터리가 위협을 교전할 때

# T=0.0초 (교전 윈도우 시작)
k = 0.6 + 0.4 × (1 - 100/150) = 0.6 + 0.4 × 0.333 = 0.73

# T=30초 (윈도우 중반)
k = 0.6 + 0.4 × (1 - 100/150) = 0.73  # 변화 없음!

# T=60초 (윈도우 종료 직전)
k = 0.6 + 0.4 × (1 - 100/150) = 0.73  # 여전히 변화 없음!
```

**문제:** k-factor가 시간에 따라 변하지 않음 (정적)

### 올바른 동작

```python
# 교전 윈도우: T=0~60초, 거리: 100km, 최대 범위: 150km

# T=0.0초 (윈도우 시작, t_remaining=60초)
k_base = 0.6 + 0.4 × (60/60) = 1.0
dist_corr = 1 - 0.4 × (100/150) = 0.733
k = 1.0 × 0.733 = 0.733  ✅

# T=30초 (윈도우 중반, t_remaining=30초)
k_base = 0.6 + 0.4 × (30/60) = 0.8
dist_corr = 1 - 0.4 × (100/150) = 0.733
k = 0.8 × 0.733 = 0.587  ✅ 감소!

# T=55초 (윈도우 종료 직전, t_remaining=5초)
k_base = 0.6 + 0.4 × (5/60) = 0.633
dist_corr = 1 - 0.4 × (100/150) = 0.733
k = 0.633 × 0.733 = 0.464  ✅ 더 감소!

# T=60초 (윈도우 종료)
k = 0.6 (k_min)  ✅ 최소값
```

**차이:** 시간에 따라 동적으로 변화 (조기 교전 인센티브)

---

## 🎯 최적화 논리에 미치는 영향

### 현재 (Distance-based)

```
MIP Objective:
MIN Σ (asset_value × P_fail)

where:
P_fail = Π (1 - k × Pk)
k = f(distance)  # 정적

결과:
- 거리만 고려 → 가까운 배터리 선호
- 타이밍 무시 → 조기 교전 인센티브 없음
- 늦은 할당도 동일한 k값 사용 (비현실적)
```

### 올바른 (Time-based)

```
MIP Objective:
MIN Σ (asset_value × P_fail)

where:
P_fail = Π (1 - k(t) × Pk)
k(t) = f(time, distance)  # 동적

결과:
- 시간 우선 고려 → 조기 교전 강력 선호
- 거리도 고려 → 가까운 배터리 추가 보너스
- 늦은 할당 패널티 → 현실적 의사결정
```

---

## 🛠️ 수정 계획

### Phase 1: 교전 윈도우 정보 확장

**파일:** `config_mip.py:799-916` (calculate_engagement_time_window)

```python
# 현재 반환값
return {
    "can_engage": bool,
    "window_quality": float,
    "threat_phases": dict,
    ...
}

# 수정 후 반환값
return {
    "can_engage": bool,
    "window_quality": float,
    "threat_phases": dict,
    "window_start_time": float,  # 🆕 추가
    "window_end_time": float,    # 🆕 추가
    "window_duration": float,    # 🆕 추가
    ...
}
```

### Phase 2: K-Factor 계산 함수 수정

**파일:** `config_mip.py:1736-1751`

```python
# 기존
def _calculate_k_factor(self, threat, system, engagement_matrix) -> float:

# 수정
def _calculate_k_factor(self, threat, system, engagement_matrix,
                        current_time: float) -> float:
    """
    Two-stage k-factor calculation:
    1. Time-based quality (k_base)
    2. Distance correction
    """

    # 윈도우 정보 획득
    window_info = engagement_matrix.get_engagement_window(system.id, threat.id)

    if not window_info or not window_info.get('can_engage', False):
        return self.k_min

    window_start = window_info['window_start_time']
    window_end = window_info['window_end_time']
    window_duration = window_end - window_start

    # Time-based k_base
    if current_time < window_start:
        t_remaining = window_duration
    elif current_time > window_end:
        return self.k_min
    else:
        t_remaining = window_end - current_time

    k_base = self.k_min + (self.k_max - self.k_min) * (t_remaining / window_duration)

    # Distance correction (0.4 계수!)
    distance = engagement_matrix.get_distance(system.id, threat.id)
    max_range = system.engagement_range
    distance_correction = 1.0 - 0.4 * (distance / max_range)

    # Final k-factor
    k_ij = k_base * distance_correction

    return np.clip(k_ij, self.k_min, self.k_max)
```

### Phase 3: 호출 체인 수정

**파일:** `config_mip.py:1658-1678` (KFactorCache.precompute)

```python
# 기존
def precompute(self, threats: List, systems: List, engagement_matrix):

# 수정
def precompute(self, threats: List, systems: List, engagement_matrix,
               current_time: float = 0.0):
    for threat in threats:
        for system in systems:
            k_value = self._calculate_k_factor(
                threat, system, engagement_matrix,
                current_time  # 🆕 추가
            )
            self.k_table[key] = k_value
```

**파일:** `nonlinear_mip_optimizer.py:152-196` (create_model)

```python
# 수정
self.k_factor_cache.precompute(
    threats,
    interceptor_systems,
    self.engagement_matrix_cache,
    current_time=current_time  # 🆕 추가 (파라미터로 받아야 함)
)
```

**파일:** `multi_missile_tracker_gui.py:1980-2012` (run_realtime_dwta)

```python
# 수정
optimizer.create_model(
    assets=assets_opt,
    interceptor_systems=systems_opt,
    threats=threats_opt,
    batteries=self.batteries,
    engagement_matrix=self.enhanced_engagement_matrix,
    current_time=self.current_time_step  # 🆕 추가
)
```

### Phase 4: 동적 K-Factor 업데이트 지원

**파일:** `config_mip.py:1633-1703` (KFactorCache)

```python
class KFactorCache:
    def __init__(self, k_min: float = 0.6, k_max: float = 1.0):
        self.k_min = k_min
        self.k_max = k_max
        self.k_table: Dict[Tuple[str, str], float] = {}
        self.last_update_time = 0.0  # 🆕 추가

    def update_time_based_k(self, current_time: float):
        """시간 변화에 따라 k-factor 재계산"""
        if current_time == self.last_update_time:
            return  # 이미 업데이트됨

        for (threat_id, system_id), old_k in self.k_table.items():
            # 재계산
            new_k = self._calculate_k_factor(..., current_time)
            self.k_table[(threat_id, system_id)] = new_k

        self.last_update_time = current_time
```

---

## 🧪 테스트 시나리오

### Test Case 1: 조기 vs 후기 할당

```python
# 시나리오
위협: T1, 교전 윈도우 0~60초
배터리: LSAM_1, 거리 100km, 범위 150km

# 현재 구현
k(T=0) = 0.73
k(T=30) = 0.73  # 동일
k(T=55) = 0.73  # 동일

→ MIP가 T=0과 T=55를 구분 못함

# 올바른 구현
k(T=0) = 0.733   # 최적
k(T=30) = 0.587  # 감소
k(T=55) = 0.464  # 큰 패널티

→ MIP가 조기 할당 선호
```

### Test Case 2: 거리 vs 타이밍 트레이드오프

```python
# 상황
위협: T1, 교전 윈도우 0~60초, 현재 T=40초
배터리 A: 거리 50km, 범위 150km
배터리 B: 거리 120km, 범위 150km

# 현재 구현 (Distance만)
k_A = 0.6 + 0.4 × (1 - 50/150) = 0.867
k_B = 0.6 + 0.4 × (1 - 120/150) = 0.680
→ 배터리 A 선택 (거리 우선)

# 올바른 구현 (Time+Distance)
t_remaining = 20초

k_base = 0.6 + 0.4 × (20/60) = 0.733

k_A = 0.733 × [1 - 0.4×(50/150)] = 0.733 × 0.867 = 0.636
k_B = 0.733 × [1 - 0.4×(120/150)] = 0.733 × 0.680 = 0.498

→ 여전히 배터리 A 선택하지만,
  타이밍 패널티로 인해 k값이 둘 다 감소
```

---

## 📊 예상 영향

### 최적화 품질
```
현재: 거리 최적화 위주
수정 후: 시간 최적화 + 거리 보정
→ 더 현실적인 할당 패턴
```

### 성능
```
현재: 정적 k-factor (1회 계산)
수정 후: 동적 k-factor (시간마다 재계산 가능)
→ 계산 복잡도 증가 가능
   (캐싱으로 완화 필요)
```

### 운영 전술
```
현재: "가까운 배터리 우선"
수정 후: "빨리 할당하고 가까운 배터리 우선"
→ 조기 교전 강력 인센티브
```

---

## 🎯 우선순위

1. **🔴 High Priority**: Phase 1, 2 (k-factor 계산 수정)
2. **🟠 Medium Priority**: Phase 3 (호출 체인 수정)
3. **🟡 Low Priority**: Phase 4 (동적 업데이트)

---

## 📝 결론

K-Factor 구현이 **근본적으로 잘못**되었습니다:
- ❌ 거리 기반 (Distance-based)
- ✅ 시간 기반 (Time-based) 필요

이는 최적화 결과의 **전술적 의미**에 영향을 미칩니다:
- 현재: 단순 거리 최적화
- 요구: 시간-거리 복합 최적화

**수정 필요성:** 🔴 **CRITICAL**

---

**보고서 작성:** Claude Code
**검증자:** User (Cross-check)
**다음 단계:** 수정 계획 실행
