# K_ij 교전창 품질 계수 분석 정리

---

## 1. 우리 프로젝트에 맞게 재작성한 K_ij 수식

논문의 표기:

$$K_{ij} = T^{\alpha} \cdot G^{\beta} \cdot K^{\gamma} \cdot E^{\delta}$$

우리 프로젝트(`k_factor_theory.py`, `_combine_factors()`)의 실제 가중치를 적용하면:

$$K_{ij} = T^{0.3} \cdot G^{0.25} \cdot K^{0.25} \cdot E^{0.2}$$

> 가중치 합 = 0.3 + 0.25 + 0.25 + 0.2 = **1.0**
>
> 합이 1.0이므로 **가중 기하 평균 공식의 지수부 `1/(w1+w2+w3+w4)`가 1이 되어**, 아래와 같이 단순화됩니다:
>
> $$K_{ij} = \left(T^{0.3} \cdot G^{0.25} \cdot K^{0.25} \cdot E^{0.2}\right)^{\frac{1}{1.0}} = T^{0.3} \cdot G^{0.25} \cdot K^{0.25} \cdot E^{0.2}$$

경계 조건:

$$K_{ij} \in [0.6,\ 1.0]$$

유효 격추확률 산출:

$$P_{ij}^{\text{eff}} = P_{\text{base}} \times K_{ij}$$

여기서 $P_{\text{base}}$는 살보 격추확률 (LSAM: 0.9775, MSAM: 0.9604).

---

## 2. 4가지 요소 반영 현황

### 2-1. T — 시간적 요소 (Temporal Factor)

**반영 여부: ✅ 반영됨 (핵심 요소, 가중치 0.3으로 가장 높음)**

**이론 정의** (`k_factor_theory.py`, `_calculate_temporal_factor()`):

$$T = k_{\min} + (1 - k_{\min}) \cdot \sqrt{\min\!\left(\frac{t_{\text{duration}}}{t_{\text{optimal}}},\ 1.0\right)}$$

- $t_{\text{optimal}} = 15$ 초 (최적 교전 윈도우)
- $t_{\text{min}} = 2$ 초 (최소 윈도우, 이하면 $T = 0.6$)
- 결과 범위: $[0.6,\ 1.0]$

**MIP 실시간 구현** (`config_mip.py`, `KFactorCache.k_window_lut`):

```
duration ≥ 60초   → T = 1.0
30초 ≤ d < 60초   → T = 0.9 ~ 1.0  (선형 보간)
10초 ≤ d < 30초   → T = 0.8 ~ 0.9  (선형 보간)
d < 10초          → T = 0.6 ~ 0.8  (선형 보간)
```

**의미**: 할당 시점이 늦어질수록 남은 교전 시간이 줄어들어 T가 감소하고, 이에 따라 $K_{ij}$도 낮아져 유효 격추확률이 하락합니다.

---

### 2-2. G — 기하학적 요소 (Geometric Factor)

**반영 여부: ✅ 반영됨 (가중치 0.25)**

**이론 정의** (`k_factor_theory.py`, `_calculate_geometric_factor()`):

$$G = 0.7 + 0.3 \cdot \cos(\theta_{\text{intercept}}) \cdot \exp\!\left(-\left(\frac{|d - d_{\text{opt}}|}{d_{\text{opt}}}\right)^2\right)$$

- $\theta_{\text{intercept}}$: 요격 각도 (정면 요격 = 0° → $\cos = 1$로 최유리)
- $d_{\text{opt}} = 50$ km (최적 교전 거리)
- 결과 범위: $[0.7,\ 1.0]$

**MIP 실시간 구현** (`config_mip.py`, `KFactorCache.k_distance_lut`):

```
거리 비율 0~50%  → G = 0.8 → 1.0  (접근하며 증가)
거리 비율 50~70% → G = 1.0         (최적 교전 구간)
거리 비율 70~100%→ G = 1.0 → 0.6  (이탈하며 감소)
```

실시간에서는 계산 속도를 위해 각도 정보 없이 **거리 비율만으로 근사**합니다.

**의미**: 탄도미사일이 포대의 최적 교전 거리에 있을 때 G=1.0이고, 너무 가깝거나 멀어지면 감소합니다.

---

### 2-3. K — 운동학적 요소 (Kinematic Factor)

**반영 여부: ✅ 반영됨 (가중치 0.25)**

**이론 정의** (`k_factor_theory.py`, `_calculate_kinematic_factor()`):

$$K = f_{\text{altitude}}(h) \cdot f_{\text{speed}}(v)$$

**고도 함수** $f_{\text{altitude}}$:

$$f_{\text{altitude}}(h) = \begin{cases} 0.8 & h < 5 \text{ km (저고도, 어려움)} \\ 1.0 - 0.2 \cdot \frac{|h - 30|}{30} & 5 \leq h \leq 80 \text{ km (최적 30km)} \\ 0.9 & h > 80 \text{ km (고고도)} \end{cases}$$

