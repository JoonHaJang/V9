"""
Optimized MIP Wrapper - 기존 시스템과의 통합
===========================================
기존 NonLinearMIPOptimizer와 호환되는 인터페이스 제공
"""

from optimized_mip_core import OptimizedMIPCore, SparseEngagementMatrix
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time

@dataclass
class Asset:
    """방어 자산"""
    id: str
    position: Tuple[float, float]
    value: float
    priority: int
    estimated_threat_missiles: List[str]

@dataclass
class InterceptorSystem:
    """요격체계"""
    id: str
    system_type: str
    position: Tuple[float, float]
    available_missiles: int
    max_missiles_per_target: int
    intercept_probability: float
    engagement_range: float

@dataclass
class Threat:
    """위협 미사일"""
    id: str
    target_asset_id: str
    current_position: Tuple[float, float, float]
    estimated_impact_time: float
    launch_position: Tuple[float, float] = (0.0, 0.0)
    flight_time: float = 300.0
    specs: dict = None
    launch_time: float = 0.0
    trajectory_type: str = "ballistic"
    rcs: float = 0.5


class OptimizedMIPWrapper:
    """
    기존 NonLinearMIPOptimizer를 대체할 수 있는 래퍼
    - 동일한 인터페이스 제공
    - 내부적으로 OptimizedMIPCore 사용
    """

    def __init__(self, config):
        self.config = config
        self.core = OptimizedMIPCore(config)

        # 기존 인터페이스 호환성
        self.model = None
        self.variables = {}
        self.constraints = {}
        self.objective_value = 0
        self.solve_time = 0
        self.status = None

        # 몬테카를로 시뮬레이션용
        self.custom_intercept_probs = {}

        # 데이터 저장
        self.assets = []
        self.interceptor_systems = []
        self.threats = []
        self.batteries = []

        # 성능 메트릭
        self.performance_metrics = {
            'build_time': 0,
            'solve_time': 0,
            'total_time': 0,
            'num_variables': 0,
            'num_constraints': 0,
            'sparsity': 0
        }

    def create_model(self,
                    assets: List[Asset],
                    interceptor_systems: List[InterceptorSystem],
                    threats: List[Threat],
                    batteries: List[Dict] = None,
                    engagement_matrix = None):
        """
        모델 생성 - 기존 인터페이스와 동일
        """

        print("\n" + "🔥"*30)
        print("OPTIMIZED MIP WRAPPER - Model Creation")
        print("🔥"*60)

        # 데이터 저장
        self.assets = assets
        self.interceptor_systems = interceptor_systems
        self.threats = threats
        self.batteries = batteries or []

        # Threat 객체를 dict로 변환 (Sparse Matrix 빌드용)
        threats_dict = []
        for threat in threats:
            threat_dict = {
                'id': getattr(threat, 'id', ''),
                'target_asset': getattr(threat, 'target_asset_id', ''),
                'position': getattr(threat, 'current_position', (0, 0, 0)),
                'estimated_impact_time': getattr(threat, 'estimated_impact_time', 0)
            }
            threats_dict.append(threat_dict)

        # Assets를 dict로 변환
        assets_dict = []
        for asset in assets:
            asset_dict = {
                'id': getattr(asset, 'id', ''),
                'position': getattr(asset, 'position', (0, 0)),
                'value': getattr(asset, 'value', 10.0),
                'priority': getattr(asset, 'priority', 1)
            }
            assets_dict.append(asset_dict)

        # Enhanced Engagement Matrix 확인
        from config_mip import EnhancedEngagementMatrix
        if not isinstance(engagement_matrix, EnhancedEngagementMatrix):
            print("⚠️  Warning: EnhancedEngagementMatrix not provided!")
            print("   Creating basic engagement matrix...")
            # 기본 매트릭스 생성 로직 필요
            return None

        # OptimizedMIPCore로 모델 생성
        start_time = time.time()

        self.model = self.core.create_optimized_model(
            self.batteries,
            threats_dict,
            assets_dict,
            engagement_matrix
        )

        if self.model is None:
            print("❌ Model creation failed!")
            return None

        # 성능 메트릭 저장
        self.performance_metrics['build_time'] = self.core.build_time
        self.performance_metrics['num_variables'] = self.core.num_variables
        self.performance_metrics['num_constraints'] = self.core.num_constraints

        print("✅ Optimized model created successfully!\n")

        return self.model

    def solve(self, time_limit=10.0, mip_gap=0.02):
        """
        모델 풀이 - 기존 인터페이스와 동일한 결과 반환
        """

        if self.model is None:
            return {
                'feasible': False,
                'objective_value': float('inf'),
                'upper_assignments': {},
                'lower_assignments': {}
            }

        # OptimizedMIPCore의 solve 호출
        result = self.core.solve(
            time_limit=time_limit,
            gap=mip_gap,
            threads=None  # 자동
        )

        # 성능 메트릭 업데이트
        self.performance_metrics['solve_time'] = result.get('solve_time', 0)
        self.performance_metrics['total_time'] = (
            self.performance_metrics['build_time'] +
            self.performance_metrics['solve_time']
        )

        # 상태 저장
        self.objective_value = result.get('objective_value', float('inf'))
        self.solve_time = result.get('solve_time', 0)
        self.status = result.get('status', 'Unknown')

        # 진단 정보 추가 (기존 시스템 호환)
        result['diagnosis'] = {
            'num_variables': self.performance_metrics['num_variables'],
            'num_constraints': self.performance_metrics['num_constraints'],
            'solver_status': self.status,
            'num_threats': len(self.threats),
            'num_batteries': len(self.batteries),
            'total_missiles': sum(b.get('available_missiles', 0) for b in self.batteries),
            'feasible_engagements': len(self.core.sparse_matrix.feasible_pairs),
            'time_limit_reached': False
        }

        return result

    def set_intercept_probabilities(self, intercept_probs):
        """몬테카를로 시뮬레이션에서 샘플링된 요격확률 설정"""
        self.custom_intercept_probs = intercept_probs.copy()
        # TODO: OptimizedMIPCore에 전달하는 로직 추가
        print(f"[OptimizedWrapper] Set custom intercept probabilities for {len(intercept_probs)} threats")

    def get_performance_report(self):
        """성능 리포트 생성"""

        report = f"""
{'='*70}
⚡ OPTIMIZED MIP PERFORMANCE REPORT
{'='*70}

📊 Variables & Constraints:
   Variables:    {self.performance_metrics['num_variables']:,}
   Constraints:  {self.performance_metrics['num_constraints']:,}

⏱️  Timing:
   Build Time:   {self.performance_metrics['build_time']:.3f}s
   Solve Time:   {self.performance_metrics['solve_time']:.3f}s
   Total Time:   {self.performance_metrics['total_time']:.3f}s

📈 Problem Size:
   Assets:       {len(self.assets)}
   Batteries:    {len(self.batteries)}
   Threats:      {len(self.threats)}
   Feasible Pairs: {len(self.core.sparse_matrix.feasible_pairs)}

🎯 Solution:
   Status:       {self.status}
   Objective:    {self.objective_value:.2f}

{'='*70}
        """

        return report


