"""
Non-linear MIP Optimizer with McCormick Relaxation
==================================================
원래 목적함수를 McCormick 선형화로 구현

목적함수: min Z = Σ B_i * [Π (1 - x_iu*k_iu*P_iu) * Π (1 - x_il*k_il*P_il)]

수정사항:
- k_iu: 교전 윈도우 기반 확률 보정 계수 (0.6~1.0 연속값)
- 미사일 수: 교전 시 기본 2발 고정
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
import sys

try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False
    logging.warning("PuLP not available. Install with: pip install pulp")

from config_mip import (
    MIPConfig,
    EnhancedEngagementMatrix,
    KFactorCache,
    McCormickCoefficients,
    StateFilter,
    BinaryTreeMcCormickCache
)
import time

# 🆕 Warm-start 통합
try:
    from warmstart_integration import add_warmstart_methods
    WARMSTART_AVAILABLE = True
except ImportError:
    WARMSTART_AVAILABLE = False
    logging.warning("Warm-start module not available")

@dataclass
class Asset:
    """방어 자산"""
    id: str
    position: Tuple[float, float]  # (x, y) 좌표
    value: float  # B_i: 자산 가치
    priority: int
    estimated_threat_missiles: List[str]  # 위협하는 미사일 ID들

@dataclass 
class InterceptorSystem:
    """요격체계 (상층/하층)"""
    id: str
    system_type: str  # "UPPER" (상층) or "LOWER" (하층)  
    position: Tuple[float, float]
    available_missiles: int  # M_u or M_l
    max_missiles_per_target: int  # 사용하지 않음 (항상 2발 고정)
    intercept_probability: float  # P (단발 요격 확률)
    engagement_range: float

@dataclass
class Threat:
    """위협 미사일 - 교전 윈도우 계산을 위한 확장 정보 포함"""
    id: str
    target_asset_id: str
    current_position: Tuple[float, float, float]
    estimated_impact_time: float
    
    # 교전 윈도우 계산을 위한 추가 속성
    launch_position: Tuple[float, float] = (0.0, 0.0)
    flight_time: float = 300.0
    specs: dict = None
    launch_time: float = 0.0
    trajectory_type: str = "ballistic"
    rcs: float = 0.5
    
    def __post_init__(self):
        if self.specs is None:
            self.specs = {
                "max_altitude_km": 50.0,
                "avg_speed_kmh": 2000.0,
                "trajectory_type": self.trajectory_type,
                "rcs": self.rcs
            }

class NonLinearMIPOptimizer:
    """McCormick 선형화를 사용한 비선형 MIP 최적화기 - 현실적 운영 제약조건 반영"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.variables = {}
        self.constraints = {}
        self.objective_value = 0
        self.solve_time = 0
        self.status = None
        # 몬테카를로 시뮬레이션용 샘플링된 요격확률
        self.custom_intercept_probs = {}
        
        # 🆕 Warm-start: 이전 타임스텝 해 저장
        self.previous_solution = None
        self.previous_threats = set()
        self.previous_systems_capacity = {}

        # Root Node Gap 측정 플래그 (논문 실험용, 기본 비활성화)
        self.capture_root_gap = False
        
        # 로깅 설정 (디버그 출력 비활성화)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.WARNING)  # INFO 메시지 비활성화
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
        
        # McCormick 선형화 파라미터
        self.big_M = 1000  # Big-M 값
        self.epsilon = 1e-6  # 수치적 안정성
        
        # k 파라미터 범위 (교전 윈도우 기반 확률 보정 계수)
        self.k_min = 0.6  # 하한: 최악 조건에서도 60% 효율 보장
        self.k_max = 1.0  # 상한: 최적 조건에서 100% 효율
        
        # 미사일 수 고정값
        self.missiles_per_engagement = 2  # 교전 시 기본 2발 사용
        
        # 성능 최적화 파라미터
        self.use_binary_tree_method = True  # 이진 트리 방식 사용
        self.use_warm_start = True  # 웜 스타트 사용
        self.use_advanced_solver_options = True  # 고급 솔버 옵션 사용
        self.fast_mode = True  # 빠른 모드: 속도 우선 최적화
        
        # 🔧 CRITICAL: Warm-start 엔진 초기화 (메서드가 추가된 후 호출됨)
        
        # 현실적 운영 제약조건 설정
        self.max_engagements_per_target = 2  # 표적당 최대 교전 횟수
        self.enable_engagement_zones = True  # 교전 영역 제약 활성화
        self.enable_capacity_constraints = True  # 용량 제약 활성화
        self.enable_launcher_exclusivity = False  # 발사대 단독 할당 제약 (False = 다중 교전 허용)
        self.enable_multi_layer_defense = True  # 다층 방어 활성화
        
        # 교전 가능성 매트릭스 (나중에 설정)
        self.engagement_matrix = {}
        self.battery_specs = {}  # 포대별 스펙 정보
        
        # 🆕 최적화 캐시 객체들
        self.engagement_matrix_cache = None
        self.k_factor_cache = None
        self.mccormick_cache = None
        self.binary_tree_cache = BinaryTreeMcCormickCache()  # Binary Tree 통계용
        
    def create_model(self,
                    assets: List[Asset],
                    interceptor_systems: List[InterceptorSystem],
                    threats: List[Threat],
                    batteries: List[Dict] = None,
                    engagement_matrix: Dict = None,
                    current_time: float = 0.0):
        """비선형 MIP 모델 생성 - 현실적 운영 제약조건 반영

        Args:
            current_time: 현재 시간 (초, Time-based K-factor 계산용)
        """
        
        if not PULP_AVAILABLE:
            raise ImportError("PuLP is required for MIP optimization")
        
        # 🆕 1. Enhanced Engagement Matrix 처리 (캐시 재사용)
        if isinstance(engagement_matrix, EnhancedEngagementMatrix):
            if not hasattr(self, 'engagement_matrix_cache') or self.engagement_matrix_cache is None:
                self.engagement_matrix_cache = engagement_matrix
                print("[OK] Enhanced Engagement Matrix 사용")
        else:
            if not hasattr(self, 'engagement_matrix_cache'):
                print("[WARN] 기존 engagement_matrix 사용 (최적화 미적용)")
                self.engagement_matrix_cache = None
            # 기존 dict 형태 저장
            if engagement_matrix:
                self.engagement_matrix = engagement_matrix
        
        # 🆕 2. K-Factor 캐시 생성 (이미 존재하면 재사용)
        if self.engagement_matrix_cache and not hasattr(self, 'k_factor_cache'):
            self.k_factor_cache = KFactorCache(k_min=self.k_min, k_max=self.k_max)
            self.k_factor_cache.precompute(
                threats,
                interceptor_systems,
                self.engagement_matrix_cache,
                current_time=current_time  # 🆕 Time-based K-factor
            )
        
        # 🆕 3. McCormick 계수 캐시 생성 (이미 존재하면 재사용)
        if hasattr(self, 'k_factor_cache') and not hasattr(self, 'mccormick_cache'):
            self.mccormick_cache = McCormickCoefficients(
                k_min=self.k_min, 
                k_max=self.k_max,
                missiles_per_engagement=self.missiles_per_engagement
            )
            self.mccormick_cache.precompute(
                threats, 
                interceptor_systems, 
                self.k_factor_cache
            )
        
        # 모델 생성 (최소화 문제)
        self.model = pulp.LpProblem("Realistic_DWTA", pulp.LpMinimize)
        
        # 인덱스 집합 생성
        self.assets = assets
        self.interceptor_systems = interceptor_systems
        self.threats = threats
        self.batteries = batteries or []
        
        # 기존 engagement_matrix가 dict인 경우 저장
        if not self.engagement_matrix_cache:
            if engagement_matrix:
                self.engagement_matrix = engagement_matrix
            else:
                # engagement_matrix가 제공되지 않았으면 생성
                from config_mip import EngagementZoneConfig
                self.engagement_matrix = EngagementZoneConfig.create_engagement_matrix()
                print(f"[INFO] Engagement matrix auto-generated: {len(self.engagement_matrix)} pairs")
        else:
            self.engagement_matrix = {}  # 캐시 사용 시 빈 dict
        
        # 상층/하층 시스템 분리 (LSAM=상층, MSAM=하층)
        # Backward compatibility: 기존 "UPPER"/"LOWER" 명명 규칙도 지원
        self.upper_systems = [s for s in interceptor_systems if getattr(s, 'system_type', '') in ["LSAM", "UPPER"]]
        self.lower_systems = [s for s in interceptor_systems if getattr(s, 'system_type', '') in ["MSAM", "LOWER"]]
        
        # 포대별 스펙 정보 저장
        for battery in self.batteries:
            self.battery_specs[battery["id"]] = battery["specs"]
        
        print(f"Model setup: {len(assets)} assets, {len(self.upper_systems)} upper, {len(self.lower_systems)} lower systems, {len(threats)} threats")
        
        # 결정변수 생성 (먼저 실행하여 실제 교전 가능 쌍 계산)
        self._create_decision_variables()
        
        # 🆕 FBBT 적용 (탐색 공간 감소)
        self._apply_fbbt()
        
        # 🔥 방안 B: engagement_matrix_cache 사용 시에도 실제 생성된 변수 수 출력
        total_feasible_pairs = len(self.variables.get('x_upper', {})) + len(self.variables.get('x_lower', {}))
        print(f"Batteries: {len(self.batteries)}, Engagement matrix: {total_feasible_pairs} feasible pairs (cache-based)")
        
        # McCormick 변수 딕셔너리 초기화
        self.mccormick_variables = {}
        
        # McCormick 보조 변수 및 제약조건 생성
        self._create_mccormick_linearization()
        
        # 원래 제약조건 추가
        self._add_original_constraints()
        
        # 선형화된 목적함수 설정
        self._set_linearized_objective()
        
        # self.logger.info("Non-linear MIP model created successfully")
    
    def _create_decision_variables(self):
        """결정변수 생성 - k를 교전 윈도우 기반 확률 보정 계수로 재정의"""
        
        # 🆕 교전 매트릭스 처리 (캐시 사용 또는 기존 방식)
        if not self.engagement_matrix_cache:
            # 이미 dict로 설정된 경우 재생성 생략
            if not self.engagement_matrix:
                from config_mip import EngagementZoneConfig
                self.engagement_matrix = EngagementZoneConfig.create_engagement_matrix()
                print(f"Engagement matrix created with {len(self.engagement_matrix)} battery-threat pairs")
        
        # x_iu: 상층 요격체계 u가 자산 i를 방어하는 미사일 위협에 할당 (0 or 1)
        self.variables['x_upper'] = {}

        # 하층 시스템 변수들
        self.variables['x_lower'] = {}

        # K_ij 상수값 저장 (결과 보고용)
        self.k_constants = {}
        
        # ⚡ 성능 최적화: getattr 호출 최소화
        # 상층 시스템 할당 변수 생성
        for asset in self.assets:
            asset_id = getattr(asset, 'id', '')  # 한 번만 호출
            for threat in self.threats:
                threat_target = getattr(threat, 'target_asset_id', '')  # 한 번만 호출
                if threat_target == asset_id:
                    threat_id = getattr(threat, 'id', '')  # 한 번만 호출
                    for system in self.upper_systems:
                        system_id = getattr(system, 'id', '')  # 한 번만 호출
                        key = (asset_id, threat_id, system_id)
                        
                        # 🆕 교전 매트릭스 확인 - 교전 가능한 경우만 변수 생성
                        # 캐시 사용 또는 기존 dict 사용
                        if self.engagement_matrix_cache:
                            # 🔧 FIX: 실시간 위치 정보 전달
                            threat_current_pos = getattr(threat, 'current_position', None)
                            if threat_current_pos and len(threat_current_pos) >= 2:
                                threat_current_pos = (threat_current_pos[0], threat_current_pos[1])
                            
                            battery_position = None
                            battery_specs = None
                            for bat in self.batteries:
                                if bat['id'] == system_id:
                                    battery_position = bat.get('position')
                                    battery_specs = bat.get('specs')
                                    break
                            
                            is_feasible = self.engagement_matrix_cache.is_feasible(
                                system_id, 
                                threat_id,
                                threat_current_position=threat_current_pos,
                                battery_position=battery_position,
                                battery_specs=battery_specs
                            )
                        else:
                            engagement_key = (system_id, threat_id)
                            is_feasible = self.engagement_matrix.get(engagement_key, False)
                        
                        if is_feasible:
                            # 이진 할당 변수
                            self.variables['x_upper'][key] = pulp.LpVariable(
                                f"x_upper_{asset_id}_{threat_id}_{system_id}",
                                cat='Binary'
                            )
        
        # 하층 시스템 할당 변수 생성
        for asset in self.assets:
            asset_id = getattr(asset, 'id', '')  # 한 번만 호출
            for threat in self.threats:
                threat_target = getattr(threat, 'target_asset_id', '')  # 한 번만 호출
                if threat_target == asset_id:
                    threat_id = getattr(threat, 'id', '')  # 한 번만 호출
                    for system in self.lower_systems:
                        system_id = getattr(system, 'id', '')  # 한 번만 호출
                        key = (asset_id, threat_id, system_id)
                        
                        # 🆕 교전 매트릭스 확인 - 교전 가능한 경우만 변수 생성
                        # 캐시 사용 또는 기존 dict 사용
                        if self.engagement_matrix_cache:
                            # 🔧 FIX: 실시간 위치 정보 전달
                            threat_current_pos = getattr(threat, 'current_position', None)
                            if threat_current_pos and len(threat_current_pos) >= 2:
                                threat_current_pos = (threat_current_pos[0], threat_current_pos[1])
                            
                            battery_position = None
                            battery_specs = None
                            for bat in self.batteries:
                                if bat['id'] == system_id:
                                    battery_position = bat.get('position')
                                    battery_specs = bat.get('specs')
                                    break
                            
                            is_feasible = self.engagement_matrix_cache.is_feasible(
                                system_id, 
                                threat_id,
                                threat_current_position=threat_current_pos,
                                battery_position=battery_position,
                                battery_specs=battery_specs
                            )
                        else:
                            engagement_key = (system_id, threat_id)
                            is_feasible = self.engagement_matrix.get(engagement_key, False)
                        
                        if is_feasible:
                            # 이진 할당 변수
                            self.variables['x_lower'][key] = pulp.LpVariable(
                                f"x_lower_{asset_id}_{threat_id}_{system_id}",
                                cat='Binary'
                            )
        
        # 🆕 최적화: Print I/O 제거 (20-40ms 절약)
        # print(f"Created {len(self.variables['x_upper'])} upper system variables (engagement-feasible only)")
        # print(f"Created {len(self.variables['x_lower'])} lower system variables (engagement-feasible only)")
        # print(f"k range: [{self.k_min}, {self.k_max}], missiles per engagement: {self.missiles_per_engagement}")
        # print(f"Engagement constraints applied: {len(self.engagement_matrix)} total, {sum(self.engagement_matrix.values())} feasible")
    
    def _can_engage(self, battery_id: str, threat_id: str) -> bool:
        """포대가 위협을 교전할 수 있는지 확인 (다층 방어 강화)"""
        
        # 디버깅: 교전 매트릭스 상태 확인
        if not hasattr(self, 'engagement_matrix') or not self.engagement_matrix:
            print(f"DEBUG: No engagement matrix available! Matrix size: {len(getattr(self, 'engagement_matrix', {}))}")
            return False
            
        if not self.enable_engagement_zones:
            # 교전 영역 제약 비활성화시 모든 교전 허용
            # 다층 방어 강화: 상층 시스템 활용 인센티브 제공
            if battery_id.startswith('LSAM') or battery_id.startswith('S') and any(getattr(s, 'id', '') == battery_id and getattr(s, 'system_type', '') in ["LSAM", "UPPER"] for s in self.upper_systems):
                print(f"Upper layer system {battery_id} engagement enabled for threat {threat_id}")
            return True
        
        # 교전 가능성 매트릭스에서 확인
        key = (battery_id, threat_id)
        can_engage = self.engagement_matrix.get(key, False)
        
        # 다층 방어 강화: 상층 시스템 교전 가능성 로깅
        is_upper_system = (battery_id.startswith('LSAM') or 
                          any(getattr(s, 'id', '') == battery_id and getattr(s, 'system_type', '') in ["LSAM", "UPPER"] for s in self.upper_systems))
        if is_upper_system:
            if can_engage:
                print(f"Upper layer system {battery_id} CAN engage threat {threat_id}")
            else:
                print(f"Upper layer system {battery_id} CANNOT engage threat {threat_id} - engagement matrix restriction")
        
        return can_engage
    
    def set_intercept_probabilities(self, intercept_probs):
        """몬테카를로 시뮬레이션에서 샘플링된 요격확률 설정"""
        self.custom_intercept_probs = intercept_probs.copy()
        print(f"Optimizer: Set custom intercept probabilities for {len(intercept_probs)} threats")
    
    def _calculate_k_value(self, battery: Dict, threat: Dict, base_k: float = 1.0) -> float:
        """교전 윈도우 기반 k 값 계산"""
        
        # 기존 교전 윈도우 계산 로직 활용
        from config_mip import EngagementZoneConfig
        
        battery_info = {
            "id": battery.get("id", ""),
            "position": battery.get("position", (0, 0)),
            "coverage_radius_km": battery.get("coverage_radius_km", 100),
            "system_type": battery.get("system_type", "LSAM")
        }
        
        threat_info = {
            "id": getattr(threat, 'id', ""),
            "launch_position": getattr(threat, 'launch_position', (0, 0)),
            "target_asset_id": getattr(threat, 'target_asset_id', ""),
            "flight_time": getattr(threat, 'flight_time', 300),
            "specs": getattr(threat, 'specs', {})
        }
        
        # 윈도우 품질 계산
        window_analysis = EngagementZoneConfig.calculate_engagement_time_window(battery_info, threat_info)
        
        if not window_analysis.get("can_engage", False):
            return self.k_min
        
        window_quality = window_analysis.get("window_quality", 0.5)
        
        # k 값을 윈도우 품질에 따라 조정 (0.6~1.0 범위)
        k_value = self.k_min + (self.k_max - self.k_min) * window_quality
        
        return max(self.k_min, min(self.k_max, k_value))
    
    def _create_mccormick_linearization(self):
        """McCormick 선형화 적용"""
        
        # Step 1: 각 곱 항 x*k*P를 선형화
        self._linearize_xkp_products()
        
        # Step 2: 생존 확률 (1 - 요격확률) 계산
        self._create_survival_probability_variables()
        
        # Step 3: 자산별 총 생존 확률 (상층 × 하층) 선형화
        self._linearize_asset_survival_probability()
    
    def _linearize_xkp_products(self):
        """w_ij = K_ij * P_ij * x_ij 선형화.

        K_ij는 LUT에서 사전 계산된 상수이므로 w_ij = (K_ij * P_ij) * x_ij 는
        이진변수에 상수를 곱한 선형 항이다. McCormick 선형화는 필요하지 않다.
        """
        import numpy as np

        def _get_k_constant(threat_id, system_id, threat_obj, system_obj):
            """LUT에서 K 상수값 계산 (거리 기반 or fallback)."""
            if self.k_factor_cache and hasattr(self.k_factor_cache, 'get_k_from_distance'):
                threat_pos = getattr(threat_obj, 'current_position', None)
                system_pos = getattr(system_obj, 'position', None)
                if threat_pos and system_pos:
                    distance = np.linalg.norm(
                        np.array(threat_pos[:2]) - np.array(system_pos[:2])
                    )
                    max_range = getattr(system_obj, 'engagement_range', 1.0)
                    k = self.k_factor_cache.get_k_from_distance(distance, max_range)
                    if k is not None:
                        return float(np.clip(k, self.k_min, self.k_max))
            return (self.k_min + self.k_max) / 2.0  # fallback: 중앙값

        def _get_p_total(threat_id, system_id, default_p_single):
            if self.mccormick_cache:
                coeffs = self.mccormick_cache.get_coeffs(threat_id, system_id)
                if coeffs:
                    return coeffs['P_total']
            if threat_id in self.custom_intercept_probs:
                p = self.custom_intercept_probs[threat_id]
            else:
                p = default_p_single
            return 1 - (1 - p) ** self.missiles_per_engagement

        # 상층 시스템
        self.mccormick_variables['w_upper'] = {}
        upper_constraints = []

        for asset in self.assets:
            asset_id = getattr(asset, 'id', '')
            for threat in self.threats:
                if getattr(threat, 'target_asset_id', '') != asset_id:
                    continue
                threat_id = getattr(threat, 'id', '')
                for system in self.upper_systems:
                    system_id = getattr(system, 'id', '')
                    key = (asset_id, threat_id, system_id)
                    if key not in self.variables['x_upper']:
                        continue

                    x_var = self.variables['x_upper'][key]
                    system_obj = next((s for s in self.interceptor_systems if s.id == system_id), None)
                    K_ij = _get_k_constant(threat_id, system_id, threat, system_obj)
                    P_total = _get_p_total(threat_id, system_id, 0.85)
                    kP = K_ij * P_total

                    # K_ij 상수 저장 (보고용)
                    self.k_constants[key] = K_ij

                    w_var = pulp.LpVariable(
                        f"w_u_{asset_id}_{threat_id}_{system_id}",
                        lowBound=0, upBound=kP
                    )
                    self.mccormick_variables['w_upper'][key] = w_var

                    # w = K_ij * P * x  (선형 등식, 2개 부등식으로 표현)
                    upper_constraints.append((f"w_upper_lb_{key}", w_var >= kP * x_var))
                    upper_constraints.append((f"w_upper_ub_{key}", w_var <= kP * x_var))

        for name, con in upper_constraints:
            self.model.constraints[name] = con

        # 하층 시스템
        self.mccormick_variables['w_lower'] = {}
        lower_constraints = []

        for asset in self.assets:
            asset_id = getattr(asset, 'id', '')
            for threat in self.threats:
                if getattr(threat, 'target_asset_id', '') != asset_id:
                    continue
                threat_id = getattr(threat, 'id', '')
                for system in self.lower_systems:
                    system_id = getattr(system, 'id', '')
                    key = (asset_id, threat_id, system_id)
                    if key not in self.variables['x_lower']:
                        continue

                    x_var = self.variables['x_lower'][key]
                    system_obj = next((s for s in self.interceptor_systems if s.id == system_id), None)
                    K_ij = _get_k_constant(threat_id, system_id, threat, system_obj)
                    P_total = _get_p_total(threat_id, system_id, 0.78)
                    kP = K_ij * P_total

                    self.k_constants[key] = K_ij

                    w_var = pulp.LpVariable(
                        f"w_l_{asset_id}_{threat_id}_{system_id}",
                        lowBound=0, upBound=kP
                    )
                    self.mccormick_variables['w_lower'][key] = w_var

                    lower_constraints.append((f"w_lower_lb_{key}", w_var >= kP * x_var))
                    lower_constraints.append((f"w_lower_ub_{key}", w_var <= kP * x_var))

        for name, con in lower_constraints:
            self.model.constraints[name] = con
    
    def _create_survival_probability_variables(self):
        """생존 확률 변수 생성: s_u = (1 - w_u), s_l = (1 - w_l)"""
        
        self.mccormick_variables['s_upper'] = {}
        self.mccormick_variables['s_lower'] = {}
        
        # 상층 생존 확률: s_u = 1 - w_u
        for key, w_var in self.mccormick_variables['w_upper'].items():
            s_var = pulp.LpVariable(f"s_u_{key[0]}_{key[1]}_{key[2]}", lowBound=0, upBound=1)
            self.mccormick_variables['s_upper'][key] = s_var
            self.model.constraints[f"s_upper_{key[0]}_{key[1]}_{key[2]}"] = (s_var == 1 - w_var)
        
        # 하층 생존 확률: s_l = 1 - w_l  
        for key, w_var in self.mccormick_variables['w_lower'].items():
            s_var = pulp.LpVariable(f"s_l_{key[0]}_{key[1]}_{key[2]}", lowBound=0, upBound=1)
            self.mccormick_variables['s_lower'][key] = s_var
            self.model.constraints[f"s_lower_{key[0]}_{key[1]}_{key[2]}"] = (s_var == 1 - w_var)
    
    def _linearize_asset_survival_probability(self):
        """자산별 총 생존 확률 선형화: Π (s_u) * Π (s_l)
        최적화: 상층/하층 시스템이 같은 자산/위협에 할당된 경우를 효율적으로 처리
        """
        
        self.mccormick_variables['asset_survival'] = {}
        
        for asset in self.assets:
            # 해당 자산을 위협하는 미사일들 찾기
            asset_threats = [t for t in self.threats if getattr(t, 'target_asset_id', '') == getattr(asset, 'id', '')]
            
            if not asset_threats:
                continue
            
            # 🆕 중복 제거: engagement_matrix는 이미 create_model에서 생성됨
            # (Line 542-546 제거 - 불필요한 재생성 방지)
            
            # 각 위협에 대한 생존 확률 변수들 통합 수집 (상층/하층 구분 없이)
            all_survival_vars = []
            
            # 🔍 디버깅: 변수 수집 과정 추적
            debug_s_upper_count = 0
            debug_s_lower_count = 0
            
            for threat in asset_threats:
                # 상층 시스템들의 생존 확률
                for system in self.upper_systems:
                    key = (getattr(asset, 'id', ''), getattr(threat, 'id', ''), getattr(system, 'id', ''))
                    if key in self.mccormick_variables['s_upper']:
                        all_survival_vars.append(self.mccormick_variables['s_upper'][key])
                        debug_s_upper_count += 1
                
                # 하층 시스템들의 생존 확률
                for system in self.lower_systems:
                    key = (getattr(asset, 'id', ''), getattr(threat, 'id', ''), getattr(system, 'id', ''))
                    if key in self.mccormick_variables['s_lower']:
                        all_survival_vars.append(self.mccormick_variables['s_lower'][key])
                        debug_s_lower_count += 1
            
            # 🔍 디버깅: 수집 결과 출력
            if len(all_survival_vars) == 0:
                print(f"[DEBUG] Asset {getattr(asset, 'id', '')}: No survival vars! "
                      f"Threats={len(asset_threats)}, "
                      f"s_upper_found={debug_s_upper_count}, s_lower_found={debug_s_lower_count}, "
                      f"Total s_upper={len(self.mccormick_variables.get('s_upper', {}))}, "
                      f"Total s_lower={len(self.mccormick_variables.get('s_lower', {}))}")
            
            # 모든 생존 확률의 곱을 한 번에 계산 (계층 구조 최적화)
            if all_survival_vars:
                # 🆕 Binary Tree 통계 출력
                n_vars = len(all_survival_vars)
                tree_depth = self.binary_tree_cache.get_tree_depth(n_vars)
                mccormick_count = self.binary_tree_cache.get_mccormick_count(n_vars)
                
                # 이진 트리 형태로 곱 계산 (로그 깊이)
                asset_survival_var = self._create_product_variable(
                    all_survival_vars, f"asset_survival_{getattr(asset, 'id', '')}"
                )
            else:
                # [NOTE] 할당 가능한 시스템이 없으면 생존 확률 = 0 (100% 손실)
                asset_survival_var = pulp.LpVariable(f"asset_survival_{getattr(asset, 'id', '')}", lowBound=0, upBound=0)
                self.model.constraints[f"asset_survival_{getattr(asset, 'id', '')}_zero"] = (asset_survival_var == 0)
            
            # 최종 자산 생존 확률 저장
            self.mccormick_variables['asset_survival'][getattr(asset, 'id', '')] = asset_survival_var
        
        # print(f"Asset survival variables: {len(self.mccormick_variables['asset_survival'])}")  # 비활성화
    
    def _apply_fbbt(self):
        """FBBT (Feasibility-Based Bound Tightening) 적용
        
        교전 불가능한 변수를 0으로 고정하여 탐색 공간을 지수적으로 감소시킴.
        비트마스크 대신 if문 사용 - Python에서는 분기 예측이 더 효율적.
        """
        fixed_count = 0
        current_time = getattr(self, 'current_time', 0.0)
        
        # 상층 시스템 변수 FBBT
        for key, x_var in self.variables.get('x_upper', {}).items():
            asset_id, threat_id, system_id = key
            
            # 이미 고정된 변수는 스킵
            if x_var.upBound == 0:
                continue
            
            should_fix = False
            
            # 조건 1: 거리 제약 (engagement_matrix_cache 사용)
            if self.engagement_matrix_cache:
                # 위협 현재 위치 가져오기
                threat = next((t for t in self.threats if getattr(t, 'id', '') == threat_id), None)
                if threat:
                    threat_pos = getattr(threat, 'current_position', None)
                    battery_specs = None
                    for bat in self.batteries:
                        if bat['id'] == system_id:
                            battery_specs = bat.get('specs')
                            break
                    
                    if threat_pos and battery_specs:
                        is_feasible = self.engagement_matrix_cache.is_feasible(
                            system_id, threat_id,
                            threat_current_position=threat_pos,
                            battery_specs=battery_specs
                        )
                        if not is_feasible:
                            should_fix = True
            
            # 조건 2: 탄약 부족 (포대별 잔여 미사일 < 2)
            if not should_fix:
                for battery in self.batteries:
                    if battery['id'] == system_id:
                        available = battery.get('available_missiles', battery.get('specs', {}).get('battery_config', {}).get('total_missiles', 999))
                        if available < self.missiles_per_engagement:
                            should_fix = True
                        break
            
            # 변수 고정
            if should_fix:
                x_var.upBound = 0
                x_var.lowBound = 0
                fixed_count += 1
        
        # 하층 시스템 변수 FBBT (동일 로직)
        for key, x_var in self.variables.get('x_lower', {}).items():
            asset_id, threat_id, system_id = key
            
            if x_var.upBound == 0:
                continue
            
            should_fix = False
            
            if self.engagement_matrix_cache:
                threat = next((t for t in self.threats if getattr(t, 'id', '') == threat_id), None)
                if threat:
                    threat_pos = getattr(threat, 'current_position', None)
                    battery_specs = None
                    for bat in self.batteries:
                        if bat['id'] == system_id:
                            battery_specs = bat.get('specs')
                            break
                    
                    if threat_pos and battery_specs:
                        is_feasible = self.engagement_matrix_cache.is_feasible(
                            system_id, threat_id,
                            threat_current_position=threat_pos,
                            battery_specs=battery_specs
                        )
                        if not is_feasible:
                            should_fix = True
            
            if not should_fix:
                for battery in self.batteries:
                    if battery['id'] == system_id:
                        available = battery.get('available_missiles', battery.get('specs', {}).get('battery_config', {}).get('total_missiles', 999))
                        if available < self.missiles_per_engagement:
                            should_fix = True
                        break
            
            if should_fix:
                x_var.upBound = 0
                x_var.lowBound = 0
                fixed_count += 1
        
        if fixed_count > 0:
            total_vars = len(self.variables.get('x_upper', {})) + len(self.variables.get('x_lower', {}))
            reduction_pct = (fixed_count / total_vars * 100) if total_vars > 0 else 0
            print(f"[FBBT] Fixed {fixed_count}/{total_vars} variables to zero ({reduction_pct:.1f}% reduction)")
        
        return fixed_count
    
    def _set_linearized_objective(self):
        """목적함수: min Σ v_i · S_i  (논문 식 (1) 직접 대응: 기대 위험 손실 최소화)

        S_i = asset_survival[i] = Π_j(1 - w_ij) ∈ [0,1]: 자산 i 위협 생존확률
        v_i: 자산 가치.  Z* > 0, 낮을수록 방어 효과 높음.
        """
        objective_terms = []
        asset_value_map = {getattr(a, 'id', ''): getattr(a, 'value', 1) for a in self.assets}

        for asset_id, survival_var in self.mccormick_variables.get('asset_survival', {}).items():
            v = asset_value_map.get(asset_id, 1)
            objective_terms.append(v * survival_var)

        if objective_terms:
            self.model.setObjective(pulp.lpSum(objective_terms))
            print(f"Objective function: {len(objective_terms)} asset-survival terms (minimize expected loss)")
        else:
            self.model.setObjective(0)

    def _add_basic_constraints(self):
        
        # 🔧 변수가 없으면 제약 조건 추가 건너뛰기 (무한 대기 방지)
        if not self.variables.get('x_upper') and not self.variables.get('x_lower'):
            print("[WARNING] No decision variables created - skipping constraint addition")
            return
        
        # 제약조건 1+2: 조건부 다층 방어 제약 (상층과 하층 모두 가능한 경우에만 강제)
        constraint_counter = 0  # 고유 제약 이름 생성용
        
        # ⚡ 성능 최적화: 제약 조건 리스트에 모아서 일괄 추가
        constraints_to_add = []
        
        for asset in self.assets:
            asset_id = getattr(asset, 'id', '')  # 한 번만 호출
            for threat in self.threats:
                threat_target = getattr(threat, 'target_asset_id', '')  # 한 번만 호출
                if threat_target == asset_id:
                    threat_id = getattr(threat, 'id', '')  # 한 번만 호출
                    upper_assignments = []
                    lower_assignments = []
                    
                    # 상층 할당 변수 수집
                    for system in self.upper_systems:
                        system_id = getattr(system, 'id', '')  # 한 번만 호출
                        key = (asset_id, threat_id, system_id)
                        if key in self.variables['x_upper']:
                            upper_assignments.append(self.variables['x_upper'][key])
                    
                    # 하층 할당 변수 수집
                    for system in self.lower_systems:
                        system_id = getattr(system, 'id', '')  # 한 번만 호출
                        key = (asset_id, threat_id, system_id)
                        if key in self.variables['x_lower']:
                            lower_assignments.append(self.variables['x_lower'][key])
                    
                    # 다층 방어 제약: 용량 허용 범위 내에서 최대한 할당 (목적함수가 유도)
                    # 강제 할당(>=1) 제약 제거: 동시 위협 수 > 포대 용량 시 infeasible 방지
                    if upper_assignments or lower_assignments:
                        upper_available = len(upper_assignments) > 0
                        lower_available = len(lower_assignments) > 0

                        # 같은 위협에 상층+하층 동시 할당 금지 (SLS: 한 계층만 교전)
                        if upper_available and lower_available:
                            constraint_counter += 1
                            constraints_to_add.append((
                                f"LayerExclusive_{asset_id}_{threat_id}_{constraint_counter}",
                                pulp.lpSum(upper_assignments) + pulp.lpSum(lower_assignments) <= 1
                            ))

                        # 계층별 최대 1개 포대만 할당 (중복 방지)
                        if upper_assignments:
                            constraint_counter += 1
                            constraints_to_add.append((
                                f"MaxUpper_{asset_id}_{threat_id}_{constraint_counter}",
                                pulp.lpSum(upper_assignments) <= 1
                            ))
                        if lower_assignments:
                            constraint_counter += 1
                            constraints_to_add.append((
                                f"MaxLower_{asset_id}_{threat_id}_{constraint_counter}",
                                pulp.lpSum(lower_assignments) <= 1
                            ))
        
        # 제약조건 3: 상층 요격체계 용량 제한 (미사일 수 기반)
        for system in self.upper_systems:
            system_id = getattr(system, 'id', '')  # 한 번만 호출
            available_missiles = getattr(system, 'available_missiles', 10)  # 한 번만 호출
            total_engagements = []
            for asset in self.assets:
                asset_id = getattr(asset, 'id', '')  # 한 번만 호출
                for threat in self.threats:
                    threat_target = getattr(threat, 'target_asset_id', '')  # 한 번만 호출
                    if threat_target == asset_id:
                        threat_id = getattr(threat, 'id', '')  # 한 번만 호출
                        key = (asset_id, threat_id, system_id)
                        if key in self.variables['x_upper']:
                            total_engagements.append(self.variables['x_upper'][key])
            
            if total_engagements:
                # 각 교전당 2발 사용, 총 미사일 수 제한
                total_missiles_needed = pulp.lpSum(total_engagements) * self.missiles_per_engagement
                constraints_to_add.append((
                    f"Capacity_upper_{system_id}",
                    total_missiles_needed <= available_missiles
                ))
        
        # 제약조건 4: 하층 요격체계 용량 제한 (미사일 수 기반)
        for system in self.lower_systems:
            system_id = getattr(system, 'id', '')  # 한 번만 호출
            available_missiles = getattr(system, 'available_missiles', 10)  # 한 번만 호출
            total_engagements = []
            for asset in self.assets:
                asset_id = getattr(asset, 'id', '')  # 한 번만 호출
                for threat in self.threats:
                    threat_target = getattr(threat, 'target_asset_id', '')  # 한 번만 호출
                    if threat_target == asset_id:
                        threat_id = getattr(threat, 'id', '')  # 한 번만 호출
                        key = (asset_id, threat_id, system_id)
                        if key in self.variables['x_lower']:
                            total_engagements.append(self.variables['x_lower'][key])
            
            if total_engagements:
                # 각 교전당 2발 사용, 총 미사일 수 제한
                total_missiles_needed = pulp.lpSum(total_engagements) * self.missiles_per_engagement
                constraints_to_add.append((
                    f"Capacity_lower_{system_id}",
                    total_missiles_needed <= available_missiles
                ))
        
        # ⚡ 성능 최적화: 제약 조건 일괄 추가
        for name, constraint in constraints_to_add:
            self.model += constraint, name
        
        # 추가 제약조건: k는 x가 1일 때만 의미 있음 (x=0이면 k 값 무관)
        # 하지만 McCormick 선형화에서 이미 처리되므로 추가 제약 불필요
        
        print("Added all basic constraints")
    
    def _add_capacity_constraints(self):
        """용량 제약조건들 추가"""
        
        # 각 시스템의 총 미사일 수 제한 (이미 _add_basic_constraints에서 처리됨)
        pass
    
    def _add_launcher_exclusivity_constraints(self):
        """발사대 단독 할당 제약조건 추가 (선택적)"""
        
        # 발사대 단독 할당이 비활성화되어 있으면 다중 할당 허용
        if not self.enable_launcher_exclusivity:
            print("Launcher exclusivity constraints disabled - allowing multiple target assignments per system")
            return
        
        # 각 시스템은 한 번에 하나의 표적에만 교전 가능 (활성화 시)
        for system in self.upper_systems:
            total_assignments = pulp.lpSum([
                self.variables['x_upper'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), getattr(system, 'id', '')), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ])
            self.model += total_assignments <= 1
        
        for system in self.lower_systems:
            total_assignments = pulp.lpSum([
                self.variables['x_lower'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), getattr(system, 'id', '')), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ])
            self.model += total_assignments <= 1
    
    def _add_target_engagement_limits(self):
        """표적당 최대 교전 횟수 제약조건 추가"""
        
        for threat in self.threats:
            threat_id = getattr(threat, 'id', '')
            target_asset_id = getattr(threat, 'target_asset_id', '')
            
            # 🆕 제약 1: 표적별 동시 교전 금지 - 한 표적에 한 번에 하나의 배터리만
            total_concurrent_engagements = pulp.lpSum([
                self.variables['x_upper'].get((getattr(asset, 'id', ''), threat_id, getattr(system, 'id', '')), 0)
                for asset in self.assets
                for system in self.upper_systems
                if getattr(asset, 'id', '') == target_asset_id
            ]) + pulp.lpSum([
                self.variables['x_lower'].get((getattr(asset, 'id', ''), threat_id, getattr(system, 'id', '')), 0)
                for asset in self.assets
                for system in self.lower_systems
                if getattr(asset, 'id', '') == target_asset_id
            ])
            
            # 🆕 다층 방어 지원: 한 표적에 최대 2개 배터리 (상층 1개 + 하층 1개)
            self.model += total_concurrent_engagements <= 2, f"Multi_Layer_Defense_{threat_id}"
    
    def _add_battery_simultaneous_engagement_limits(self):
        """포대별 동시 교전 능력 제약조건 추가"""
        
        for battery in self.batteries:
            battery_id = battery["id"]
            specs = battery["specs"]
            
            # 포대 설정에서 동시 교전 능력 확인
            max_simultaneous = specs["battery_config"]["simultaneous_engagements"]
            
            # 해당 포대의 동시 교전 수 제한
            total_simultaneous = pulp.lpSum([
                self.variables['x_upper'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), battery_id), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ]) + pulp.lpSum([
                self.variables['x_lower'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), battery_id), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ])
            
            self.model += total_simultaneous <= max_simultaneous
    
    def _set_linearized_objective(self):
        """목적함수: min Σ v_i · S_i  (논문 식 (1) 직접 대응: 기대 위험 손실 최소화)

        S_i = asset_survival[i] = Π_j(1 - w_ij) ∈ [0,1]: 자산 i 위협 생존확률
        v_i: 자산 가치.  Z* > 0, 낮을수록 방어 효과 높음.
        """
        objective_terms = []
        asset_value_map = {getattr(a, 'id', ''): getattr(a, 'value', 1) for a in self.assets}

        for asset_id, survival_var in self.mccormick_variables.get('asset_survival', {}).items():
            v = asset_value_map.get(asset_id, 1)
            objective_terms.append(v * survival_var)

        if objective_terms:
            self.model.setObjective(pulp.lpSum(objective_terms))
            print(f"Objective function: {len(objective_terms)} asset-survival terms (minimize expected loss)")
        else:
            self.model.setObjective(0)

    def _add_original_constraints(self):
        """원래 제약조건들 + 현실적 운영 제약조건들 추가"""
        
        # 기존 제약조건들
        self._add_basic_constraints()
        
        # 현실적 운영 제약조건들
        if self.enable_capacity_constraints:
            self._add_capacity_constraints()
        
        if self.enable_launcher_exclusivity:
            self._add_launcher_exclusivity_constraints()
        
        self._add_target_engagement_limits()
        self._add_battery_simultaneous_engagement_limits()

        print("Added all original and realistic operational constraints")

    def _add_original_constraints(self):
        """원래 제약조건들 + 현실적 운영 제약조건들 추가"""
        
        # 기존 제약조건들
        self._add_basic_constraints()
        
        # 현실적 운영 제약조건들
        if self.enable_capacity_constraints:
            self._add_capacity_constraints()
        
        if self.enable_launcher_exclusivity:
            self._add_launcher_exclusivity_constraints()
        
        self._add_target_engagement_limits()
        self._add_battery_simultaneous_engagement_limits()

        print("Added all original and realistic operational constraints")

    def _add_capacity_constraints(self):
        """용량 제약조건들 추가"""
        
        # 각 시스템의 총 미사일 수 제한 (이미 _add_basic_constraints에서 처리됨)
        pass
    
    def _add_launcher_exclusivity_constraints(self):
        """발사대 단독 할당 제약조건 추가 (선택적)"""
        
        # 발사대 단독 할당이 비활성화되어 있으면 다중 할당 허용
        if not self.enable_launcher_exclusivity:
            print("Launcher exclusivity constraints disabled - allowing multiple target assignments per system")
            return
        
        # 각 시스템은 한 번에 하나의 표적에만 교전 가능 (활성화 시)
        for system in self.upper_systems:
            total_assignments = pulp.lpSum([
                self.variables['x_upper'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), getattr(system, 'id', '')), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ])
            self.model += total_assignments <= 1
        
        for system in self.lower_systems:
            total_assignments = pulp.lpSum([
                self.variables['x_lower'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), getattr(system, 'id', '')), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ])
            self.model += total_assignments <= 1
    
    def _add_target_engagement_limits(self):
        """표적당 최대 교전 횟수 제약조건 추가"""
        
        for threat in self.threats:
            threat_id = getattr(threat, 'id', '')
            target_asset_id = getattr(threat, 'target_asset_id', '')
            
            # 🆕 제약 1: 표적별 동시 교전 금지 - 한 표적에 한 번에 하나의 배터리만
            total_concurrent_engagements = pulp.lpSum([
                self.variables['x_upper'].get((getattr(asset, 'id', ''), threat_id, getattr(system, 'id', '')), 0)
                for asset in self.assets
                for system in self.upper_systems
                if getattr(asset, 'id', '') == target_asset_id
            ]) + pulp.lpSum([
                self.variables['x_lower'].get((getattr(asset, 'id', ''), threat_id, getattr(system, 'id', '')), 0)
                for asset in self.assets
                for system in self.lower_systems
                if getattr(asset, 'id', '') == target_asset_id
            ])
            
            # 🆕 다층 방어 지원: 한 표적에 최대 2개 배터리 (상층 1개 + 하층 1개)
            self.model += total_concurrent_engagements <= 2, f"Multi_Layer_Defense_{threat_id}"
    
    def _add_battery_simultaneous_engagement_limits(self):
        """포대별 동시 교전 능력 제약조건 추가"""
        
        for battery in self.batteries:
            battery_id = battery["id"]
            specs = battery["specs"]
            
            # 포대 설정에서 동시 교전 능력 확인
            max_simultaneous = specs["battery_config"]["simultaneous_engagements"]
            
            # 해당 포대의 동시 교전 수 제한
            total_simultaneous = pulp.lpSum([
                self.variables['x_upper'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), battery_id), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ]) + pulp.lpSum([
                self.variables['x_lower'].get((getattr(asset, 'id', ''), getattr(threat, 'id', ''), battery_id), 0)
                for asset in self.assets
                for threat in self.threats
                if getattr(threat, 'target_asset_id', '') == getattr(asset, 'id', '')
            ])
            
            self.model += total_simultaneous <= max_simultaneous
    
    def _set_linearized_objective(self):
        """목적함수: min Σ v_i · S_i  (논문 식 (1) 직접 대응: 기대 위험 손실 최소화)

        S_i = asset_survival[i] = Π_j(1 - w_ij) ∈ [0,1]: 자산 i 위협 생존확률
        v_i: 자산 가치.  Z* > 0, 낮을수록 방어 효과 높음.
        """
        objective_terms = []
        asset_value_map = {getattr(a, 'id', ''): getattr(a, 'value', 1) for a in self.assets}

        for asset_id, survival_var in self.mccormick_variables.get('asset_survival', {}).items():
            v = asset_value_map.get(asset_id, 1)
            objective_terms.append(v * survival_var)

        if objective_terms:
            self.model.setObjective(pulp.lpSum(objective_terms))
            print(f"Objective function: {len(objective_terms)} asset-survival terms (minimize expected loss)")
        else:
            self.model.setObjective(0)
    
    def solve(self) -> Dict:
        """모델 해결 - 최적화된 버전"""
        
        if not self.model:
            raise ValueError("Model not created. Call create_model() first.")
        
        # print("Solving non-linear MIP model...")
        start_time = time.time()
        
        # 모델 전처리 - 변수 개수와 제약조건 정보 출력
        num_variables = self.model.numVariables()
        num_constraints = len(self.model.constraints)
        # print(f"Model size: {num_variables} variables, {num_constraints} constraints")
        
        # 🆕 최적화: Config 기반 solver 설정 사용 (GUI 응답성 우선)
        # MIP는 전역 최적해를 찾아야 GA보다 우수함
        solver_config = self.config.solver_config
        time_limit = solver_config.time_limit_sec
        gap_tolerance = solver_config.gap_tolerance
        threads = solver_config.threads
        verbose = 1 if solver_config.verbose else 0
        
        # 🚀 최적화된 Solver 설정 (단일 통합 설정)
        solver_options = [
            'presolve on',
            'cuts aggressive',      # moderate → aggressive (더 빠른 분기한계)
            'heuristics on',
            'gomory on',            # Gomory cuts 활성화
            'clique on'             # Clique cuts 활성화
        ]
        
        # Warm-start 활성화 시 mipstart 추가
        if self.use_warm_start and self.previous_solution:
            solver_options.append('mipstart on')
        
        # Root Node Gap 측정: CBC 로그 파일 경로 설정 (capture_root_gap=True 시)
        import os as _os, tempfile as _tempfile, re as _re
        _log_path = None
        if self.capture_root_gap:
            _log_path = _tempfile.mktemp(suffix='_cbc.log')

        # 최적화된 단일 Solver 설정
        solver = pulp.PULP_CBC_CMD(
            msg=1 if self.capture_root_gap else 0,
            timeLimit=5,
            gapRel=0.01,
            threads=4,
            options=solver_options,
            **({"logPath": _log_path} if _log_path else {})
        )

        # 🆕 Warm-start 적용
        if self.use_warm_start and self.previous_solution:
            self._apply_warm_start()

        # 솔버 실행
        self.model.solve(solver)
        solve_time = time.time() - start_time

        # Root Node Gap 파싱 (CBC 로그: "Continuous objective value is X")
        _z_lp_root = None
        if _log_path and _os.path.exists(_log_path):
            try:
                with open(_log_path) as _f:
                    for _line in _f:
                        # CBC 형식: "Continuous objective value is X - ..."
                        _m = _re.search(r'Continuous objective value is\s*([-\d.eE+]+)', _line)
                        if _m:
                            _z_lp_root = float(_m.group(1))
                            break
            except Exception:
                pass
            finally:
                try:
                    _os.remove(_log_path)
                except Exception:
                    pass
        
        # 결과 분석
        feasible = self.model.status == pulp.LpStatusOptimal
        objective_value = self.model.objective.value() if feasible and self.model.objective else float('inf')
        
        if objective_value is None:
            objective_value = float('inf')
        
        # 진단 정보 수집
        total_missiles = sum(b.get('available_missiles', 0) for b in self.batteries)
        feasible_engagements = sum(1 for v in self.engagement_matrix.values() if v) if self.engagement_matrix else 0
        
        # 🆕 포대별 할당 수 계산 (constraint 문제 진단용)
        battery_assignment_counts = {}
        if feasible:
            for battery in self.batteries:
                battery_id = battery["id"]
                count = 0
                # x_upper 변수 확인
                for key, var in self.variables['x_upper'].items():
                    if key[2] == battery_id and var.value() and var.value() > 0.5:
                        count += 1
                # x_lower 변수 확인
                for key, var in self.variables['x_lower'].items():
                    if key[2] == battery_id and var.value() and var.value() > 0.5:
                        count += 1
                battery_assignment_counts[battery_id] = count
        
        # solver_config 가져오기 (config에서)
        time_limit = getattr(self.config, 'solver_config', None)
        if time_limit:
            time_limit_sec = getattr(time_limit, 'time_limit_sec', 5)
        else:
            time_limit_sec = 5  # 기본값
        
        # 🆕 Warm-start 정보 추출
        warmstart_applied = False
        warmstart_count = 0
        if hasattr(self, 'warmstart_stats'):
            warmstart_applied = self.warmstart_stats.get('applied', False)
            warmstart_count = self.warmstart_stats.get('count', 0)
        
        # Root Node Gap 계산 (공식: |Z* - Z_LP_root| / (|Z*| + ε))
        _EPS = 1e-10
        _root_gap_pct = None
        if _z_lp_root is not None and objective_value not in (float('inf'), None) and abs(objective_value) > 1e-9:
            _root_gap_pct = abs(_z_lp_root - objective_value) / (abs(objective_value) + _EPS) * 100.0

        result = {
            'feasible': feasible,
            'objective_value': objective_value,
            'solve_time': solve_time,
            'status': pulp.LpStatus[self.model.status],
            'warmstart_applied': warmstart_applied,
            'warmstart_count': warmstart_count,
            'root_node_gap_pct': _root_gap_pct,   # Root Node Gap (%) — None이면 미측정
            'z_lp_root': _z_lp_root,               # LP 완화 목적함수값
            'diagnosis': {
                'solver_status': pulp.LpStatus[self.model.status],
                'num_variables': len(self.model.variables()),
                'num_constraints': len(self.model.constraints),
                'num_threats': len(self.threats),
                'num_systems': len(self.upper_systems) + len(self.lower_systems),
                'total_missiles': total_missiles,
                'time_limit_reached': solve_time >= time_limit_sec * 0.95,
                'feasible_engagements': feasible_engagements,
                'battery_assignments': battery_assignment_counts
            }
        }
        
        if feasible:
            # 할당 결과 추출
            result['upper_assignments'] = self._extract_assignments('x_upper')
            result['lower_assignments'] = self._extract_assignments('x_lower')
            result['upper_k_values'] = self._extract_k_values('x_upper')
            result['lower_k_values'] = self._extract_k_values('x_lower')
            result['asset_survival_probs'] = self._extract_survival_probabilities()

            # Backward compatibility: 기존 코드 호환성을 위한 missiles 정보 제공
            result['upper_missiles'] = self._extract_missiles('x_upper')
            result['lower_missiles'] = self._extract_missiles('x_lower')
        
        # print(f"Model solved in {solve_time:.3f}s | Feasible: {feasible} | Objective: {objective_value:.6f}")
        
        # 🆕 Warm-start: 현재 해 저장 (다음 타임스텝용)
        if feasible and self.use_warm_start:
            self._save_solution_for_warmstart(result)
        
        return result
    
    def _extract_assignments(self, var_type: str) -> Dict:
        """할당 결과 추출 with detailed LSAM tracking"""
        assignments = {}
        
        # LSAM 변수 상세 추적 (첫 번째 호출에서만 출력)
        if var_type == 'x_upper':
            print("\n=== LSAM VARIABLE VALUES ===")
            lsam_variables_found = 0
            lsam_variables_selected = 0
            
            # 상층 시스템 할당 추출
            for (asset_id, threat_id, system_id), var in self.variables['x_upper'].items():
                var_value = var.value() if var.value() is not None else 0
                
                # LSAM 변수 추적
                if 'LSAM' in system_id:
                    lsam_variables_found += 1
                    print(f"LSAM Variable: {system_id} -> {threat_id} (Asset: {asset_id}) = {var_value}")
                    if var_value > 0.5:
                        lsam_variables_selected += 1
                        print(f"  *** LSAM SELECTED: {system_id} assigned to {threat_id} ***")
                
                if var_value > 0.5:
                    key = f"{asset_id}_{threat_id}"
                    assignments[key] = system_id
            
            print(f"LSAM Summary: {lsam_variables_found} variables created, {lsam_variables_selected} selected")
            print(f"Upper assignments extracted: {len(assignments)}")
            
        elif var_type == 'x_lower':
            # 하층 시스템 할당 추출
            for (asset_id, threat_id, system_id), var in self.variables['x_lower'].items():
                var_value = var.value() if var.value() is not None else 0
                if var_value > 0.5:
                    key = f"{asset_id}_{threat_id}"
                    assignments[key] = system_id
            
            print(f"Lower assignments extracted: {len(assignments)}")
        
        return assignments
    
    def _extract_k_values(self, var_type: str) -> Dict:
        """K 상수값 추출 (k_constants dict 기반)."""
        k_values = {}
        for key in self.variables[var_type]:
            if key in self.k_constants:
                asset_id, threat_id, system_id = key
                k_values[f"{asset_id}_{threat_id}_{system_id}"] = round(self.k_constants[key], 4)
        return k_values

    def _extract_missiles(self, var_type: str) -> Dict:
        """Backward compatibility: 기존 코드 호환성을 위한 미사일 수 추출 (교전시 2발 고정)"""
        missiles = {}
        for key, var in self.variables[var_type].items():
            if var.value() and var.value() > 0.5:
                asset_id, threat_id, system_id = key
                missiles[f"{asset_id}_{threat_id}_{system_id}"] = self.missiles_per_engagement
        return missiles
    
    def _extract_survival_probabilities(self) -> Dict:
        """자산별 생존 확률 추출"""
        survival_probs = {}
        
        for asset_id, var in self.mccormick_variables['asset_survival'].items():
            if var.value() is not None:
                survival_probs[asset_id] = var.value()
        
        return survival_probs
    
    def _create_product_variable(self, variables_list, var_name):
        """Create a variable representing the product of a list of variables using McCormick relaxation.
        
        For a list of variables [v1, v2, ..., vn], creates intermediate variables to compute their product.
        Uses binary tree approach to minimize the number of McCormick constraints.
        
        🆕 최적화: Binary Tree로 O(log n) 깊이로 McCormick 적용
        - n개 변수 → n-1회 McCormick (최소)
        - 각 McCormick당 4개 제약 → 총 4(n-1)개 제약
        
        🔥 개선사항:
        - Bound Propagation: 정확한 bounds 계산으로 McCormick envelope 축소
        - Bound-Aware Grouping: tight한 변수부터 곱셈하여 효율 향상
        - 제약 추가 방식 통일: model.constraints[] 사용
        
        Args:
            variables_list: List of PuLP variables to multiply
            var_name: Base name for the product variable
            
        Returns:
            PuLP variable representing the product
        """
        if not variables_list:
            # Empty list - return constant 1
            result_var = pulp.LpVariable(f"{var_name}_empty", lowBound=1, upBound=1)
            self.model.constraints[f"{var_name}_empty_eq"] = (result_var == 1)
            return result_var
        
        if len(variables_list) == 1:
            # Single variable - return as is
            return variables_list[0]
        
        if len(variables_list) == 2:
            # Two variables - direct McCormick relaxation with tight bounds
            v1, v2 = variables_list
            
            # 🔥 OPTIMIZED: Bound Propagation - 정확한 bounds 계산
            # 타입 체크: 상수가 전달된 경우 처리
            if isinstance(v1, (int, float)):
                L1 = U1 = float(v1)
            else:
                L1 = v1.lowBound if v1.lowBound is not None else 0
                U1 = v1.upBound if v1.upBound is not None else 1
            
            if isinstance(v2, (int, float)):
                L2 = U2 = float(v2)
            else:
                L2 = v2.lowBound if v2.lowBound is not None else 0
                U2 = v2.upBound if v2.upBound is not None else 1
            
            # 곱셈의 정확한 bounds (생존 확률은 모두 양수)
            product_lower = L1 * L2
            product_upper = U1 * U2
            
            # 🔥 FIX: 상수 처리 - 둘 다 상수면 직접 계산
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                # 둘 다 상수 - 직접 곱셈 결과 반환
                return float(v1) * float(v2)
            
            product_var = pulp.LpVariable(
                f"{var_name}_prod",
                lowBound=product_lower,  # 개선: 정확한 하한
                upBound=product_upper    # 개선: 정확한 상한
            )
            
            # 🔥 FIX: McCormick constraints - 상수 처리
            # v1, v2가 상수일 경우 그 값을 직접 사용
            v1_expr = float(v1) if isinstance(v1, (int, float)) else v1
            v2_expr = float(v2) if isinstance(v2, (int, float)) else v2
            
            # McCormick constraints for product = v1 * v2
            # 제약 추가 방식 통일: model.constraints[] 사용
            self.model.constraints[f"{var_name}_mcc1"] = (product_var >= L2 * v1_expr + L1 * v2_expr - L1 * L2)
            self.model.constraints[f"{var_name}_mcc2"] = (product_var >= U2 * v1_expr + U1 * v2_expr - U1 * U2)
            self.model.constraints[f"{var_name}_mcc3"] = (product_var <= L2 * v1_expr + U1 * v2_expr - L2 * U1)
            self.model.constraints[f"{var_name}_mcc4"] = (product_var <= U2 * v1_expr + L1 * v2_expr - U2 * L1)
            
            return product_var
        
        # More than 2 variables - use binary tree approach with Huffman Tree optimization
        # 🔥 OPTIMIZED: Huffman Tree - 자산 가치 기반 정렬 (고가치 자산 우선)
        def get_asset_value_weight(v):
            """변수의 자산 가치 추출 (높은 가치 우선 - Huffman Tree)"""
            if isinstance(v, (int, float)):
                return 0.0  # 상수는 가중치 0
            
            # 변수 이름에서 asset_id 추출 시도
            var_name = getattr(v, 'name', '')
            if 'asset_survival_' in var_name:
                # asset_survival_A01 형태
                asset_id = var_name.split('_')[-1]
            elif '_A' in var_name:
                # s_upper_A01_T01_LSAM_01 형태
                parts = var_name.split('_')
                asset_id = next((p for p in parts if p.startswith('A') and len(p) <= 4), None)
            else:
                return 0.0
            
            # 자산 가치 조회
            if asset_id:
                for asset in self.assets:
                    if getattr(asset, 'id', '') == asset_id:
                        # 음수로 반환하여 내림차순 정렬 (높은 가치가 앞으로)
                        return -getattr(asset, 'value', 0)
            return 0.0
        
        sorted_vars = sorted(variables_list, key=get_asset_value_weight)
        
        mid = len(sorted_vars) // 2
        left_vars = sorted_vars[:mid]
        right_vars = sorted_vars[mid:]
        
        # Recursively create products for left and right halves
        left_product = self._create_product_variable(left_vars, f"{var_name}_left")
        right_product = self._create_product_variable(right_vars, f"{var_name}_right")
        
        # Create final product of the two halves
        return self._create_product_variable([left_product, right_product], var_name)


# 🆕 Warm-start 메서드 통합
if WARMSTART_AVAILABLE:
    NonLinearMIPOptimizer = add_warmstart_methods(NonLinearMIPOptimizer)
    
    # 🔧 CRITICAL: 기존 __init__ 래핑하여 Warm-start 자동 활성화
    original_init = NonLinearMIPOptimizer.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # Warm-start 엔진 자동 활성화
        if self.use_warm_start:
            self.enable_warmstart()
    
    NonLinearMIPOptimizer.__init__ = new_init


if __name__ == "__main__":
    print("=== Non-linear MIP Optimizer Test ===")
    
    # 기본 가용성 확인
    print(f"PuLP Available: {PULP_AVAILABLE}")
    
    if PULP_AVAILABLE:
        print("[SUCCESS] Non-linear MIP Optimizer ready for implementation")
    else:
        print("[ERROR] PuLP not available - install with: pip install pulp")