# SLS 2층 방어 시스템 완전 분석 보고서

## 📋 분석 개요

본 보고서는 현재 시뮬레이터의 SLS(Shoot-Look-Shoot) 2층 방어 시스템을 최소 단위로 분해하여 다음 질문들에 대한 답변을 제공합니다:

1. **상층(LSAM) 실패 시 하층(MSAM)에서 대응 가능한가?**
2. **시간제약 상 상층 방어 실패 시 하층에서 방어가 가능한가?**
3. **상층 실패 시 다음 시나리오는 어떻게 되는가?**
4. **완전 자동 재교전 시 최대 3회 재교전이 가능한가?**

---

## 1. 현재 시스템 구조 분석

### 1.1 2층 방어 시스템 구성

```
┌─────────────────────────────────────────────────────┐
│ 상층 방어 (Upper Layer)                             │
├─────────────────────────────────────────────────────┤
│ • 시스템: LSAM (Long-range SAM)                     │
│ • 교전 고도: 고고도 (High Altitude)                 │
│ • 기본 Pk: 0.85 (85%)                               │
│ • 교전 방식: 2발 살보 (SALVO)                       │
│ • 탄약: 24발/포대                                   │
└─────────────────────────────────────────────────────┘
                    ↓ (실패 시)
┌─────────────────────────────────────────────────────┐
│ 하층 방어 (Lower Layer)                             │
├─────────────────────────────────────────────────────┤
│ • 시스템: MSAM (Medium-range SAM)                   │
│ • 교전 고도: 중고도 (Medium Altitude)               │
│ • 기본 Pk: 0.78 (78%)                               │
│ • 교전 방식: 2발 살보 (SALVO)                       │
│ • 탄약: 48발/포대                                   │
└─────────────────────────────────────────────────────┘
```

### 1.2 코드 위치 및 구현

**파일**: `multi_missile_tracker_gui.py`

**핵심 메서드**: `_process_impact()` (Line 1259-1475)

---

## 2. 질문별 상세 분석

### 2.1 ❌ **상층 실패 시 하층 대응 가능 여부**

#### **현재 구현 상태: 불가능**

**이유**:
```python
# multi_missile_tracker_gui.py Line 1285-1326
for battery_id in assigned_batteries:  # 모든 할당된 배터리 순회
    battery = next((b for b in self.batteries if b['id'] == battery_id), None)
    
    if battery and battery.get('status') == 'OPERATIONAL':
        # LSAM과 MSAM을 구분하지 않고 순차 처리
        missiles_to_fire = min(2, battery.get('available_missiles', 0))
        battery['available_missiles'] -= missiles_to_fire
        
        # 모든 배터리의 Pk를 누적 계산
        for shot_num in range(missiles_to_fire):
            Pk_shot = self.uncertainty_model.sample_intercept_probability(base_Pk)
            P_survival *= (1 - Pk_shot)  # 누적 계산
```

**문제점**:
1. **상층/하층 분리 없음**: 할당된 모든 배터리를 동시에 처리
2. **순차 교전 로직 부재**: 상층 성공 여부를 판정하지 않고 즉시 모든 배터리 발사
3. **조건부 하층 교전 미구현**: 상층 실패 시에만 하층 교전하는 로직 없음

**실제 동작**:
```
위협 T001 교전 범위 진입
    ↓
할당된 배터리: [LSAM_01, MSAM_01]
    ↓
LSAM_01 발사 (2발) → P_survival = 0.0225
MSAM_01 발사 (2발) → P_survival = 0.0225 × 0.0484 = 0.00109
    ↓
P_kill_total = 0.9989 (99.89%)
    ↓
결과 판정 (성공/실패)
```

**결론**: 상층과 하층이 **동시에 발사**되므로, 상층 실패 시 하층이 대응하는 것이 아니라 **처음부터 모두 발사**됨.

---

### 2.2 ⚠️ **시간제약 상 하층 방어 가능 여부**

#### **현재 구현: 시간제약 검증 없음**

**교전 윈도우 계산 코드**:
```python
# config_mip.py Line 276-308 (_calculate_k_value)
window_analysis = EngagementZoneConfig.calculate_engagement_time_window(
    battery_info, 
    threat_info
)

if not window_analysis.get("can_engage", False):
    return self.k_min

window_quality = window_analysis.get("window_quality", 0.5)
k_value = self.k_min + (self.k_max - self.k_min) * window_quality
```

**문제점**:
1. **교전 윈도우는 최적화 시점에만 계산**: 할당 단계에서만 사용
2. **실행 시점 검증 없음**: `_process_impact()`에서 시간 여유 확인 안 함
3. **상층 실패 후 하층 교전 시간 계산 없음**: 순차 교전 시 남은 시간 미검증