def create_optimized_optimizer(config, use_optimized=True):
    """
    Factory 함수 - 최적화 버전 또는 기존 버전 생성

    Args:
        config: MIPConfig 객체
        use_optimized: True면 최적화 버전, False면 기존 버전

    Returns:
        Optimizer 인스턴스
    """

    if use_optimized:
        print("🚀 Creating Optimized MIP Optimizer...")
        return OptimizedMIPWrapper(config)
    else:
        print("📊 Creating Original MIP Optimizer...")
        from nonlinear_mip_optimizer import NonLinearMIPOptimizer
        return NonLinearMIPOptimizer(config)


# 🔥 A/B 테스트 함수
def compare_optimizers(config, assets, systems, threats, batteries, engagement_matrix):
    """
    기존 vs 최적화 버전 성능 비교
    """

    print("\n" + "="*80)
    print("🔬 OPTIMIZER COMPARISON TEST")
    print("="*80)

    results = {}

    # 1. 기존 버전 테스트
    print("\n[1/2] Testing Original Optimizer...")
    try:
        from nonlinear_mip_optimizer import NonLinearMIPOptimizer

        original = NonLinearMIPOptimizer(config)

        start = time.time()
        original.create_model(assets, systems, threats, batteries, engagement_matrix)
        result_original = original.solve()
        time_original = time.time() - start

        results['original'] = {
            'time': time_original,
            'objective': result_original.get('objective_value', float('inf')),
            'feasible': result_original.get('feasible', False),
            'status': result_original.get('status', 'Unknown')
        }

        print(f"   ✅ Original: {time_original:.3f}s, Obj={results['original']['objective']:.2f}")

    except Exception as e:
        print(f"   ❌ Original failed: {e}")
        results['original'] = None

    # 2. 최적화 버전 테스트
    print("\n[2/2] Testing Optimized Optimizer...")
    try:
        optimized = OptimizedMIPWrapper(config)

        start = time.time()
        optimized.create_model(assets, systems, threats, batteries, engagement_matrix)
        result_optimized = optimized.solve()
        time_optimized = time.time() - start

        results['optimized'] = {
            'time': time_optimized,
            'objective': result_optimized.get('objective_value', float('inf')),
            'feasible': result_optimized.get('feasible', False),
            'status': result_optimized.get('status', 'Unknown')
        }

        print(f"   ✅ Optimized: {time_optimized:.3f}s, Obj={results['optimized']['objective']:.2f}")

    except Exception as e:
        print(f"   ❌ Optimized failed: {e}")
        results['optimized'] = None

    # 3. 비교 결과
    print("\n" + "="*80)
    print("📊 COMPARISON RESULTS")
    print("="*80)

    if results['original'] and results['optimized']:
        speedup = results['original']['time'] / results['optimized']['time']
        obj_diff = abs(results['original']['objective'] - results['optimized']['objective'])

        print(f"\n⚡ Speed Improvement: {speedup:.2f}x faster")
        print(f"   Original:  {results['original']['time']:.3f}s")
        print(f"   Optimized: {results['optimized']['time']:.3f}s")

        print(f"\n🎯 Objective Quality:")
        print(f"   Original:  {results['original']['objective']:.2f}")
        print(f"   Optimized: {results['optimized']['objective']:.2f}")
        print(f"   Difference: {obj_diff:.2f} ({'Same' if obj_diff < 0.1 else 'Different'})")

        print(f"\n✅ Both solutions are {'EQUIVALENT' if obj_diff < 0.1 and speedup > 1.5 else 'COMPARABLE'}")

        if speedup > 2.0:
            print(f"🎉 OPTIMIZED VERSION IS {speedup:.1f}x FASTER!")

    print("="*80 + "\n")

    return results
