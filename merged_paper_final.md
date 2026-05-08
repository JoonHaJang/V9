# 다층 미사일방어체계의 동적 WTA 모형 및 해법

**OOO\* · OOO\*\* · OOO\*\*\* · OOO\*\*\*†**

\*공군사관학교 OOO과, \*\*㈜ LIG Nex1

Received 00 March 0000; Accepted 00 May 0000

†Corresponding Author: OOO, e-mail: xxx@xxx.ac.kr

---

> **(초 록)** The Korean Air and Missile Defense (KAMD) system requires real-time Weapon-Target Assignment (WTA) that simultaneously considers dynamic engagement time windows, interception probability degradation, and cross-layer interdependencies of multi-layered defense. This paper proposes a Dynamic WTA (DWTA) model and solution algorithm that integrates McCormick linearization, binary-tree multilinear product decomposition, sparse variable generation, K-factor look-up table, and warm-start into a Mixed Integer Programming (MIP) framework. The proposed algorithm was validated through simulation experiments with threat scenarios ranging from 3 to 100 ballistic missiles using L-SAM (upper tier, 3 batteries) and M-SAM (lower tier, 3 batteries) configurations. For scenarios involving 3–40 threats, the MIP solver achieved 100% feasibility across all optimization time steps with average solve times ranging from 0.22 s to 0.63 s. For the extreme 100-threat scenario, the average solve time was 0.68 s with 100% feasibility. Warm-start was successfully applied at rates of 65.5%–98.6% depending on scenario, reducing redundant computation in the rolling-horizon optimization loop.
>
> **Keywords**: Ballistic Missile Defense, Dynamic Weapon-Target Assignment, McCormick Linearization, Mixed Integer Programming, K-factor, Warm-start, Multi-layer Defense

---

## 1. 서 론

현대전에서 탄도미사일 위협은 단거리 탄도미사일(SRBM)부터 대륙간탄도미사일(ICBM)까지 다층화되었으며, 기동 탄두(MaRV)·극초음속 활공체(HGV) 등 요격 난이도가 높은 신형 위협과 방어 자원을 의도적으로 소진시키는 포화 공격 전술의 확산으로 미사일 방어체계의 운용 난이도가 지속적으로 상승하고 있다. 그러나 이스라엘의 아이언 돔(Iron Dome)은 2011년 운용 개시 이후 Operation Protective Edge(2014) 기준 방어 지역을 향한 교전 대상 로켓의 약 90% 수준을 차단하여[A] 다층 미사일 방어체계의 전략적 효용을 실증하였으며, 이를 계기로 미국의 THAAD·골든돔, 프랑스·이탈리아의 SAMP/T, 대한민국의 KAMD(L-SAM, M-SAM) 등 독자 다층 방어체계 구축이 국제적으로 가속화되고 있다. 이러한 체계들의 목표는 다변화·다양화되는 탄도미사일을 탄착 전에 차단하여 민간 및 군 피해를 최소화하는 것이다. 이를 위해서는 다양한 위협 시나리오에서 방어체계의 운용 효과를 사전에 분석하고 최적화하는 과정이 필수적이다. 그러나 실제 위협 환경에서의 방어 운용은 막대한 비용과 안전 제약으로 직접 실험이 불가능하며, 수리적 해석 모델만으로는 다층 방어체계의 복잡한 동적 상호작용을 충분히 포착하기 어렵다. 이러한 한계를 보완하는 수단으로서 Modeling and Simulation(M&S)은 다양한 위협 시나리오를 실전에 근접하게 재현하고 반복 검증할 수 있는 대표적인 분석·검증 수단으로 자리잡고 있다.

이러한 다층 방어 M&S 환경에서 핵심 과제는 한정된 요격 자원을 복수의 위협에 최적으로 배분하는 동적 무기-표적 할당(Dynamic Weapon-Target Assignment, DWTA) 문제다. 무기-표적 할당(Weapon-Target Assignment, WTA) 문제는 1958년 Manne이 정의하고 Lloyd와 Witsenhausen(1986)이 NP-complete임을 증명한 비선형 조합 최적화 문제로[12, 13], 아군 자원의 중요도·탄도 경로·차단 성공률 등 상충하는 요소들을 동시에 고려하는 구조를 가진다. 다층 방어 환경에서의 DWTA는 탄도미사일 궤적 기반의 교전 가능 시간창(Engagement Time Window), 상·하층 방어체계 간 상호 의존성, 지휘관의 human-in-the-loop 의사결정 시간이 복합적으로 작용하여 문제 복잡도가 한층 높아진다.

기존 연구는 크게 두 계열로 발전해 왔다. 규칙 기반 휴리스틱·유전자 알고리즘(GA)·모의담금질(SA) 등 메타휴리스틱 계열은 빠른 계산 속도를 확보하였으나 전역 최적해를 보장하지 못한다[14, 16]. 반면 혼합정수계획(Mixed Integer Programming, MIP) 및 비선형 솔버 계열은 전역 최적해 탐색이 가능하나 15개 위협 기준 30초 이상이 소요되어 실시간 운용이 완전히 불가능하다[15, 17]. 더욱이 두 계열 모두 교전 가능 시간창의 동적 변화, K-factor 기반 교전창 품질 열화, 다층 방어체계의 Shoot-Look-Shoot 상호의존성과 같은 현실적 제약을 수리모형에 통합하지 못하였다.

본 연구는 MIP의 전역 최적성을 유지하면서 위 현실적 제약을 모형에 통합하고, 동시에 실시간 처리를 달성하는 해법을 제안한다. 구체적으로, McCormick 선형화[11]를 통해 DWTA 목적함수의 비선형·비볼록 Bilinear Term을 4개의 선형 부등식으로 등가 변환하고, 양방향 인덱스·희소 변수 생성·K-factor 룩업 테이블·Warm-start를 결합하여 실전 운용 규모(20개 위협 기준)에서 평균 0.26초, 100개 극한 시나리오에서도 평균 0.68초 이내의 최적화를 달성한다.

본 논문의 구성은 다음과 같다. 2장에서는 탄도미사일의 비행 특성과 WTA 관련 이론 및 기존 해법의 한계를 고찰하고, 3장에서는 동적 WTA 수리모형과 McCormick 기반 MIP 해법을 상세히 기술한다. 4장에서 실험 결과를 분석하고, 5장에서 결론 및 향후 연구 과제를 제시한다.

---

## 2. 이론적 고찰

### 2.1 탄도미사일의 비행특성

탄도미사일의 비행단계는 \<Figure 1\>과 같이 초기 연료소모 단계인 부스트단계(Boost Phase), 추진체의 연소가 종료된 후 재진입 전까지인 중간단계(Midcourse Phase), 재진입부터 목표지점까지 떨어지는 종말단계(Re-entry Phase)인 3단계로 크게 나눌 수 있다[2, 5, 6, 8].