**시간제약 분석**:

```
위협 비행 시간: 300초
교전 가능 시점: flight_progress ≥ 0.6 (180초 경과)
남은 시간: 120초

상층 교전 (LSAM):
  - 발사 시점: T=180s
  - 요격 시점: T=185s (5초 후)
  - 결과 판정: T=185s

하층 교전 (MSAM):
  - 발사 시점: T=185s (상층 실패 직후)
  - 요격 시점: T=190s (5초 후)
  - 남은 시간: 110초 (충분)
```

**결론**: 이론적으로는 시간 여유가 **충분**하지만, 현재 코드에서는 **검증하지 않음**.

---

### 2.3 📋 **상층 실패 시 다음 시나리오**

#### **현재 구현 동작**:

```python
# multi_missile_tracker_gui.py Line 1360-1475
P_kill = 1.0 - P_survival  # 모든 배터리의 누적 Pk

if P_kill >= 0.5 and missiles_fired > 0:
    result = 'INTERCEPTED'
    missile['active'] = False
    self.stats['intercepted'] += 1
else:
    result = 'MISSED'
    
    # Shoot-Look-Shoot 재교전 로직
    if self.shoot_look_shoot_enabled and current_attempt < self.max_engagement_attempts:
        missile['needs_reassignment'] = True  # 재할당 요청
        # 위협은 계속 활성 상태 유지
    else:
        # 최종 실패
        missile['active'] = False
        self.stats['missed'] += 1
```

**시나리오 흐름**:

```
1. 초기 할당:
   T001 → [LSAM_01, MSAM_01]

2. 교전 실행 (T=180s):
   LSAM_01 발사 (2발) + MSAM_01 발사 (2발)
   P_kill_total 계산

3-A. 성공 시 (P_kill ≥ 0.5):
   → 요격 성공
   → 위협 비활성화
   → 배터리 할당 해제

3-B. 실패 시 (P_kill < 0.5):
   → 요격 실패
   → needs_reassignment = True
   → 다음 최적화에서 재할당
   → 재교전 시도 (최대 3회)
```

**결론**: 상층 실패 시 **재교전 메커니즘**으로 처리되며, 하층 단독 대응은 **불가능**.

---

### 2.4 ✅ **최대 3회 재교전 가능 여부**

#### **현재 구현: 가능**

**설정 값**:
```python
# multi_missile_tracker_gui.py Line 948-950
self.engagement_attempts = {}  # 각 위협에 대한 교전 시도 횟수
self.max_engagement_attempts = 3  # 최대 3회
self.shoot_look_shoot_enabled = True  # 재교전 활성화
```

**재교전 로직**:
```python
# multi_missile_tracker_gui.py Line 1262-1267
if missile_id not in self.engagement_attempts:
    self.engagement_attempts[missile_id] = 1
else:
    self.engagement_attempts[missile_id] += 1

current_attempt = self.engagement_attempts[missile_id]

# Line 1422-1433
if self.shoot_look_shoot_enabled and current_attempt < self.max_engagement_attempts:
    # 재교전 가능
    missile['needs_reassignment'] = True
    self.control_panel.log_message(
        f"[WARN] INTERCEPT MISS: {missile_id} - Retry {current_attempt}/{self.max_engagement_attempts}",
        "WARNING"
    )
```

**재교전 흐름**:

```
교전 #1 (T=180s):
  - 할당: [LSAM_01, MSAM_01]
  - 결과: 실패 (P_kill < 0.5)
  - 조치: needs_reassignment = True
  - current_attempt = 1

교전 #2 (T=185s):
  - 재할당: [LSAM_02, MSAM_02] (다른 배터리)
  - 결과: 실패
  - 조치: needs_reassignment = True
  - current_attempt = 2

교전 #3 (T=190s):
  - 재할당: [LSAM_03, MSAM_03]
  - 결과: 성공 또는 최종 실패
  - current_attempt = 3 (최대치)
  - 3회 초과 시 자산 피격
```

**결론**: 최대 3회 재교전 **가능** (구현됨).

---

## 3. 문서와 코드 비교

### 3.1 문서 내용 (`다층방어_순차교전_메커니즘.md`)

**문서 주장**:
```
1단계: 상층(LSAM) 교전
  ↓ (실패 시)
2단계: 하층(MSAM) 즉시 교전
```

**코드 구현**:
```
1단계: 모든 배터리(LSAM + MSAM) 동시 교전
  ↓
결과 판정 (성공/실패)
```

