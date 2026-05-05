# 다층 미사일방어체계의 동적 WTA 모형 및 해법

**OOO\* · OOO\*\* · OOO\*\*\* · OOO\*\*\*†**

\*공군사관학교 OOO과, \*\*㈜ LIG

---

> **(초 록)** Republic of Korea is (
>
> **Keywords**: Ballistic Missile Defense~~

---

## 1. 서 론

현대전에서 탄도미사일 위협은 단거리 탄도미사일(SRBM)부터 대륙간탄도미사일(ICBM)까지 다층화되었으며, 기동 탄두(MaRV)·극초음속 활공체(HGV) 등 요격 난이도가 높은 신형 위협과 방어 자원을 의도적으로 소진시키는 포화 공격 전술의 확산으로 미사일 방어체계의 운용 난이도가 지속적으로 상승하고 있다. 그러나 이스라엘의 아이언 돔(Iron Dome)은 2011년 운용 개시 이후 Operation Protective Edge(2014) 기준 교전 대상 로켓의 90% 수준을 차단하여[A] 다층 미사일 방어체계의 전략적 효용을 실증하였으며, 이를 계기로 미국의 THAAD·골든돔, 프랑스·이탈리아의 SAMP/T, 대한민국의 KAMD(L-SAM, M-SAM) 등 독자 다층 방어체계 구축이 국제적으로 가속화되고 있다. 이러한 체계들의 목표는 다변화·다양화되는 탄도미사일을 탄착 전에 차단하여 민간 및 군 피해를 최소화하는 것이다. 이를 위해서는 다양한 위협 시나리오에서 방어체계의 운용 효과를 사전에 분석하고 최적화하는 과정이 필수적이다. 그러나 실제 위협 환경에서의 방어 운용은 막대한 비용과 안전 제약으로 직접 실험이 불가능하며, 수리적 해석 모델만으로는 다층 방어체계의 복잡한 동적 상호작용을 충분히 포착하기 어렵다. 이러한 한계를 보완하는 수단으로서 Modeling and Simulation(M&S)은 다양한 위협 시나리오를 실전에 근접하게 재현하고 반복 검증할 수 있는 대표적인 분석·검증 수단으로 자리잡고 있다.

이러한 다층 방어 M&S 환경에서 핵심 과제는 한정된 요격 자원을 복수의 위협에 최적으로 배분하는 동적 무기-표적 할당(Dynamic Weapon-Target Assignment, DWTA) 문제다. 무기-표적 할당(Weapon-Target Assignment, WTA) 문제는 1958년 Manne이 정의하고 Lloyd와 Witsenhausen(1986)이 NP-complete임을 증명한 비선형 조합 최적화 문제로[12, 13], 아군 자원의 중요도·탄도 경로·차단 성공률 등 상충하는 요소들을 동시에 고려하는 구조를 가진다. 다층 방어 환경에서의 DWTA는 탄도미사일 궤적 기반의 교전 가능 시간창(Engagement Time Window), 상·하층 방어체계 간 상호 의존성, 지휘관의 human-in-the-loop 의사결정 시간이 복합적으로 작용하여 문제 복잡도가 한층 높아진다.

기존 연구는 크게 두 계열로 발전해 왔다. 규칙 기반 휴리스틱·유전자 알고리즘(GA)·모의담금질(SA) 등 메타휴리스틱 계열은 빠른 계산 속도를 확보하였으나 전역 최적해를 보장하지 못한다[14, 16]. 반면 혼합정수계획(Mixed Integer Programming, MIP) 및 비선형 솔버 계열은 전역 최적해 탐색이 가능하나 15개 위협 기준 30초 이상이 소요되어 실시간 운용이 완전히 불가능하다[15, 17]. 더욱이 두 계열 모두 교전 가능 시간창의 동적 변화, K-factor 기반 교전창 품질 열화, 다층 방어체계의 Shoot-Look-Shoot 상호의존성과 같은 현실적 제약을 수리모형에 통합하지 못하였다.

본 연구는 MIP의 전역 최적성을 유지하면서 위 현실적 제약을 모형에 통합하고, 동시에 실시간 처리를 달성하는 해법을 제안한다. 구체적으로, McCormick 선형화[11]를 통해 DWTA 목적함수의 비선형·비볼록 Bilinear Term을 4개의 선형 부등식으로 등가 변환하고, 양방향 인덱스·희소 변수 생성·K-factor 룩업 테이블·Warm-start를 결합하여 실전 운용 규모(20개 위협 기준)에서 평균 0.1초 이내의 최적화를 달성한다.

본 논문의 구성은 다음과 같다. 2장에서는 탄도미사일의 비행 특성과 WTA 관련 이론 및 기존 해법의 한계를 고찰하고, 3장에서는 동적 WTA 수리모형과 McCormick 기반 MIP 해법을 상세히 기술한다. 4장에서 실험 결과를 분석하고, 5장에서 결론 및 향후 연구 과제를 제시한다.

---

## 2. 이론적 고찰

### 2.1 탄도미사일의 비행특성

탄도미사일의 비행단계는 \<Figure 1\>과 같이 초기 연료소모 단계인 부스트단계(Boost Phase), 추진체의 연소가 종료된 후 재진입 전까지인 중간단계(Midcourse Phase), 재진입부터 목표지점까지 떨어지는 종말 단계(Re-entry Phase)인 3단계로 크게 나눌 수 있다[2, 5, 6, 8].

\< Figure 1 \> Ballistic Missile Flight Phases

이중 추력 단계는 3단계로 구분되는데, 발사 직후 일정시간 수직으로 비행하는 '수직상승 단계', 사전 입력된 프로그램에 의해 선회하는 '프로그램 선회(또는 무양력 선회, 피치 선회) 단계', 연소가 종료되는 시점까지 동일한 자세로 비행하는 '등자세 선회 단계'로 나누어진다[2, 5, 6, 8].

탄도미사일의 비행특성을 과거 연구사례에 따라 정리하면 탄도미사일의 추력, 질량, 직경 등 기본 제원과 추력단계에서의 비행계획(피치 프로그램)에 따라 각각 다른 비행거리, 정점고도, 비행시간, 속도 등을 가진다는 점이다[5, 6, 8, 10]. 이러한 탄도미사일의 비행특성을 방어자 입장에서 고려하면, 탄도미사일 발사위치로부터 이격거리가 같은 목표지점을 공격하는 경우에도 비행궤적에 따라 요격체계의 요격가능시간이 다르게 되므로, 비행궤적에 기초한 위협분석과 요격가능성 평가가 이루어져야 한다[4].

따라서, 다층 미사일방어체계의 동적 WTA 문제 해결을 위해서는 탄도미사일 비행궤적에 기초하여 동적 수리모형 수립이 필요하다. 따라서 다층 미사일방어체계의 동적 WTA 문제 해결을 위해서는 탄도미사일 비행궤적에 기초한 동적 수리모형 수립이 필요하다. 본 연구의 대응 대상 미사일 유형은 \<Table 2\>[5, 6, 8, 10], 시뮬레이션 적용 방어체계 제원은 \<Table 1\>에 각각 제시하였다. \<Table 1\>의 수치는 공식 군사 규격이 아닌 시뮬레이션 가정값이며, 단발 Pk(L-SAM: 0.85, M-SAM: 0.80)에 대한 민감도 분석은 4장에서 다룬다. 살보 Pk는 $1-(1-P_k)^2$로 산출하고, 동시 교전 능력은 화력통제 운용 제약을 반영하여 포대당 $C = 3$으로 설정한다(3.1절 참조).

\<Table 2\> Classification of Ballistic Missiles by Range [5, 6, 8, 10]

| Type | Classification | Representative | Range | Flight Time | Max. Speed |
|------|---------------|----------------|-------|-------------|------------|
| CRBM | Short-range BM | Scud-B | 300 km | ~240 s | Mach 4.5–5.0 |
| MRBM | Medium-range BM | Nodong | 1,300 km | ~480–600 s | Mach 9.0+ |
| IRBM | Intermediate-range BM | — | 3,000–5,500 km | 900–1,200 s+ | Mach 12.0–15.0+ |

\<Table 1\> Interceptor System Specifications Used in This Study (Simulation Parameters)

| System | Engagement Altitude | Engagement Range | Simultaneous Engagement | Single-shot Pk | Salvo Pk (2-shot) |
|--------|--------------------|-----------------:|------------------------|:--------------:|:-----------------:|
| L-SAM (upper tier) | 40–70 km | 150–300 km | 10 targets/battery | 0.85 | 0.9775 |
| M-SAM (lower tier) | 15–40 km | 5–50 km | 8 targets/battery | 0.80 | 0.96 |



### 2.2 WTA 문제 해법

#### 2.2.1 WTA 문제의 정의 및 복잡도

WTA 문제는 $m$개의 무기를 $n$개의 표적에 배분하여 표적의 기댓값 생존 확률 합을 최소화하는 조합 최적화 문제로, Manne(1958)이 최초로 수리모형으로 정의하였다[12]. Lloyd와 Witsenhausen(1986)은 이 문제가 NP-complete임을 증명하였으며[13], 위협 수 $n$ 증가 시 탐색 공간이 $O(2^n)$으로 지수 증가한다. 다층 방어 환경에서의 DWTA는 탄도미사일 궤적 기반의 교전 가능 시간창(Engagement Time Window), 상·하층 방어체계 간 상호 의존성, 지휘관의 human-in-the-loop 의사결정 시간이 복합적으로 작용하여 정적 WTA에 비해 문제 복잡도가 한층 높아진다.

#### 2.2.2 기존 해법의 두 계열과 한계

기존 WTA 해법은 크게 두 계열로 분류된다(Kline et al., 2019)[14].

**첫째, 휴리스틱·메타휴리스틱 계열**

규칙 기반 휴리스틱은 0.01초 이내의 빠른 계산이 가능하나 최적성이 보장되지 않으며, 다층 방어 환경의 복잡한 제약 구조에서 성능이 급격히 저하된다. 유전자 알고리즘(GA)·모의담금질(SA)·입자 군집 최적화(PSO) 등 메타휴리스틱은 근사 최적해 탐색이 가능하나, 수십 초에서 수 분의 계산 시간이 소요되어 1초 이내의 실시간 운용 요건을 충족하지 못한다(Ahuja et al., 2007)[15]. 이들 방법은 이진-연속 Bilinear Term 구조를 직접 처리하지 않으므로 전역 최적해 보장이 원천적으로 불가능하다.

**둘째, MIP·비선형 솔버 계열**

이론적으로 전역 최적해 탐색이 가능하나, IPOPT·BARON 등 비선형 솔버를 직접 적용할 경우 15개 위협 기준 30초 이상이 소요되어 실시간 운용이 완전히 불가능하다. Lu와 Chen(2021)이 정적 WTA(SWTA)에 대해 열 열거(column enumeration) 기반 정수선형계획으로 80×80 인스턴스를 0.40초에 풀었으나[17], 이는 교전 가능 시간창·K-factor·다층 상호의존성이 없는 정적 문제에 한정된 성과이다. Andersen et al.(2022)의 branch-and-adjust 알고리즘은 1,500×1,000 인스턴스를 2시간 이내에 처리하지만, 역시 동적 시간창을 포함하지 않는다[18].

결국 두 계열 모두 최적성과 실시간성을 동시에 충족하지 못한다는 근본적 트레이드오프를 해소하지 못하고 있으며, 이것이 본 연구의 출발점이다.

#### 2.2.3 기존 DWTA 연구의 현실적 제약 미반영 문제

기존 DWTA 연구들은 알고리즘 탐색 효율에 집중한 나머지, 실전 운용 환경에서 필수적인 다음 제약들을 충분히 반영하지 못했다.

첫째, **교전 가능 시간창(Time Window)의 동적 변화**다. 탄도미사일의 비행 단계(부스트·중간코스·종말)에 따라 각 방어체계의 교전 가능 구간이 실시간으로 변화한다. 기존 연구 대부분은 교전 가능성을 고정 이진값(가능/불가능)으로 단순화하여 이 시간적 변화를 모형에 반영하지 않았다.

둘째, **교전창 품질(K-factor)의 연속적 열화**다. 교전 윈도우 내에서도 할당 시점이 늦어질수록 가용 추적 시간이 줄어 요격 확률이 감소한다. 이 시간-거리 복합 품질 계수를 명시적으로 결정변수로 포함한 DWTA 연구는 존재하지 않는다.

셋째, **다층 방어체계의 계층 간 상호의존성**이다. 상층(L-SAM)의 요격 성공 여부가 하층(M-SAM)의 교전 필요성과 자원 배분에 직접 영향을 미치는 Shoot-Look-Shoot(SLS) 구조는, 단층 방어를 가정하는 기존 연구로는 포착되지 않는다.

이상의 세 가지 현실적 제약을 수리모형에 통합하면서도 실시간 처리 요건을 만족하는 해법은 현재까지 보고된 바 없다. 본 연구는 McCormick 선형화를 통해 이를 동시에 달성한다.

\<Table 3\> Comparison of WTA Solution Approaches

\<Table 3\> Comparison of WTA Solution Approaches

| Method | Representative | Computation Time | Optimality | Time Window | Dynamic Pk (K-factor) | Multi-layer |
|--------|---------------|-----------------|------------|-------------|----------------------|-------------|
| Rule-based heuristic | MMR, etc. | ≤0.01 s [16] | Not guaranteed | No | No | No |
| Metaheuristic | GA, SA, PSO | ~s to min [14, 16] | Near-optimal | Partial [14] | No | No |
| Nonlinear solver (direct) | IPOPT, BARON | ≥30 s [15] | Global optimal | No | No | No |
| Static WTA linearization | Lu(2021), Andersen(2022) | 0.4 s ~ 2 h [17, 18] | Global optimal | No | No | No |
| **This study (McCormick MIP)** | **CBC/HiGHS** | **0.22–0.77 s** | **Global optimal** | **Yes** | **Yes** | **Yes** |

---

## 3. 다층 미사일방어체계의 동적 WTA 모형 및 해법

본 장에서는 다층 미사일방어체계의 동적 WTA 문제 해결을 위해 동적 모형을 정립하고 이를 위한 해법을 제시한다.

### 3.1 동적 WTA 모형

#### ◦ 가정사항

본 모형의 가정사항은 다음과 같이 설정하였다.

첫째, 탄도미사일의 위험도는 해당 탄도미사일의 예상 낙하지역의 중요도에 따라 설정한다.

둘째, 적 탄도미사일의 공격계획(시간, 규모)은 알 수 없다.

셋째, 각각의 탄도미사일에는 각각 최대 상층 방어체계 1개, 하층 방어체계 1개를 요격미사일을 할당하며, Shot-Look-Shot 방법에 따라 운용한다.

넷째, 탄도미사일에 대한 방어체계의 일반적인 격추확률, 동시교전 능력 및 유도탄 보유량은 주어져 있다.

#### ◦ 집합 및 인덱스

| 기호 | 정의 |
|------|------|
| $u \in U$ | 상층방어체계 |
| $l \in L$ | 하층방어체계 |
| $j \in J(t)$ | 시점 $t$에서 아직 제거되지 않았고, 교전 대상이 되는 탄도미사일의 집합 |

#### ◦ 파라미터

| 파라미터 | 정의 |
|----------|------|
| $a_{uj}(t)$ / $a_{lj}(t)$ | 시점 $t$ 기준, 상/하층 방어체계 $u$ / $l$이 탄도미사일 $j$를 교전하기 위해 추적을 시작할 수 있는 가장 이른 시각 |
| $b_{uj}(t)$ / $b_{lj}(t)$ | 시점 $t$ 기준, 상/하층 방어체계 $u$ / $l$이 탄도미사일 $j$를 교전(명중)할 수 있는 최종 시각 |
| $W_{uj}(t)$ / $W_{lj}(t)$ | 시점 $t$ 기준, 상/하층 방어체계 $u$ / $l$의 탄도미사일 $j$에 대한 교전 가능 시간창 ※ $W_{uj}(t) = [a_{uj}(t),\, b_{uj}(t)]$ |
| $M_u(t)$ / $M_l(t)$ | 시점 $t$에서 상/하층 방어체계 $u$ / $l$이 보유하고 있는 유도탄 수량 |
| $C_u$ / $C_l$ | 상/하층 방어체계 $u$ / $l$의 동시교전 능력 |
| $T_j$ | 탄도미사일 $j$의 위험도 |
| $P_u$ / $P_l$ | 탄도미사일에 대한 상/하층 방어체계 $u$ / $l$의 일반 격추확률 |
| $K_{uj}$ / $K_{lj}$ | 탄도미사일 $j$에 대한 상/하층 방어체계 $u$ / $l$의 격추확률 함수 ※ $K_{uj}$ / $K_{lj} \in [0, 1]$ |

#### ◦ 결정변수

| 변수 | 정의 |
|------|------|
| $x_{uj}(t)$ / $x_{lj}(t)$ | 상/하층 방어체계 $u$ / $l$이 교전가능 시간창 $W_{uj}(t)$ / $W_{lj}(t)$를 현재 시점 $t$의 교전계획에 포함하면 1, 아니면 0 |

> **[보충 — md §3.1.4]** K-factor $k_{ij}(t)$는 교전 윈도우 내에서 할당 시점에 따른 가용 시간을 반영한 품질 계수이다.
>
> $$k_{ij}(t) = k_{\min} + (k_{\max} - k_{\min}) \cdot \frac{t_{\text{remaining}}}{t_{\text{window}}}$$
>
> 종합 K-factor는 시간적(Temporal), 기하학적(Geometric), 운동학적(Kinematic), 환경적(Environmental) 요소를 가중 기하 평균으로 결합한다.
>
> $$k_{\text{combined}} = \text{temporal}^{0.4} \times \text{geometric}^{0.25} \times \text{kinematic}^{0.2} \times \text{environmental}^{0.15}$$

#### ◦ 수리모형

$$\min_{x(t)}\;\sum_{j \in J(t)} T_j \left\{ \prod_{u \in U}(1 - x_{uj}(t)\,K_{uj}\,P_u) \cdot \prod_{l \in L}(1 - x_{lj}(t)\,K_{lj}\,P_l) \right\} \tag{1}$$

**subject to**

$$\sum_{u \in U} x_{uj}(t) \leq 1, \quad \forall j \in J(t) \tag{2}$$

$$\sum_{l \in L} x_{lj}(t) \leq 1, \quad \forall j \in J(t) \tag{3}$$

$$\sum_{j \in J(t)} x_{uj}(t) \leq M_u(t), \quad \forall u \in U \tag{4}$$

$$\sum_{j \in J(t)} x_{lj}(t) \leq M_l(t), \quad \forall l \in L \tag{5}$$

$$\sum_{j:\,\theta \in W_{uj}(t)} x_{uj}(t) \leq C_u, \quad \forall u \in U,\; \forall \theta \in \mathbb{R} \tag{6}$$

$$\sum_{j:\,\theta \in W_{lj}(t)} x_{lj}(t) \leq C_l, \quad \forall l \in L,\; \forall \theta \in \mathbb{R} \tag{7}$$

본 수리모형의 목적함수(식 (1))는 아군의 중요시설을 공격하는 각 탄도미사일의 위험도의 합을 최소화하는 것이다. 각 탄도미사일의 위험도는 탄도미사일이 가지고 있는 위험도에 상/하층 방어체계의 요격 미사일이 교전계획에 따라 할당되었을 경우 방어되지 못할 확률을 곱하여 계산한다. 탄도미사일이 방어되지 못할 확률은 병렬신뢰도 개념을 적용하였으며, 탄도미사일에 대한 상/하층 방어체계의 일반적으로 알려진 격추확률($P_{u/l}$)에 각각의 탄도미사일에 대한 방어체계의 교전가능 시간창(time window)의 길이와 요격각도와 거리에 따라 동역학적 요소 등을 반영한 격추확률 함수($K_{uj/lj} \in [0,1]$)를 곱하여 계산하였다. 특히 목적함수는 이진 변수 $x_{uj}$, $x_{lj} \in \{0,1\}$와 연속 변수 $K_{uj}$, $K_{lj} \in [0,1]$의 곱셈 항(Bilinear Term) 및 다항곱(Multilinear Product)을 포함하여 비선형·비볼록(Non-convex) 구조를 가진다. 이로 인해 다수의 지역 최적해가 발생하며, 이것이 3.3절에서 선형화를 적용하는 근거가 된다.

본 모형은 동적 할당을 위해 크게 두가지 방법을 적용하였다. 첫 번째 방법으로 결정변수[$x_{uj/lj}(t)$]는 상/하층 방어체계가 교전가능 시간창[$W_{uj/lj}(t)$]을 교전계획에 포함하는지 여부를 결정하는 것으로 0과 1의 이진변수로 표현하였다. 두 번째 방법으로 미래의 적 탄도미사일 공격은 불확실하고 상태가 계속 바뀌므로 시간 경과에 따라 목적함수를 재계산하는 rolling horizon 방식을 적용하였다. 이 방법은 매 시점마다 각 시점 기준으로 최선의 방법을 반복해서 계산한다.

첫 번째 및 두 번째 제약식(식 (2), (3))은 각각의 탄도미사일에 대해 상층 및 하층 방어체계의 유도탄을 각각 최대 1발씩 할당한다.

세 번째 및 네 번째 제약식(식 (4), (5))은 각각의 탄도미사일에 대해 상층 및 하층 방어체계는 각각의 체계에서 보유하고 있는 유도탄의 수량 내에서 할당한다.

레이다는 물리적/기술적 한계로 인해 제한된 능력으로 표적을 다루게 된다[1]. 이를 고려하여 다섯 번째 및 여섯 번째 제약식(식 (6), (7))은 각각의 상층 및 하층 방어체계의 동시 교전능력 범위 내에서 할당이 되도록 제한하였다. 여기에서 $\theta \in W_{ij}(t)$는 특정 시각 $\theta$에서 유효한 시간창을 의미하며, 유효한 시간창을 합친 수는 각 방어체계의 동시교전 능력[$C_u / C_l$]을 초과할 수 없다.

### 3.2 모형의 구현

#### ◦ 탄도미사일 궤적 시뮬레이션

탄도미사일 비행궤적에 기초한 동적 WTA 모형을 위해 탄도미사일의 비행단계별(부스트 단계, 중간단계, 종말단계) 동역학적 특성을 반영한 탄도미사일 궤적 시뮬레이터를 제작하였다.

탄도미사일 궤적 시뮬레이션을 통해 \<Figure 2\>와 같이 탄도미사일 제원, 비행계획을 반영한 다양한 종류의 탄도미사일 궤적을 생성하였다.

\< Figure 2 \> Ballistic Missile Trajectory Simulation

#### ◦ Time Window 및 격추확률 계산

상/하층 방어체계의 탄도미사일에 대한 교전 가능 시간창(time window)을 계산하기 위한 방법은 \<Figure 3\>과 같이 탄도미사일 궤적 시뮬레이션에 의한 탄도미사일 궤적과 각각의 방어체계의 방어영역이 겹치는 위치와 시각을 계산하였다.

\< Figure 3 \> Conceptual Diagram of the Ballistic Missile Engagement Time Window Calculation Method for Missile Defense Systems

격추확률 계산은 일반적인 격추확률에 Time Window 등을 적용하여 함수화하여 적용하였다. \<Figure 4\>와 같이 Time Window가 긴 경우(①)에 Time Window가 짧은 경우(②)보다 더 높은 격추확률을 부여하였다.

\< Figure 4 \> Conceptual Diagram for Interception Probability Calculation

> **[보충 — md §3.2.2]** 교전창 품질 $Q_w$는 교전 가능 시간의 길이에 따라 아래와 같이 구간별로 정의된다.
>
> $$Q_w = \begin{cases} 0.2 \times (\Delta t / t_{\min}) & 0 \leq \Delta t < t_{\min} \\ (\Delta t - t_{\min}) / (t_{\text{opt}} - t_{\min}) & t_{\min} \leq \Delta t < t_{\text{opt}} \\ 1.0 & \Delta t \geq t_{\text{opt}} \end{cases}$$
>
> 체계별 파라미터: L-SAM은 $t_{\min} = 12$ s, $t_{\text{opt}} = 35$ s; M-SAM은 $t_{\min} = 8$ s, $t_{\text{opt}} = 20$ s.

#### ◦ 수리모형에 적용하기 위한 Time Window 및 격추확률의 자료 저장 구조

각각의 탄도미사일에 대하여 각각의 상층 및 하층 방어체계의 Time Window 및 격추확률 계산 결과는 수리모형에 적용할 수 있도록 \<Figure 5\>와 같은 자료구조에 따라 저장한다.

\< Figure 5 \> Conceptual Diagram of Time Window and Interception Probability Matrix

Time Window는 탄도미사일이 요격체계의 교전가능 공간을 통과하는 구간에 탄도미사일 탐지 및 요격미사일 비과시간의 추가가 필요하므로[3], 이를 반영하여 계산하였다.

> **[보충 — md §3.2.3]** 평가결과 통합 자료구조는 다음과 같이 계층적으로 구성된다.
>
> ```
> MissileDefenseEvaluationData
> ├── threats: List[Threat]
> ├── interceptor_systems: List[InterceptorSystem]
> ├── engagement_windows: Dict[(system_id, threat_id), WindowData]
> ├── intercept_probability: Dict[(system_id, threat_id), ProbabilityData]
> └── metadata: EvaluationMetadata
> ```
>
> 궤적 샘플링 간격은 **0.5초 단위**이며, 각 시각에서의 3차원 위치, 거리, 고도, 속도, K-factor를 기록한다.

### 3.3 해법 개발

> **[구조 확정 — 내용 추후 작성]**
>
> #### 3.3.1 선형화의 필요성
> *(3.1의 식(1)에 포함된 이진-연속 Bilinear Term이 비선형·비볼록의 원인임을 재확인하고, 선형화의 필요성 기술 예정)*
>
> #### 3.3.2 McCormick 선형화 기법
> *(보조 변수 $w_{ij}$ 도입, 4개 선형 부등식 유도, 등가 변환 증명 기술 예정)*
>
> $$w_{ij} \geq k_{\min} \cdot P_j^{(m)} \cdot x_{ij} \tag{8}$$
> $$w_{ij} \geq k_{ij} \cdot P_j^{(m)} - k_{\max} \cdot P_j^{(m)} \cdot (1 - x_{ij}) \tag{9}$$
> $$w_{ij} \leq k_{\max} \cdot P_j^{(m)} \cdot x_{ij} \tag{10}$$
> $$w_{ij} \leq k_{ij} \cdot P_j^{(m)} \tag{11}$$
>
> #### 3.3.3 MIP 문제 구성
> *(Binary Tree 구조 기반 다항곱 선형화, 최종 MIP 모형 기술 예정)*
>
> #### 3.3.4 Branch-and-Bound 기반 최적화
> *(LP Relaxation → Branching → Bounding → Termination 절차 기술 예정)*
>
> #### 3.3.5 실시간 처리를 위한 자료구조 및 구현 최적화
> *(양방향 인덱스, uint64 비트마스크, 희소 변수 생성, K-factor LUT, Warm-start 기술 예정)*

---

## 4. 실험결과 및 분석

> **[구조 확정 — 내용 추후 작성]**
>
> ### 4.1 실험 환경 및 시나리오 설계
> *(위협 수 규모별 4개 그룹, 8개 시나리오, MIP 솔버 설정, 반복 횟수 기술 예정)*
>
> ### 4.2 문제 규모 분석
> *(McCormick 선형화 후 변수 수·제약 수 준선형 성장 분석 예정)*
>
> | 시나리오 | 위협 수 | 포대 수 | 평균 변수 수 | 평균 제약 수 |
> |----------|---------|---------|-------------|-------------|
> | SMALL_3  | 3  | 6  | 29    | 84    |
> | SMALL_5  | 5  | 6  | 48    | 130   |
> | SMALL_8  | 8  | 6  | 81    | 211   |
> | MEDIUM_10 | 10 | 6 | 103   | 266   |
> | BASELINE_15 | 15 | 6 | 147 | 375   |
> | MEDIUM_20 | 20 | 6 | 185   | 473   |
> | LARGE_40 | 40 | 6  | 630   | 1,515 |
> | STRESS_100 | 100 | 15 | 1,137 | 2,671 |
>
> ### 4.3 확장성 분석: 위협 규모별 성능
> *(성공률, 평균/최대 풀이 시간, Timeout률, Warm-start률 분석 예정)*
>
> | 시나리오 | 위협 수 | 성공률 (%) | 평균 풀이 시간 (s) | Timeout률 (%) | Warm-start률 (%) |
> |----------|---------|-----------|-----------------|--------------|----------------|
> | SMALL_3  | 3   | 100.0 | 0.220 | 0.0 | 95.5 |
> | SMALL_5  | 5   | 100.0 | 0.384 | 0.0 | 98.3 |
> | SMALL_8  | 8   | 100.0 | 0.626 | 0.0 | 98.4 |
> | MEDIUM_10 | 10 | 100.0 | 0.447 | 0.0 | 98.4 |
> | BASELINE_15 | 15 | 100.0 | 0.382 | 0.0 | 98.5 |
> | MEDIUM_20 | 20 | 100.0 | 0.256 | 0.0 | 98.5 |
> | LARGE_40 | 40 | 100.0 | 0.453 | 0.0 | 98.6 |
> | STRESS_100 | 100 | 96.0 | 0.769 | 0.0 | 94.0 |
>
> ### 4.4 McCormick 선형화 효과 검증
> *(동일 조건(15개 위협·동일 하드웨어)에서 비선형 솔버 직접 적용 대비 79배 이상 속도 향상, 등가 변환 검증 예정)*
>
> ### 4.5 Warm-start 효과 검증
> *(Cold-start 대비 4–5배 처리 속도 향상, 적용률 94–98.6% 분석 예정)*

---

## 5. 결론

> **[구조 확정 — 내용 추후 작성]**
>
> ### 수리적 기여
> *(McCormick 등가 변환을 통한 전역 최적해 보장 수학적 증명 기술 예정)*
>
> ### 알고리즘적 기여
> *(Binary Tree 선형화, 하이브리드 사전계산, Warm-start 통합으로 평균 0.1 s 실시간 최적화 달성 기술 예정)*
>
> ### 실험적 기여
> *(3–40개 위협 성공률 100%, 평균 풀이 시간 0.65 s 이하, 100개 극한 시나리오 성공률 96% 기술 예정)*
>
> ### 향후 연구과제
> *(100개 이상 대규모 시나리오 문제 분해·병렬 솔버 적용, 전자전·기상 포함 확률적 모형 확장, 강건 최적화, HITL 검증 기술 예정)*

---

## Acknowledgement

This paper is the result of research supported by LIG Nex1 Co., Ltd.

---

## References

[1] Cha, S.B., Park, S.H., Jung, J.H., Kim, W.C. and Choi, I.O., Efficient Dwell Time Allocation Method for Multi-Function Radar Resource Management, *Journal of KIIT*, 2023, Vol. 21, No. 5, pp. 91-100.

[2] Hong, D.W., Yim, D.S. and Choi, B.W., Application and Determination of Defended Footprint Using a Simulation Model for Ballistic Missile Trajectory, *Journal of the KIMST*, 2018, Vol. 21, No. 4, pp. 551-561.

[3] Hong, S.W., Song, J.Y. and Chang, Y.K., Analysis on Time Performance of Intercept System for Engagement Plan of Missile Defense System, *Journal of the KIMST*, 2019, Vol. 22, No. 1, pp. 93-105.

[4] Im, J.S., Yoo, B.C., Kim, J.H. and Choi, B.W., A Study of Multi-to-Majority Response on Threat Assessment and Weapon Assignment Algorithm: by Adjusting Ballistic Missiles and Long-Range Artillery Treat, *Journal of Korean Society of Industrial and Systems Engineering*, 2021, Vol. 44, No. 4, pp. 43-52.

[5] Kim, J.W. and Kwon, Y.S., Analysis of Flight Trajectory Characteristics of the MRBM by Adjusting the Angle of a Flight Path, *Journal of the KIMST*, 2015, Vol. 18, No. 2, pp. 173-180.

[6] Kwak, K.H., Kim, K.T., Choi, B.W. and Kyung, J.H., Ballistic Missile Trajectory Prediction Model Using Observation Data, *Journal of Korean Society of Industrial and Systems Engineering*, 2025, Vol. 48, No. 2, pp. 111-121.

[7] Kwak, K.H., Lee, J.Y. and Jung, C.Y., The Optimal Allocation Model for SAM Using Multi-Heuristic Algorithm: Focused on Aircraft Defense, *Journal of the Korean Operations Research and Management Science Society*, 2009, Vol. 34, No. 4, pp. 43-55.

[8] Kwon, Y.S. and Choi, B.S., Analysis of the Flight Trajectory Characteristics of Ballistic Missiles, *Journal of the Military Operations Research Society of Korea*, 2006, Vol. 32, No. 1, pp. 176-187.

[9] Lee, J.Y. and Kwak, K.H., The Optimal Allocation Model for SAM Using Multi-Heuristic Algorithm: Focused on Theater Ballistic Missile Defense, *IE Interfaces*, 2008, Vol. 21, No. 3, pp. 262-273.

[10] Yoo, B.C., Kim, J.H., Kwon, Y.S. and Choi, B.W., A Study on the Flight Trajectory Prediction Method of Ballistic Missiles, *Journal of KOSSE*, 2020, Vol. 16, No. 2, pp. 131-140.

[11] McCormick, G.P., Computability of Global Solutions to Factorable Nonconvex Programs: Part I — Convex Underestimating Problems, *Mathematical Programming*, 1976, Vol. 10, No. 1, pp. 147-175.

[A] Armstrong, M.J., The Effectiveness of Rocket Attacks and Defenses in Israel, *Journal of Global Security Studies*, 2018, Vol. 3, No. 2, pp. 113-132. https://doi.org/10.1093/jogss/ogx028
> ※ Operation Pillar of Defense(2012) 및 Protective Edge(2014) 데이터를 실증 분석하여 아이언 돔의 교전 대상 로켓 차단율을 추정. Protective Edge 기준 방어 지역 내 90% 차단율 추정치 제시. Oxford Academic 오픈 접근 가능.

[12] Manne, A.S., A Target-Assignment Problem, *Operations Research*, 1958, Vol. 6, No. 3, pp. 346-351. https://doi.org/10.1287/opre.6.3.346
> ※ WTA 문제를 최초로 정의한 논문. 비선형 정수계획 모형으로 WTA를 공식화하고, 무기-표적 할당의 최적화 틀을 제시. JSTOR 통해 오픈 접근 가능.

[13] Lloyd, S.P. and Witsenhausen, H.S., Weapons Allocation is NP-Complete, *Proceedings of the 1986 Summer Computer Simulation Conference*, 1986, pp. 1054-1058.
> ※ WTA 문제가 NP-complete임을 증명한 원천 논문. 본문 1장의 "NP-complete임을 증명" 인용 근거.

[14] Kline, A., Ahner, D. and Hill, R., The Weapon-Target Assignment Problem, *Computers & Operations Research*, 2019, Vol. 105, pp. 226-236. https://doi.org/10.1016/j.cor.2018.10.015
> ※ WTA 문제의 정식·비정식(SWTA/DWTA) 모형과 정확해·휴리스틱 알고리즘 전반을 체계적으로 정리한 종합 리뷰. "기존 해법 두 계열(휴리스틱·정확해) 모두 실시간성과 최적성을 동시 충족하지 못한다"는 1-④의 직접 근거. ResearchGate에서 저자 제공 preprint 오픈 접근 가능.

[15] Ahuja, R.K., Kumar, A., Jha, K.C. and Orlin, J.B., Exact and Heuristic Algorithms for the Weapon-Target Assignment Problem, *Operations Research*, 2007, Vol. 55, No. 6, pp. 1136-1146. https://doi.org/10.1287/opre.1070.0440
> ※ 정수계획 기반 하한(lower bound) 알고리즘과 VLSN 휴리스틱을 제시하여, 80개 무기×80개 표적 인스턴스에서 최적해 탐색이 가능하지만 수 시간이 소요됨을 보고. MIP 계열도 실시간 적용 불가임을 뒷받침하는 핵심 근거. INFORMS PubsOnline 오픈 접근 가능.

[16] Kline, A.G., Ahner, D.K. and Lunday, B.J., Real-time Heuristic Algorithms for the Static Weapon Target Assignment Problem, *Journal of Heuristics*, 2019, Vol. 25, No. 3, pp. 377-397. https://doi.org/10.1007/s10732-018-9401-1
> ※ 실시간 요건 충족을 위해 최적성을 포기한 휴리스틱 계열의 대표 연구. "실시간 가능 but 최적성 미보장"이라는 1-④ 첫 번째 계열의 근거. Springer에서 오픈 접근 가능.

[17] Lu, Y. and Chen, D.Z., A New Exact Algorithm for the Weapon-Target Assignment Problem, *Omega*, 2021, Vol. 98, Article 102138. https://doi.org/10.1016/j.omega.2019.102138
> ※ WTA를 이진 열(column) 정수선형계획으로 변환하고 열 열거(column enumeration)와 Branch-and-Bound로 80×80 인스턴스를 0.40초에 정확히 풀어, 기존 비선형 솔버(16.2시간)에 비해 대폭 개선. 단, DWTA의 동적 시간창 제약과 다층 방어 상호의존성이 없는 정적 SWTA 기준이므로 본 연구의 DWTA 실시간 요건(1초 이내)과 직접 비교 대상은 아님을 명시할 것.

[18] Andersen, A.C., Pavlikov, K. and Toffolo, T.A.M., Weapon-Target Assignment Problem: Exact and Approximate Solution Algorithms, *Annals of Operations Research*, 2022, Vol. 312, No. 2, pp. 581-606. https://doi.org/10.1007/s10479-022-04525-6
> ※ 비선형 목적함수를 볼록 하한 선형 근사로 변환하는 branch-and-adjust 알고리즘 제시. 1,500×1,000 인스턴스를 2시간 이내 2% 오차 이내로 풀어 대규모 SWTA에서 현 최고 수준의 정확해법. 선형화 접근이 본 연구와 방향은 같으나, 동적 시간창·K-factor가 없는 정적 문제 대상이라는 점에서 차별화 근거가 됨.