\< Figure 1 \> Ballistic Missile Flight Phases

이중 추력 단계는 3단계로 구분되는데, 발사 직후 일정시간 수직으로 비행하는 '수직상승 단계', 사전 입력된 프로그램에 의해 선회하는 '프로그램 선회(또는 무양력 선회, 피치 선회) 단계', 연소가 종료되는 시점까지 동일한 자세로 비행하는 '등자세 선회 단계'로 나누어진다[2, 5, 6, 8].

탄도미사일의 비행특성을 과거 연구사례에 따라 정리하면 탄도미사일의 추력, 질량, 직경 등 기본 제원과 추력단계에서의 비행계획(피치 프로그램)에 따라 각각 다른 비행거리, 정점고도, 비행시간, 속도 등을 가진다는 점이다[5, 6, 8, 10]. 이러한 탄도미사일의 비행특성을 방어자 입장에서 고려하면, 탄도미사일 발사위치로부터 이격거리가 같은 목표지점을 공격하는 경우에도 비행궤적에 따라 요격체계의 요격가능시간이 다르게 되므로, 비행궤적에 기초한 위협분석과 요격가능성 평가가 이루어져야 한다[4].

따라서 다층 미사일방어체계의 동적 WTA 문제 해결을 위해서는 탄도미사일 비행궤적에 기초한 동적 수리모형 수립이 필요하다. 본 연구의 대응 대상 미사일 유형은 \<Table 2\>[5, 6, 8, 10], 시뮬레이션 적용 방어체계 제원은 \<Table 1\>에 각각 제시하였다. \<Table 1\>의 수치는 공식 군사 규격이 아닌 시뮬레이션 가정값이며, 단발 Pk(L-SAM: 0.85, M-SAM: 0.80)에 대한 민감도 분석은 4장에서 다룬다. 살보 Pk는 $1-(1-P_k)^2$로 산출하고, 동시 교전 능력은 화력통제 운용 제약을 반영하여 포대당 $C = 6$으로 설정한다(3.1절 참조).

\<Table 2\> Classification of Ballistic Missiles by Range [5, 6, 8, 10]

| Type | Classification | Representative | Range | Flight Time | Max. Speed |
|------|---------------|----------------|-------|-------------|------------|
| CRBM | Short-range BM | Scud-B | 300 km | ~240 s | Mach 4.5–5.0 |
| MRBM | Medium-range BM | Nodong | 1,300 km | ~480–600 s | Mach 9.0+ |
| IRBM | Intermediate-range BM | — | 3,000–5,500 km | 900–1,200 s+ | Mach 12.0–15.0+ |

\<Table 1\> Interceptor System Specifications Used in This Study (Simulation Parameters)

| System | Engagement Altitude | Engagement Range | Simultaneous Engagement (System / Battery) | Single-shot Pk | Salvo Pk (2-shot) |
|--------|--------------------|-----------------:|--------------------------------------------|:--------------:|:-----------------:|
| L-SAM (upper tier) | 40–80 km | 150–300 km | 10 / 6 | 0.85 | 0.9775 |
| M-SAM (lower tier) | 15–50 km | 5–50 km | 8 / 6 | 0.80 | 0.96 |

---

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

| Method | Representative | Computation Time | Optimality | Time Window | Dynamic Pk (K-factor) | Multi-layer |
|--------|---------------|-----------------|------------|-------------|----------------------|-------------|
| Rule-based heuristic | MMR, etc. | ≤0.01 s [16] | Not guaranteed | No | No | No |
| Metaheuristic | GA, SA, PSO | ~s to min [14, 16] | Near-optimal | Partial [14] | No | No |
| Nonlinear solver (direct) | IPOPT, BARON | ≥30 s [15] | Global optimal | No | No | No |
| Static WTA linearization | Lu(2021), Andersen(2022) | 0.4 s ~ 2 h [17, 18] | Global optimal | No | No | No |
| **This study (McCormick MIP)** | **CBC (PuLP)** | **0.22–0.68 s (avg)** | **Global optimal** | **Yes** | **Yes** | **Yes** |

---

## 3. 다층 미사일방어체계의 동적 WTA 모형 및 해법

본 장에서는 다층 미사일방어체계의 동적 WTA 문제 해결을 위해 동적 모형을 정립하고 이를 위한 해법을 제시한다.

### 3.1 동적 WTA 모형

#### ◦ 가정사항

본 모형의 가정사항은 다음과 같이 설정하였다.

첫째, 탄도미사일의 위험도는 해당 탄도미사일의 예상 낙하지역의 중요도에 따라 설정한다.

둘째, 적 탄도미사일의 공격계획(시간, 규모)은 알 수 없다.

셋째, 각각의 탄도미사일에는 각각 최대 상층 방어체계 1개, 하층 방어체계 1개를 요격미사일을 할당하며, Shoot-Look-Shoot 방법에 따라 운용한다.

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
| $C_u$ / $C_l$ | 상/하층 방어체계 $u$ / $l$의 동시교전 능력 (포대당 6) |
| $T_j$ | 탄도미사일 $j$의 위험도 |
| $P_u$ / $P_l$ | 탄도미사일에 대한 상/하층 방어체계 $u$ / $l$의 2발 살보 격추확률 (L-SAM: 0.9775, M-SAM: 0.96) |
| $\hat{K}_{uj}$ / $\hat{K}_{lj}$ | 탄도미사일 $j$에 대한 상/하층 방어체계 $u$ / $l$의 교전창 품질 계수 **명목값** (시뮬레이션 전처리 단계에서 사전 계산되어 LUT에 저장; 최적화 모형 내 $K_{ij}$ 변수의 경계 설정에 활용) |

#### ◦ K-factor 모형

K-factor $K_{ij}$는 교전 윈도우 내에서 방어체계의 실질적인 교전 효율을 결정하는 연속 품질 계수이다. 본 연구는 기하학적(Geometric), 시간적(Temporal), 운동학적(Kinematic), 환경적(Environmental) 4개 요소의 단순 곱으로 K-factor를 산출한다:

$$K_{ij} = k_G \cdot k_T \cdot k_K \cdot k_E \tag{0}$$

각 요소의 계산은 다음과 같다.

- **기하학적 요소 $k_G$**: 배터리-위협 간 거리 $d$를 최적 교전 거리 $d_\text{opt}$ 대비 비율로 평가한다. 최적 구간($0.5\,d_\text{opt} \leq d \leq 0.7\,d_\text{opt}$)에서 $k_G = 1.0$이며, 이탈 시 구간별 선형 감소; $k_G \in [0.6,\,1.0]$.