### 3.2 불일치 사항

| 항목 | 문서 | 실제 코드 |
|------|------|-----------|
| **교전 순서** | 순차 (상층 → 하층) | 동시 (모든 배터리) |
| **하층 조건** | 상층 실패 시만 | 항상 발사 |
| **배터리 분리** | 명확히 분리 | 분리 없음 |
| **로그 메시지** | "UPPER LAYER MISS → LOWER" | 해당 로그 없음 |

---

## 4. 종합 결론

### 4.1 질문별 답변 요약

| 질문 | 답변 | 상태 |
|------|------|------|
| **상층 실패 시 하층 대응 가능?** | ❌ 불가능 (동시 발사) | 미구현 |
| **시간제약 상 하층 방어 가능?** | ⚠️ 이론적 가능 (검증 없음) | 부분 구현 |
| **상층 실패 시 시나리오?** | 재교전 메커니즘 작동 | 구현됨 |
| **최대 3회 재교전 가능?** | ✅ 가능 | 구현됨 |

### 4.2 핵심 발견 사항

1. **순차 교전 미구현**: 문서와 달리 상층/하층이 **동시 발사**됨
2. **재교전은 작동**: Shoot-Look-Shoot 메커니즘으로 최대 3회 재시도 가능
3. **시간제약 미검증**: 교전 윈도우 계산은 있으나 실행 시점 검증 없음
4. **문서-코드 불일치**: 문서는 순차 교전을 설명하나 코드는 동시 교전

### 4.3 현재 시스템의 실제 동작

```
위협 발견 → 최적화 (LSAM + MSAM 할당)
    ↓
교전 범위 진입 (flight_progress ≥ 0.6)
    ↓
┌─────────────────────────────────┐
│ LSAM + MSAM 동시 발사 (4발)     │
│ P_kill_total 계산               │
└─────────────────────────────────┘
    ↓
├─ 성공 (P_kill ≥ 0.5) → 종료
└─ 실패 (P_kill < 0.5) → 재교전 (최대 3회)
    ↓
최종 실패 → 자산 피격
```

---

## 5. 개선 권장 사항

### 5.1 순차 교전 구현 (문서 일치)

```python
# 제안: _process_impact() 수정
def _process_impact(self, missile_id, missile):
    assigned_batteries = self.primary_assignments.get_batteries_for_threat(missile_id)
    
    # 1단계: 상층 배터리 분리
    upper_batteries = [bid for bid in assigned_batteries 
                      if any(b['id'] == bid and b['system_type'] == 'LSAM' 
                             for b in self.batteries)]
    lower_batteries = [bid for bid in assigned_batteries 
                      if any(b['id'] == bid and b['system_type'] == 'MSAM' 
                             for b in self.batteries)]
    
    # 2단계: 상층 교전
    P_survival = 1.0
    upper_success = False
    
    for battery_id in upper_batteries:
        # 상층 발사 로직
        ...
    
    P_kill_upper = 1.0 - P_survival
    if P_kill_upper >= 0.5:
        upper_success = True
        return  # 상층 성공 시 종료
    
    # 3단계: 상층 실패 시 하층 교전
    if not upper_success and lower_batteries:
        self.control_panel.log_message(
            f"[INFO] UPPER LAYER MISS → Engaging LOWER LAYER",
            "WARNING"
        )
        
        for battery_id in lower_batteries:
            # 하층 발사 로직
            ...
```

### 5.2 시간제약 검증 추가

```python
def _check_engagement_time_window(self, missile, battery):
    """교전 시간 여유 확인"""
    remaining_time = missile['flight_time'] * (1 - missile['flight_progress'])
    min_required_time = 10  # 최소 10초 필요
    
    if remaining_time < min_required_time:
        return False, "시간 부족"
    
    return True, remaining_time
```

---

## 6. 최종 요약

**현재 시뮬레이터 상태**:
- ✅ **재교전 메커니즘**: 완전 구현 (최대 3회)
- ❌ **순차 교전**: 미구현 (동시 발사)
- ⚠️ **시간제약 검증**: 부분 구현 (최적화 시점만)
- ❌ **상층 실패 → 하층 대응**: 미구현

**MD 문서 주장 검증**:
- "완전 자동 재교전 시 최대 3회 가능" → ✅ **사실**
- "상층 실패 시 하층 즉시 교전" → ❌ **문서와 코드 불일치**

**권장 조치**:
1. 순차 교전 로직 구현 (문서 일치)
2. 시간제약 실시간 검증 추가
3. 문서 업데이트 또는 코드 수정으로 일관성 확보