**속도 함수** $f_{\text{speed}}$:

$$f_{\text{speed}}(v) = \begin{cases} 0.8 & v > 5 \text{ km/s (초고속, 어려움)} \\ 1.0 - 0.2 \cdot \max(0,\ v/2 - 1) & \text{그 외} \end{cases}$$

- 결과 범위: $[0.8,\ 1.0]$ (타 요소에 비해 범위가 좁음 — 설계 선택)

**의미**: NODONG(고속·고고도)은 K가 낮아 요격 난이도를 반영하고, SCUD-B(저속·저고도)는 K가 높습니다.

---

### 2-4. E — 환경적 요소 (Environmental Factor)

**반영 여부: ⚠️ 부분 반영 (가중치 0.2, 기상 조건은 이상적으로 고정)**

**이론 정의** (`k_factor_theory.py`, `_calculate_environmental_factor()`):

$$E = \underbrace{\left(0.9 + 0.1 \cdot \frac{\rho(h)}{\rho_0}\right)}_{\text{대기 밀도 항}} \cdot \underbrace{W_{\text{factor}}}_{\text{기상 조건}}$$

대기 밀도 모델 (지수 감소):

$$\rho(h) = \rho_0 \cdot e^{-h / 8.5}$$

- $\rho_0 = 1.225$ kg/m³ (해수면 대기 밀도)
- 결과 범위: $[0.9,\ 1.0]$

**현재 한계**:

```python
weather_factor = 1.0  # 기상·전자전 조건은 이상적으로 가정
```

기상 및 전자전(ECM) 요소는 **이상 조건(=1.0)으로 고정**되어, 대기 밀도 항만 실제로 동작합니다.

---

## 3. 요소별 반영 현황 요약표

| 요소 | 이름 | 가중치 | 이론 정의 | MIP 실시간 구현 | 완전성 |
|------|------|--------|-----------|----------------|--------|
| T | 시간적 | **0.30** | 윈도우 지속시간 기반 | `k_window_lut` (1초 단위 LUT) | ✅ 완전 |
| G | 기하학적 | 0.25 | 각도 + 거리 | `k_distance_lut` (거리 비율 근사) | 🔶 근사 (각도 미포함) |
| K | 운동학적 | 0.25 | 고도 + 속도 | 이론 함수 사용 | ✅ 완전 |
| E | 환경적 | 0.20 | 대기 + 기상 + ECM | 대기 밀도만, 기상=1.0 고정 | ⚠️ 부분 |

---

## 4. Figure 3와 서술 문장의 논리적 연결성 분석

### Figure 3가 보여주는 것

Figure 3는 **교전 가능 시간창(윈도우 길이)**에 따라 유효 격추확률이 달라짐을 시각화합니다:

- **경우 ①** (긴 윈도우): $K_{ij}$가 크다 → $P_{\text{eff}} = P_{\text{base}} \times K_{ij}$가 크다
- **경우 ②** (짧은 윈도우): $K_{ij}$가 작다 → $P_{\text{eff}}$가 작다

### 연결 고리 분석

본문 텍스트와 Figure 3의 논리 흐름:

```
[1] K_ij = T^0.3 · G^0.25 · K^0.25 · E^0.2  (수식 정의)
        ↓
[2] T 요소 = 교전 윈도우 길이에 비례         (T의 의미 설명)
        ↓
[3] Figure 3: 긴 윈도우(①) vs 짧은 윈도우(②) 시각화  ← 여기서 T 효과를 그림으로 보임
        ↓
[4] "유효 격추확률 = P_base × K_ij" 확인 문장
```

**연결의 강점**: Figure 3는 K_ij의 **T 요소가 지배적임**을 직관적으로 증명합니다. 수식 정의 → 가장 영향력 있는 요소(T, 가중치 0.3) → 시각적 예시 순서로 논리가 흐릅니다.

**논리적 주의점**: Figure 3는 4개 요소 중 **T 요소 하나만** 시각화합니다. 나머지 G, K, E 요소의 효과는 그림에서 보이지 않습니다. 따라서 Figure 3 이후에 다음과 같은 보완 설명이 있으면 더 완결적입니다:

> *"Figure 3는 시간적 요소(T)가 K_ij에 미치는 영향을 대표적으로 나타낸 것이며, 기하학적·운동학적·환경적 요소도 동일한 원리로 K_ij를 조정한다."*

**마지막 문장의 역할**: `"유효 격추확률은 기본 살보 격추확률 Pu/Pl에 교전창 품질 계수 Kij를 곱하여 산출한다"` 는 Figure 3의 시각적 설명을 **수식으로 재확인**하는 닫는 문장입니다. Figure 3가 직관을 제공하고, 이 문장이 수식적 근거를 재명시하는 구조로, 논리적 연결성은 **적절**합니다.