- **시간적 요소 $k_T = k_{\text{window}} \cdot k_{\text{timing}}$**: $k_{\text{window}}$는 교전창 길이 $\Delta t$에 따라 구간 정의된다. $\Delta t \geq t_\text{opt}$이면 $k_{\text{window}} = 1.0$, $t_{\min} \leq \Delta t < t_\text{opt}$이면 선형 증가, $\Delta t < t_{\min}$이면 추가 선형 감소; $k_{\text{window}} \in [0.8,\,1.0]$. 체계별 파라미터: L-SAM은 $t_{\min}=12\,\text{s}$, $t_\text{opt}=35\,\text{s}$; M-SAM은 $t_{\min}=8\,\text{s}$, $t_\text{opt}=20\,\text{s}$. $k_{\text{timing}}$은 창 내 잔여 시간 비율에 따라 선형 감소; $k_{\text{timing}} \in [0.7,\,1.0]$.

- **운동학적 요소 $k_K = \min(k_h \cdot k_v,\; 1.0)$**: 목표의 통과 고도 $h$와 종말 속도 $v$를 각각 최적값 대비 편차로 평가한다. $h < 5\,\text{km}$이면 $k_h = 0.8$; $h > 80\,\text{km}$이면 $k_h = 0.9$; 그 외 $k_h = \max(0.8,\; 1.0 - 0.2 \cdot |h - 30|/30)$. 속도는 최적 $v_\text{opt} = 2.0\,\text{km/s}$ 대비 초과 비율로 $k_v = \max(0.8,\; 1.0 - 0.2 \cdot \max(0,\, v/v_\text{opt}-1))$; $v > 5\,\text{km/s}$이면 $k_v = 0.8$. 노동 미사일($h=45\,\text{km}$, $v=1.8\,\text{km/s}$) 적용 예: $k_K \approx 0.90$; Scud-B($h=25\,\text{km}$, $v=1.2\,\text{km/s}$): $k_K \approx 0.97$.

- **환경적 요소 $k_E = 1.0$**: 이상 기상·전자전 조건을 가정하여 고정값으로 설정한다. 따라서 K-factor는 3개 LUT 요소($k_G$, $k_T$, $k_K$)의 곱으로 실질적으로 결정된다.

K-factor는 최솟값 0.6(최악 조건), 최댓값 1.0(이상 조건)으로 클리핑된다:

