# DWTA 알고리즘 성능 비교 실험 가이드

## 📋 개요

본 프레임워크는 **MIP Optimizer**, **Greedy**, **GA** 알고리즘의 성능을 비교하기 위한 자동화된 실험 환경을 제공합니다.

---

## 🗂️ 파일 구조

```
Paper_DWTA_2025_12_08/
├── baseline_algorithms.py          # Greedy, GA 구현
├── performance_logger.py            # 성능 측정 및 로깅
├── run_comparison_experiment.py    # 비교 실험 스크립트
├── multi_missile_tracker_gui.py    # 메인 시뮬레이터 (통합됨)
└── performance_results/             # 결과 저장 디렉토리
    ├── *.csv                        # CSV 결과
    ├── *.json                       # JSON 결과
    ├── *.tex                        # LaTeX 표
    └── *.png                        # 비교 그래프
```

---

## 🚀 빠른 시작

### 1. 기본 비교 실험 실행

```bash
python run_comparison_experiment.py
```

**기본 설정**:
- 시나리오: `BASELINE_15`
- 알고리즘: `MIP`, `Greedy`, `GA`

---

### 2. 특정 시나리오 실험

```bash
# 단일 시나리오
python run_comparison_experiment.py BASELINE_15

# 여러 시나리오
python run_comparison_experiment.py LIGHT_5,BASELINE_15,HEAVY_30
```

---

### 3. 특정 알고리즘만 비교

```bash
# MIP vs Greedy만
python run_comparison_experiment.py BASELINE_15 MIP,Greedy

# 모든 알고리즘
python run_comparison_experiment.py BASELINE_15 MIP,Greedy,GA
```

---

## 📊 측정 지표

### A. 방어 효과성
- **자산 생존율** (`survival_rate`): 생존한 자산 비율 (%)
- **가치 보존율** (`value_preservation_rate`): 보존된 자산 가치 비율 (%)
- **요격 성공률** (`intercept_rate`): 요격 성공 비율 (%)

### B. 자원 효율성
- **미사일 사용률** (`usage_rate`): 사용된 미사일 비율 (%)
- **위협당 미사일** (`missiles_per_threat`): 평균 미사일 사용 개수
- **미사일 효율** (`successful_intercepts_per_missile`): 미사일당 요격 성공률

### C. 계산 성능
- **평균 최적화 시간** (`avg_solve_time`): 평균 solver 실행 시간 (초)
- **최대 최적화 시간** (`max_solve_time`): 최대 solver 실행 시간 (초)
- **총 최적화 시간** (`total_optimization_time`): 전체 최적화 시간 (초)

---

## 📈 결과 분석

### 1. CSV 결과 확인

```bash
# Excel이나 텍스트 에디터로 열기
performance_results/performance_comparison_YYYYMMDD_HHMMSS.csv
```

**포함 내용**:
- 모든 측정 지표
- 시나리오별, 알고리즘별 결과
- 타임스탬프

---

### 2. 비교 그래프

자동 생성되는 그래프:

1. **`survival_rate_comparison.png`**: 생존율 비교
2. **`intercept_rate_comparison.png`**: 요격률 비교
3. **`solve_time_comparison.png`**: 계산 시간 비교

---

### 3. LaTeX 표

논문에 바로 사용 가능한 LaTeX 표:

```latex
\begin{table}[htbp]
\centering
\caption{DWTA Algorithm Performance Comparison}
\label{tab:performance}
\begin{tabular}{lllrrr}
\hline
Scenario & Algorithm & Survival (\%) & Intercept (\%) & Efficiency & Time (s) \\
\hline
BASELINE_15 & MIP & 85.0 & 86.7 & 0.590 & 0.180 \\
BASELINE_15 & Greedy & 65.0 & 70.0 & 0.420 & 0.001 \\
BASELINE_15 & GA & 78.0 & 80.0 & 0.510 & 2.500 \\
\hline
\end{tabular}
\end{table}
```

---

## 🔬 논문용 실험 설계

### 실험 1: Optimality Gap (최적성 분석)

**목적**: MIP가 최적해를 찾고, Greedy/GA가 얼마나 떨어지는지 측정

```bash
# 여러 시나리오에서 실행
python run_comparison_experiment.py LIGHT_5,BASELINE_15,HEAVY_30,HEAVY_50 MIP,Greedy,GA
```

**분석**:
- MIP의 `objective_value`를 기준으로 Gap 계산
- Gap (%) = (Algorithm - MIP) / MIP × 100

---

### 실험 2: Computational Efficiency (실시간성 분석)

**목적**: 위협 수 증가에 따른 계산 시간 변화

```bash
# 규모별 시나리오 실행
python run_comparison_experiment.py LIGHT_5,BASELINE_15,HEAVY_30,HEAVY_50 MIP,GA
```

**분석**:
- X축: 위협 수 (5, 15, 30, 50)
- Y축: `avg_solve_time` (Log scale)
- MIP는 선형적, GA는 지수적 증가 예상

---

### 실험 3: Robustness (강건성 분석)

**목적**: 동일 시나리오 반복 실행 시 결과 안정성

```python
# 50회 반복 실험 (수동 스크립트)
for i in range(50):
    run_comparison_experiment(['BASELINE_15'], ['MIP', 'GA'])
```

**분석**:
- MIP: 결정론적 → 표준편차 0
- GA: 확률적 → 표준편차 > 0

---

## 📝 커스터마이징

### 1. GA 파라미터 조정

`baseline_algorithms.py`에서:

```python
tracker.ga_solver = GeneticAlgorithmDWTA(
    tracker.config,
    population_size=100,    # 개체군 크기 (기본: 50)
    generations=200,        # 세대 수 (기본: 100)
    mutation_rate=0.15      # 돌연변이율 (기본: 0.1)
)
```

---

### 2. 새로운 Baseline 추가

`baseline_algorithms.py`에 클래스 추가:

```python
class PSOAlgorithmDWTA:
    """Particle Swarm Optimization"""
    
    def solve(self, assets, systems, threats, batteries, engagement_matrix):
        # PSO 구현
        pass
```

`run_comparison_experiment.py`에서 사용:

```python
algorithms = ['MIP', 'Greedy', 'GA', 'PSO']
```

---

### 3. 추가 지표 측정

`performance_logger.py`의 `PerformanceMetrics`에 필드 추가:

```python
@dataclass
class PerformanceMetrics:
    # 기존 필드...
    
    # 새로운 지표
    coverage_overlap: float = 0
    reassignment_count: int = 0
    engagement_window_quality: float = 0
```

---

## 🎯 예상 결과

### BASELINE_15 시나리오

| Algorithm | Survival (%) | Intercept (%) | Efficiency | Time (s) |
|-----------|--------------|---------------|------------|----------|
| **MIP**   | **85.0**     | **86.7**      | **0.590**  | 0.180    |
| Greedy    | 65.0         | 70.0          | 0.420      | **0.001** |
| GA        | 78.0         | 80.0          | 0.510      | 2.500    |

**해석**:
- MIP: 최고 성능, 실시간 가능 (< 1초)
- Greedy: 가장 빠르지만 성능 낮음 (-20% survival)
- GA: 중간 성능, 느림 (14배)

---

## 🐛 문제 해결

### 1. Import 오류

```bash
ModuleNotFoundError: No module named 'baseline_algorithms'
```

**해결**: 파일이 같은 디렉토리에 있는지 확인

---

### 2. 메모리 부족

GA의 `population_size`나 `generations` 줄이기:

```python
population_size=30,  # 50 → 30
generations=50       # 100 → 50
```

---

### 3. 시뮬레이션 실패

Headless 모드 확인:

```python
tracker = MultiMissileTracker(use_mip=True, headless=True)
```

---

## 📚 참고 문헌

1. **Greedy Algorithm**: 최고 가치 자산 우선 방어
2. **Genetic Algorithm**: Holland (1975), "Adaptation in Natural and Artificial Systems"
3. **MIP with McCormick**: 본 연구의 기여

---

## 🎓 논문 작성 팁

### 그래프 1: 성능 비교 (Bar Chart)
```python
logger.plot_comparison('survival_rate', save_path='fig1_survival.png')
```

### 그래프 2: 계산 시간 (Log Scale)
```python
logger.plot_comparison('avg_solve_time', save_path='fig2_time.png')
```

### 그래프 3: 수렴 곡선 (GA만)
```python
logger.plot_convergence('BASELINE_15', algorithms=['GA'], save_path='fig3_convergence.png')
```

---

## ✅ 체크리스트

실험 전:
- [ ] 모든 파일이 같은 디렉토리에 있는지 확인
- [ ] `performance_results/` 디렉토리 생성 확인
- [ ] 시나리오 설정 확인 (`config_mip.py`)

실험 후:
- [ ] CSV 결과 확인
- [ ] 그래프 생성 확인
- [ ] LaTeX 표 생성 확인
- [ ] 결과 백업

---

**문의**: 추가 기능이 필요하면 `performance_logger.py`나 `baseline_algorithms.py`를 수정하세요.