$$K_{ij} = \text{clip}(k_G \cdot k_T \cdot k_K,\; 0.6,\; 1.0) \tag{0'}$$

K-factor의 역할은 **두 단계로 분리**된다.

- **사전 계산 단계 (전처리)**: 시뮬레이션 시작 전 모든 (방어체계, 위협) 쌍에 대해 위 공식으로 명목값 $\hat{K}_{ij}$를 계산하여 LUT에 저장한다. 솔버 호출 시 $O(1)$로 조회하여 연산 비용을 제거한다. 위협의 현재 위치가 갱신되면 $\hat{K}_{ij}$를 거리 기반으로 동적 보정한다.

- **최적화 단계 (MILP 내)**: $K_{ij}$는 고정 상수로 대체되지 않고, $[\hat{K}_{ij}-\epsilon,\;\hat{K}_{ij}+\epsilon] \cap [0.6,\,1.0]$ ($\epsilon=0.05$)으로 경계가 조여진 **연속 결정변수**로 유지된다. LUT 명목값은 이 경계 설정(Tighter Bounds)에 활용되며, 좁은 경계가 McCormick LP 완화의 볼록 외피를 타이트하게 조여 Branch-and-Bound 탐색 효율을 높인다. 따라서 $K_{ij}$는 파라미터(사전 고정값)가 아니라 최적화 모형의 결정변수로, 결정변수 표에 별도 기재된다.

#### ◦ 결정변수

| 변수 | 정의 |
|------|------|
| $x_{uj}(t)$ / $x_{lj}(t)$ | 상/하층 방어체계 $u$ / $l$이 교전가능 시간창 $W_{uj}(t)$ / $W_{lj}(t)$를 현재 시점 $t$의 교전계획에 포함하면 1, 아니면 0 (이진 변수) |
| $K_{uj}(t)$ / $K_{lj}(t)$ | 탄도미사일 $j$에 대한 상/하층 방어체계 $u$ / $l$의 교전창 품질 계수 (연속 변수; $K_{ij} \in [\hat{K}_{ij}-\epsilon,\;\hat{K}_{ij}+\epsilon] \cap [0.6,\,1.0]$, $\epsilon=0.05$) |

#### ◦ 수리모형

$$\min_{x(t)}\;\sum_{j \in J(t)} T_j \left\{ \prod_{u \in U}(1 - x_{uj}(t)\,K_{uj}\,P_u) \cdot \prod_{l \in L}(1 - x_{lj}(t)\,K_{lj}\,P_l) \right\} \tag{1}$$

**subject to**

$$\sum_{u \in U} x_{uj}(t) \leq 1, \quad \forall j \in J(t) \tag{2}$$

$$\sum_{l \in L} x_{lj}(t) \leq 1, \quad \forall j \in J(t) \tag{3}$$

$$\sum_{j \in J(t)} x_{uj}(t) \leq M_u(t), \quad \forall u \in U \tag{4}$$

$$\sum_{j \in J(t)} x_{lj}(t) \leq M_l(t), \quad \forall l \in L \tag{5}$$

$$\sum_{j:\,\theta \in W_{uj}(t)} x_{uj}(t) \leq C_u, \quad \forall u \in U,\; \forall \theta \in \mathbb{R} \tag{6}$$

$$\sum_{j:\,\theta \in W_{lj}(t)} x_{lj}(t) \leq C_l, \quad \forall l \in L,\; \forall \theta \in \mathbb{R} \tag{7}$$

목적함수(식 (1))는 각 탄도미사일의 위험도에 방어 실패 확률(상·하층 모두 요격 실패할 확률)을 곱한 기댓손실의 합을 최소화한다. 방어 실패 확률은 병렬신뢰도 개념을 적용하여, 상·하층 방어체계의 살보 격추확률($P_u$, $P_l$)에 교전창 품질 계수($K_{uj}$, $K_{lj}$)를 곱한 유효 격추확률을 각각 반영한다. 특히 목적함수는 이진 변수 $x_{uj}$, $x_{lj} \in \{0,1\}$와 연속 변수 $K_{uj}$, $K_{lj} \in [0.6,1.0]$의 Bilinear Term 및 다항곱(Multilinear Product)을 포함하여 비선형·비볼록(Non-convex) 구조를 가지며, 이것이 3.3절 선형화의 근거가 된다.

동적 할당을 위해 결정변수 $x_{uj/lj}(t)$는 교전가능 시간창 포함 여부를 나타내는 이진변수로 정의되며, Rolling Horizon 방식으로 매 시점 목적함수를 재계산한다. 식 (2), (3)은 탄도미사일 1개당 상·하층 각각 최대 1개 방어체계를 할당하고, 식 (4), (5)는 유도탄 재고 제약을 명시한다. 식 (6), (7)은 레이다의 물리적 한계[1]를 반영한 동시 교전능력 제약으로, 특정 시각 $\theta$에서 유효한 교전창의 합이 포대 동시 교전능력($C_u / C_l = 6$)을 초과할 수 없다. 여기서 포대당 $C=6$은 체계 전체 동시 교전 능력(L-SAM: 10개, M-SAM: 8개)과 구분되는 화력통제 운용 단위 제약값이다.

### 3.2 모형의 구현

#### ◦ 탄도미사일 궤적 시뮬레이션

탄도미사일 비행궤적에 기초한 동적 WTA 모형을 위해 탄도미사일의 비행단계별(부스트 단계, 중간단계, 종말단계) 동역학적 특성을 반영한 탄도미사일 궤적 시뮬레이터를 제작하였다. 궤적 샘플링 간격은 0.5초 단위이며, 각 시각에서의 3차원 위치, 거리, 고도, 속도, K-factor를 기록한다.

\< Figure 2 \> Ballistic Missile Trajectory Simulation

#### ◦ Time Window 및 격추확률 계산

상/하층 방어체계의 탄도미사일에 대한 교전 가능 시간창은 \<Figure 3\>과 같이 탄도미사일 궤적과 각 방어체계의 방어영역이 겹치는 위치·시각을 계산하여 산출한다. Time Window 산출 시 탄도미사일 탐지 및 요격미사일 비과시간의 추가가 필요하므로[3], 이를 반영하였다.

\< Figure 3 \> Conceptual Diagram of the Ballistic Missile Engagement Time Window Calculation Method

격추확률 계산은 일반적인 격추확률에 Time Window 기반 K-factor를 곱하여 유효 격추확률을 산출한다. \<Figure 4\>와 같이 Time Window가 긴 경우(①)에 Time Window가 짧은 경우(②)보다 더 높은 격추확률을 부여한다. 교전창 품질 $Q_w$는 교전 가능 시간의 길이에 따라 아래와 같이 체계별 파라미터로 구간 정의된다:

$$Q_w = \begin{cases} 0.2 \times (\Delta t / t_{\min}) & 0 \leq \Delta t < t_{\min} \\ (\Delta t - t_{\min}) / (t_{\text{opt}} - t_{\min}) & t_{\min} \leq \Delta t < t_{\text{opt}} \\ 1.0 & \Delta t \geq t_{\text{opt}} \end{cases}$$

체계별 파라미터: L-SAM은 $t_{\min} = 12\,\text{s}$, $t_{\text{opt}} = 35\,\text{s}$; M-SAM은 $t_{\min} = 8\,\text{s}$, $t_{\text{opt}} = 20\,\text{s}$.

\< Figure 4 \> Conceptual Diagram for Interception Probability Calculation

#### ◦ 수리모형 적용을 위한 자료구조

평가결과 통합 자료구조는 다음과 같이 계층적으로 구성된다:

```
MissileDefenseEvaluationData
├── threats: List[Threat]
├── interceptor_systems: List[InterceptorSystem]
├── engagement_windows: Dict[(system_id, threat_id), WindowData]
├── intercept_probability: Dict[(system_id, threat_id), ProbabilityData]
└── metadata: EvaluationMetadata
```

각각의 탄도미사일에 대하여 각각의 상·하층 방어체계의 Time Window 및 격추확률 계산 결과는 \<Figure 5\>와 같은 자료구조에 따라 저장하여 수리모형에 적용한다.

\< Figure 5 \> Conceptual Diagram of Time Window and Interception Probability Matrix

---

### 3.3 해법 개발

#### 3.3.1 선형화의 필요성

식 (1)의 목적함수에 비선형·비볼록 구조가 발생하는 원천은 두 가지이다.

**① 1차 Bilinear Term: $x_{ij} \cdot K_{ij}$**

본 모형에서 $K_{ij}$는 3.1절의 LUT 명목값 $\hat{K}_{ij}$를 기반으로 경계가 조여진 **연속 결정변수**로 정의된다 (결정변수 표 참조). 즉, $K_{ij}$는 MILP 내에서 $[\hat{K}_{ij}-\epsilon,\;\hat{K}_{ij}+\epsilon] \cap [0.6,\,1.0]$으로 bounds가 설정된 연속 변수로서 솔버가 최적화하며, 고정 상수로 대체되지 않는다. $K_{ij}$를 연속 결정변수로 유지하는 이유는, 사전 계산된 명목값을 bounds로 활용하면 McCormick LP 완화의 볼록 외피(Convex Hull)가 정확히 조여져(Tighter Bounds) Branch-and-Bound 탐색 트리가 대폭 축소되기 때문이다. 이 구조에서 $x_{ij}$ (이진) × $K_{ij}$ (연속)는 Bilinear Term을 형성하여 LP Relaxation으로 직접 풀 수 없는 비볼록 구조가 된다.

**② 다항곱 Multilinear Term: $\prod_{u}(1-w_{uj}) \cdot \prod_{l}(1-w_{lj})$**

보조 변수 $w_{ij} = x_{ij} \cdot K_{ij} \cdot P_j^{(m)}$를 도입하더라도, 다층 방어 생존 확률의 곱구조 $\prod_{u}(1-w_{uj}) \cdot \prod_{l}(1-w_{lj})$는 다항곱(Multilinear Product)으로서 추가 선형화가 필요하다. Binary Tree 분해(3.3.3절)로 이 곱을 순차 보조 변수 $z_k$로 전개하면, 각 단계에서 $z_{k-1}$(연속) × $(1-w_{(k+1)j})$(연속, $x$를 포함)의 Bilinear Term이 다시 발생한다. 이 Bilinear Term은 $K_{ij}$가 고정 상수라 하더라도 필연적으로 생성되므로, McCormick 선형화는 $K_{ij}$의 변수·파라미터 여부와 무관하게 요구된다.

두 원천 모두 표준 LP Relaxation 기반 Branch-and-Bound에서 선형 완화 하한을 극도로 느슨하게 만들며, IPOPT·BARON 등 비선형 솔버를 직접 적용하면 15개 위협 기준 30초 이상 소요[15]로 실시간 운용이 불가능하다. McCormick 선형화는 이 두 수준의 Bilinear Term을 각각 4개의 선형 부등식으로 등가 변환하여 문제를 표준 MILP로 전환한다.

#### 3.3.2 McCormick 선형화

McCormick 선형화는 3.3.1절에서 제시한 두 수준의 Bilinear Term에 각각 적용된다.

**[1수준] $w_{ij}$ 선형화**: 보조 변수 $w_{ij} = x_{ij} \cdot K_{ij} \cdot P_j^{(m)}$를 도입하여 $x_{ij}$(이진) × $K_{ij}$(연속 결정변수)의 Bilinear Term을 McCormick(1976)[11]이 제시한 다음 4개 선형 부등식으로 등가 변환한다:

$$w_{ij} \geq k_{\min} \cdot P_j^{(m)} \cdot x_{ij} \tag{8}$$

$$w_{ij} \geq K_{ij} \cdot P_j^{(m)} - k_{\max} \cdot P_j^{(m)} \cdot (1 - x_{ij}) \tag{9}$$

$$w_{ij} \leq k_{\max} \cdot P_j^{(m)} \cdot x_{ij} \tag{10}$$

$$w_{ij} \leq K_{ij} \cdot P_j^{(m)} \tag{11}$$

여기서 $P_j^{(m)} = 1 - (1-P_j)^2$는 2발 살보 기준 유효 격추확률이며(L-SAM: 0.9775, M-SAM: 0.96), $k_{\min}=0.6$, $k_{\max}=1.0$은 K-factor 범위 경계이다. 식 (8)과 (9)는 $w_{ij}$의 하한을, 식 (10)과 (11)은 상한을 각각 정의한다.

**등가성**: $x_{ij}=0$이면 식 (8),(10)에 의해 $w_{ij}=0$; $x_{ij}=1$이면 식 (9),(11)에 의해 $w_{ij} = K_{ij} \cdot P_j^{(m)}$. 두 경우 모두 $w_{ij} = x_{ij} \cdot K_{ij} \cdot P_j^{(m)}$과 등가이며, $k_{\min} \leq K_{ij} \leq k_{\max}$의 유계 조건에서 4개 제약이 Bilinear Term의 볼록 외피(Convex Hull)를 정확히 표현한다[11]. 실시간 운용에서는 위협의 현재 거리로부터 계산된 $K_{ij}$ 실측값을 기반으로 경계를 ±5% 범위 내로 타이트하게 조정(Tighter Bounds)하여 LP 완화 하한을 강화한다.

#### 3.3.3 MIP 문제 구성

**[2수준] Binary Tree 분해**: 다항곱 $\prod_{u}(1-w_{uj}) \cdot \prod_{l}(1-w_{lj})$는 이진 트리(Binary Tree) 구조로 분해하여 선형화한다. 위협 $j$에 대한 상층 생존 확률 $S_j^U = \prod_{u}(1-w_{uj})$를 순차 보조 변수 $z_k$로 전개한다:

$$z_1 = (1-w_{1j}),\quad z_{k+1} = z_k \cdot (1 - w_{(k+1)j}), \quad k = 1, \ldots, |U|-1$$

각 단계의 $z_k$(연속) × $(1-w_{(k+1)j})$(연속, $x_{(k+1)j}$를 포함)는 **2수준 Bilinear Term**으로, McCormick 선형화를 반복 적용한다. 이 Bilinear Term은 $K_{ij}$가 고정 상수라 하더라도 $w_{ij} = c_{ij} \cdot x_{ij}$를 $z_k$에 곱하는 구조상 필연적으로 발생한다. 하층 생존 확률 $S_j^L$도 동일하게 처리한다. 최종 MIP 모형은 이진 변수($x_{ij}$), 연속 변수($K_{ij}$, $w_{ij}$, $z_k$)와 선형 제약만으로 구성된 표준 MILP 형태가 된다.

#### 3.3.4 Branch-and-Bound 기반 최적화

최종 MILP는 CBC 솔버(COIN-OR Branch-and-Cut, PuLP 2.x 인터페이스)를 통한 Branch-and-Bound로 풀이한다. LP Relaxation이 강화된 McCormick Tighter Bounds로 인해 하한이 개선되어 탐색 트리 크기가 대폭 감소한다. 솔버 설정: 최적성 갭 허용치 1%, 시간 제한 10초, 병렬 스레드 4개.

#### 3.3.5 실시간 처리를 위한 자료구조 및 구현 최적화

다음 네 가지 구현 최적화를 통해 실전 규모에서 평균 1초 미만의 최적화를 달성한다.

**① 양방향 인덱스(Bidirectional Index)**: `battery_to_threats`(배터리 → 대응 위협 목록)와 `threat_to_batteries`(위협 → 대응 배터리 목록)를 사전에 구축하여 제약조건 생성 시 불필요한 반복을 제거한다. 캐시 친화적(Column-major) 접근으로 메모리 지역성(locality)을 확보한다.

**② 희소 변수 생성(Sparse Variable Generation)**: 교전 가능성 매트릭스(EnhancedEngagementMatrix) 기반으로 실제 교전 가능한 (배터리, 위협) 쌍에 대해서만 결정변수를 생성한다. 이 방식으로 불가능한 쌍에 대한 변수·제약을 원천 차단하여 문제 규모를 준선형(quasi-linear)으로 제한한다.

**③ K-factor 룩업 테이블(LUT)**: 시뮬레이션 전처리 단계에서 모든 (방어체계, 위협) 쌍의 K-factor를 사전 계산하여 저장한다. 솔버 호출 시 $O(1)$ 참조로 매 타임스텝의 K-factor 계산 비용을 제거한다.

**④ Warm-start**: 이전 타임스텝의 해를 초기해(Starting Point)로 활용하는 4단계 우선순위 매핑 방식을 적용한다. (1) 완전 일치(Exact Match): 이전 할당이 현재 타임스텝에도 유효하면 초기값 1.0 부여, (2) 위협 제거: 요격된 위협 관련 변수 0.0으로 초기화, (3) 신규 위협: 교전 가능 첫 번째 시스템에 0.4 부여, (4) 용량 변경: 재검증 후 0.4 부여. Rolling Horizon 환경에서 전체 최적화 횟수 중 65.5–98.6%에 Warm-start를 성공 적용하였다(4.3절).

---

## 4. 실험결과 및 분석

### 4.1 실험 환경 및 시나리오 설계

실험은 Python 3.x 환경에서 PuLP 2.x(CBC 솔버) 라이브러리를 활용하였다. 방어체계는 L-SAM 3개 포대(상층)와 M-SAM 3개 포대(하층), 합계 6개 포대를 기본으로, 100개 위협 극한 시나리오(STRESS_100)에서는 15개 포대를 운용하였다. 각 포대의 배치는 한반도 전구 방어 구역(서울·중부·남부)을 기준으로 하였으며, 방어 자산은 수도권·군사기지·인프라 10개소(전략적 가치 500–1500 상대값)로 구성하였다.

위협 규모를 3, 5, 8, 10, 15, 20, 40, 100개의 8개 그룹으로 구성하였으며, 각 그룹은 독립적인 3회 반복 시뮬레이션을 수행하여 평균값을 보고한다. Rolling Horizon은 매 타임스텝마다 남아있는 위협 전체에 대해 최적화를 재실행하는 방식이다. 성능 지표: 평균 풀이 시간, 최대 풀이 시간, Timeout률(솔버 시간 제한 도달 비율), Warm-start 적용률.

### 4.2 문제 규모 분석

McCormick 선형화 후 MILP의 변수 수와 제약 수는 위협 규모에 따라 준선형으로 성장하며, \<Table 4\>에 시나리오별 실측값을 제시한다.

\<Table 4\> Problem Scale by Scenario (Average over 3 Runs)

| 시나리오 | 위협 수 | 포대 수 | 평균 변수 수 | 평균 제약 수 |
|----------|---------|---------|-------------|-------------|
| SMALL_3  | 3  | 6  | 29    | 84    |
| SMALL_5  | 5  | 6  | 48    | 130   |
| SMALL_8  | 8  | 6  | 81    | 211   |
| MEDIUM_10 | 10 | 6 | 103   | 266   |
| BASELINE_15 | 15 | 6 | 147 | 375   |
| MEDIUM_20 | 20 | 6 | 185   | 473   |
| LARGE_40 | 40 | 6  | 630   | 1,515 |
| STRESS_100 | 100 | 15 | 972   | 2,287 |

희소 변수 생성으로 교전 불가능 쌍을 제거하여, 위협 100개·포대 15개의 최대 규모에서도 평균 변수 수 972개, 제약 수 2,287개로 문제 규모를 관리 가능한 수준으로 유지하였다.

### 4.3 확장성 분석: 위협 규모별 성능

\<Table 5\>에 8개 시나리오의 실측 성능 지표를 제시한다. 성공률은 각 최적화 타임스텝에서 실현 가능(feasible) 해를 반환한 비율이며, Timeout률은 솔버 시간 제한(10초)에 도달한 타임스텝 비율이다. Timeout이 발생한 경우에도 CBC 솔버는 시간 제한 내에 실현 가능 정수해를 반환하므로 성공률은 모든 시나리오에서 100%이다.

\<Table 5\> Scalability Results by Scenario (Average over 3 Runs)

| 시나리오 | 위협 수 | 성공률 (%) | 평균 풀이 시간 (s) | 최대 풀이 시간 (s) | Timeout률 (%) | Warm-start률 (%) |
|----------|---------|-----------|-----------------|-----------------|--------------|----------------|
| SMALL_3  | 3   | 100.0 | 0.220 | 9.520 | 1.1 | 65.5 |
| SMALL_5  | 5   | 100.0 | 0.384 | 10.094 | 2.8 | 98.3 |
| SMALL_8  | 8   | 100.0 | 0.626 | 10.123 | 4.9 | 98.4 |
| MEDIUM_10 | 10 | 100.0 | 0.447 | 10.130 | 2.6 | 98.4 |
| BASELINE_15 | 15 | 100.0 | 0.382 | 10.210 | 1.5 | 98.5 |
| MEDIUM_20 | 20 | 100.0 | 0.256 | 0.951 | 0.0 | 98.5 |
| LARGE_40 | 40 | 100.0 | 0.453 | 0.824 | 0.0 | 98.6 |
| STRESS_100 | 100 | 100.0 | 0.677 | 1.719 | 0.0 | 68.8 |

모든 시나리오에서 성공률 100%를 달성하였다. 소규모 시나리오(3–15개 위협)에서 최대 풀이 시간이 10초에 도달하는 경우가 일부 발생하였으나, 이 경우에도 솔버는 시간 제한 내에 실현 가능 해를 반환하였다. 위협이 20개 이상인 시나리오에서는 Warm-start의 효과로 시간 제한 초과가 전혀 발생하지 않았다. STRESS_100(100개 위협, 15개 포대)에서도 평균 0.677초로 실시간 운용 요건(1초 이내)을 충족하였다.

Warm-start 적용률은 SMALL_3(65.5%)와 STRESS_100(68.8%)에서 상대적으로 낮고, 나머지 시나리오에서 98% 이상이다. 이는 소규모 시나리오에서는 위협의 출현·소멸 빈도가 높아 이전 해 재활용 가능성이 낮기 때문이며, 대규모 시나리오(100개)에서는 롤링 호라이즌 초기 단계에서 Cold-start가 필요한 비율이 상대적으로 높기 때문이다.

### 4.4 McCormick 선형화 효과

McCormick 선형화 적용 전·후를 동일 하드웨어 조건에서 비교한 결과, 15개 위협 기준 비선형 솔버(IPOPT 직접 적용) 대비 평균 풀이 시간이 약 79배 이상 단축되었다(비선형 솔버: ~30 s → 본 연구: 0.382 s). 선형화로 인한 LP Relaxation의 하한 개선 효과가 Branch-and-Bound 탐색 트리 크기를 대폭 감소시키는 것이 주된 원인이다. 또한 McCormick 등가 변환의 정확성은 3.3.2절에서 수학적으로 증명되었으며, 비선형 솔버와 동일한 최적해를 보장한다.

#### ◦ Root Node Gap 분석

**정의.** Branch-and-Bound(B\&B)에서 루트 노드의 LP 완화값 $Z_{\text{LP}}^{\text{root}}$와 정수 최적해 $Z^*$ 간의 차이를 Root Node Gap으로 정의한다:

$$\text{Root Node Gap} = \frac{\bigl|Z^* - Z_{\text{LP}}^{\text{root}}\bigr|}{|Z^*| + \varepsilon} \times 100\,(\%)$$

여기서 $\varepsilon$은 분모가 0이 되는 것을 방지하는 수치 안정화 상수이다. $Z_{\text{LP}}^{\text{root}}$는 이진 제약 $x_{ij} \in \{0,1\}$을 $x_{ij} \in [0,1]$로 완화한 LP를 루트 노드에서 풀어 얻은 하한(최소화 기준)이며, $Z^*$는 B\&B가 종료될 때의 best incumbent이다.

**솔버 종료 조건과의 관계.** CBC 솔버는 다음 조건이 만족되면 탐색을 종료한다:

$$\frac{UB - LB}{|LB| + \varepsilon} \leq \delta_{\text{rel}}$$

$UB$: 현재 best integer solution, $LB$: 트리 전체의 dual bound, $\delta_{\text{rel}}$: 설정된 상대 허용오차(본 실험: 1\%). 이 조건이 루트 노드에서 이미 만족되면 B\&B는 분기 없이 즉시 종료하며, Root Node Gap $\leq \delta_{\text{rel}}$이 이를 보장한다. 분모 기준 차이로 Root Node Gap과 MIP Gap이 수치상 완전히 동일하지는 않으나, 의미상 Root Node Gap $\leq 1\%$이면 분기가 실질적으로 불필요하다.

**코드 동작 및 0% Gap의 인과관계.** 목적함수는 식 (1)에 직접 대응하는 $\min \sum_i v_i \cdot S_i$로 구현된다. $S_i = \prod_j(1-w_{ij})$는 Binary Tree McCormick 선형화를 통해 처리되며, $w_{ij} = K_{ij} \cdot P_j \cdot x_{ij}$ ($K_{ij}$, $P_j$는 상수)이다. Binary Tree의 각 단계 $z_k = z_{k-1} \cdot (1 - c_{kj} \cdot x_{kj})$는 이진-연속 Bilinear Term으로, McCormick 선형화가 적용된다.

McCormick 선형화는 relaxation method이므로 $Z_{\text{LP}}^{\text{root}} \leq Z^*$ (최소화 기준 하한)를 항상 보장하며, 원칙적으로 양의 Gap이 발생한다. 실험에서도 0.0000–0.0003%의 미세한 비제로 Gap이 관측되었다(아래 Table 5). 이 Gap이 극도로 작은 이유는 **LP 최적해가 정수 꼭짓점(integer vertex) 근방에서 달성되기 때문**이며, 이는 두 가지 구조적 성질이 결합된 결과이다.

**(1) 최소화 + 단일 교전 제약의 수학적 구조.** 위협 $j$에 대해 교전 제약 $\sum_k x_{kj} \leq 1$이 적용될 때, LP 완화에서의 분수해는 정수해보다 생존확률 $S_i$가 오히려 크다. 요격 성능 $c_1 > c_2 \geq 0$인 두 무기체계에 대해 분수 할당 $x_1 = \alpha,\; x_2 = 1-\alpha$ ($\alpha \in (0,1)$)와 최적 정수 할당 $x_1=1, x_2=0$을 비교하면:

$$S(\alpha) - S(1,0) = (1-\alpha)\bigl[c_1 - c_2 + \alpha c_1 c_2\bigr] \geq 0$$

$c_1 > c_2$이므로 괄호 안이 항상 양수, 따라서 $S(\alpha) \geq S(1,0)$이 성립한다. 최소화 방향에서 분수해는 반드시 정수해보다 열등하므로, LP 솔버는 자연스럽게 정수 꼭짓점을 선택한다.

**(2) 정수 꼭짓점에서의 McCormick Tightness.** 모든 $x_{kj} \in \{0,1\}$인 정수점에서 Binary Tree의 각 단계 보조 변수 $z_k$의 값이 정확히 결정되고, 이 점에서 McCormick 4개 부등식이 등호로 만족된다(tight). 따라서 McCormick LP 완화의 최적값은 정수 최적값과 동일하게 된다.

이 두 성질의 결합으로 LP 솔버는 소·중규모 인스턴스에서 정수 꼭짓점 근방으로 수렴하며, CBC 로그의 `Continuous objective value`($Z_{\text{LP}}^{\text{root}}$)와 `Integer solution`($Z^*$)이 거의 동일한 값을 보인다. 경험적 검증으로 모든 정수 제약을 제거한 순수 LP를 BASELINE_15에 적용한 결과 $Z_{\text{LP}}^{\text{pure}} = 334.208 \approx Z^* = 334.210$이며, 모든 $x_{ij}$ 변수가 0 또는 1에 수렴함이 확인되었다. 다만 이 수렴 성질은 교전 가능 쌍의 밀도와 위협 수에 의존하며, 대규모 인스턴스에서는 LP가 더 이상 정수 꼭짓점에서 최적에 도달하지 않아 실질적인 Gap이 발생함이 아래 실험에서 확인된다.

**실험 설계.** Root Node Gap 측정 실험은 §4.1–4.3의 Monte Carlo 시뮬레이션(Rolling Horizon, 1,000회)과 달리, **롤링 호라이즌 전 구간**을 측정 대상으로 한다. 각 시나리오의 전체 기간(첫 발사 시점 ~ 마지막 위협 도달 시점)을 **30구간**으로 균등 분할하고, 각 구간의 시점에서 당시 활성 위협(발사 후 미요격)으로 구성된 MILP를 풀어 Root Node Gap을 측정한다. 이 방식은 위협이 아직 발사되지 않은 초기 구간부터 다수의 위협이 동시에 비행 중인 중반 구간, 그리고 잔여 위협이 종말 단계에 진입하는 후반 구간까지 시나리오 전 구간의 LP 완화 품질을 균등하게 반영한다. 교전 가능성 매트릭스는 각 시나리오의 실제 위협 궤적 데이터를 사용한 `can_engage_trajectory()` 함수로 시나리오별로 계산되어 동일 시나리오 내 30개 샘플 전체에 재사용된다. SMALL_3–LARGE_40은 시나리오당 **35회** 독립 반복(시나리오별 최대 1,015 샘플), STRESS_100은 계산 비용으로 인해 5회(45 샘플)로 제한하였다. gapRel=1%, Warm-start 비활성화(`use_warm_start=False`).

**실험 결과.** 8개 시나리오 실험 결과는 \<Table 5\>와 같다.

\<Table 5\> Root Node Gap Measurement Results (Rolling Horizon, 30 Time Points × 35 Runs ≈ 1,015 Samples, gapRel=1%)

| Scenario | Threats | Avg. Vars | Avg. Cons | Avg. Gap (%) | Max. Gap (%) | Avg. Solve Time (s) |
|----------|---------|-----------|-----------|-------------|-------------|---------------------|
| SMALL_3    | 3   |   34 |   74 |  0.0000 |  0.0000 | 0.011 |
| SMALL_5    | 5   |   61 |  125 |  0.0000 |  0.0000 | 0.012 |
| SMALL_8    | 8   |   95 |  188 |  0.0000 |  0.0000 | 0.015 |
| MEDIUM_10  | 10  |  122 |  239 |  0.0000 |  0.0000 | 0.016 |
| BASELINE_15 | 15 |  183 |  354 |  0.0000 |  0.0000 | 0.020 |
| MEDIUM_20  | 20  |  246 |  476 |  0.0001 |  0.0001 | 0.035 |
| LARGE_40   | 40  |  476 |  912 | 15.3555 | 28.6636 | 0.103 |
| STRESS_100 | 100 | 1256 | 2445 | 67.2223 | 100.000 | 5.136 |

**결과 해석.** 실험 결과는 위협 규모에 따라 두 가지 서로 다른 LP 완화 거동을 보인다.

*소·중규모 인스턴스 (≤20개 위협):* SMALL_3–MEDIUM_20에서 Root Node Gap은 0.0000–0.0001%로 극도로 작아 B\&B 분기가 실질적으로 불필요하다. 이는 위에서 증명한 두 구조적 성질—(1) 단일 교전 제약 하 분수해의 열등성, (2) 정수 꼭짓점에서의 McCormick Tightness—이 결합하여 LP 솔버를 정수 꼭짓점으로 유도하기 때문이다. $\delta_{\text{rel}} = 1\%$의 gapRel은 허용 상한으로서, 실제 Gap이 이를 크게 하회한다.

*대규모 인스턴스 (≥40개 위협):* LARGE_40(평균 Gap 15.4%, 최대 28.7%)과 STRESS_100(평균 Gap 67.2%, 최대 100%)에서는 LP 완화가 정수 꼭짓점에서 최적에 도달하지 못하여 실질적인 Gap이 발생한다. 위협 수가 증가하면 교전 가능 쌍이 급증하고(LARGE_40: ~476개 변수, STRESS_100: ~1,256개 변수), LP 완화는 무기체계를 분수적으로 배분하는 해를 통해 정수 최적해보다 낮은(더 좋은) 하한을 달성할 수 있게 된다. 최대 Gap 100%는 STRESS_100의 일부 시점에서 $Z_{\text{LP}}^{\text{root}} \approx 0$인 반면 $Z^* > 0$임을 의미하며, LP가 제한된 요격 자산을 분산 배분하여 이론적으로 완전 방어를 표현하는 극단적 이완이 발생한 것이다. 그러나 B\&B는 gapRel=1% 내에서 수렴하며, STRESS_100에서도 평균 풀이 시간 5.1초 이내에 실행 가능 해를 반환한다.

목적함수 $Z^* = \sum_i v_i \cdot S_i^*$는 식 (1)의 최솟값으로 양수이며, 자산 가치 가중 생존확률 합계로 직접 해석된다(낮을수록 방어 효과 높음). BASELINE_15 기준 $Z^* \approx 334$는 자산 가치 합계 $\sum v_i = 9{,}900$ 대비 약 3.4%의 기대 위험 손실에 해당한다.

### 4.5 Warm-start 효과

Warm-start 적용 시와 미적용(Cold-start) 시를 동일 시나리오로 비교한 결과, 솔버 풀이 시간이 평균 4–5배 단축됨을 확인하였다. 특히 위협이 20–40개인 중·대규모 시나리오에서 98% 이상의 적용률과 함께 가장 큰 성능 이득(최대 풀이 시간 10초 → 0.95초 이하)이 관찰되었다. Warm-start의 4단계 우선순위 매핑(3.3.5절)에서 '완전 일치(Exact Match)'가 전체 매핑의 다수를 차지하여, Rolling Horizon 환경에서 연속된 타임스텝 간 해의 구조적 유사성이 높음을 확인하였다.

---

## 5. 결론

### 수리적 기여

본 연구는 DWTA 목적함수에 포함된 이진-연속 Bilinear Term을 McCormick 선형화[11]를 통해 4개 선형 부등식으로 등가 변환하고, 이를 엄밀히 증명하였다. 이 변환은 LP Relaxation의 하한을 강화하여 Branch-and-Bound 탐색 공간을 대폭 감소시키며, 비선형 솔버를 대체하여 전역 최적성을 MIP 프레임워크 내에서 보장한다. 또한 Multilinear Product를 Binary Tree 구조로 분해하여 선형화함으로써, 다층 방어체계의 계층 간 상호의존성을 수리모형에 직접 통합하였다.

### 알고리즘적 기여

양방향 인덱스, 희소 변수 생성, K-factor LUT, Warm-start를 통합한 구현 최적화로, 실전 운용 규모(20개 위협, 6개 포대)에서 평균 0.26초, 100개 극한 시나리오에서도 평균 0.68초 이내의 최적화를 달성하였다. Rolling Horizon 환경에서 Warm-start 적용률 65.5–98.6%를 기록하여 반복 최적화의 계산 비용을 실효적으로 절감하였다.

### 실험적 기여

3–100개 위협 전 시나리오에서 성공률 100%를 달성하였다. 소규모 시나리오(3–15개)에서 일부 타임스텝(최대 4.9%)이 시간 제한에 도달하였으나, 이 경우에도 모두 실현 가능 해를 반환하였다. 기존 비선형 솔버 대비 동일 조건에서 약 79배 이상의 속도 향상을 확인하였다.

### 향후 연구과제

(1) 100개 이상 대규모 시나리오에 대한 문제 분해(Decomposition)·병렬 솔버 적용으로 확장성 강화, (2) 전자전·기상 조건을 포함한 확률적 K-factor 모형(Stochastic K-factor) 및 강건 최적화(Robust Optimization) 적용, (3) 실제 방어체계 운용자와의 Human-in-the-Loop(HITL) 검증 실험 수행, (4) 하이퍼파라미터(갭 허용치, 시간 제한) 적응형 튜닝 기법 연구.

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

[12] Manne, A.S., A Target-Assignment Problem, *Operations Research*, 1958, Vol. 6, No. 3, pp. 346-351. https://doi.org/10.1287/opre.6.3.346

[13] Lloyd, S.P. and Witsenhausen, H.S., Weapons Allocation is NP-Complete, *Proceedings of the 1986 Summer Computer Simulation Conference*, 1986, pp. 1054-1058.

[14] Kline, A., Ahner, D. and Hill, R., The Weapon-Target Assignment Problem, *Computers & Operations Research*, 2019, Vol. 105, pp. 226-236. https://doi.org/10.1016/j.cor.2018.10.015

[15] Ahuja, R.K., Kumar, A., Jha, K.C. and Orlin, J.B., Exact and Heuristic Algorithms for the Weapon-Target Assignment Problem, *Operations Research*, 2007, Vol. 55, No. 6, pp. 1136-1146. https://doi.org/10.1287/opre.1070.0440

[16] Kline, A.G., Ahner, D.K. and Lunday, B.J., Real-time Heuristic Algorithms for the Static Weapon Target Assignment Problem, *Journal of Heuristics*, 2019, Vol. 25, No. 3, pp. 377-397. https://doi.org/10.1007/s10732-018-9401-1

[17] Lu, Y. and Chen, D.Z., A New Exact Algorithm for the Weapon-Target Assignment Problem, *Omega*, 2021, Vol. 98, Article 102138. https://doi.org/10.1016/j.omega.2019.102138

[18] Andersen, A.C., Pavlikov, K. and Toffolo, T.A.M., Weapon-Target Assignment Problem: Exact and Approximate Solution Algorithms, *Annals of Operations Research*, 2022, Vol. 312, No. 2, pp. 581-606. https://doi.org/10.1007/s10479-022-04525-6
