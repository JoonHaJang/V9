"""
Warm-Start Core Module - First Principles Implementation
=========================================================
근본부터 재설계한 DWTA Warm-Start 시스템

핵심 원리:
1. 상태 전이의 연속성 (State Transition Continuity)
2. 할당의 지속성 (Assignment Persistence)
3. 구조적 유사성 (Structural Similarity)
"""

from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class WarmStartState:
    """이전 타임스텝의 상태 스냅샷"""
    threats: Set[str]
    systems_capacity: Dict[str, int]
    upper_assignments: Dict[str, str]  # {asset_threat_key: system_id}
    lower_assignments: Dict[str, str]
    timestamp: int


class WarmStartEngine:
    """First-Principles Warm-Start 엔진"""
    
    def __init__(self):
        self.previous_state: Optional[WarmStartState] = None
        self.mapping_stats = {
            'exact_match': 0,
            'threat_removed': 0,
            'new_threat': 0,
            'capacity_changed': 0,
            'infeasible': 0
        }
    
    def compute_initial_values(
        self,
        variables: Dict,
        current_threats: Set[str],
        current_systems: Dict[str, int],
        engagement_matrix
    ) -> Dict[Tuple, float]:
        """
        변수별 초기값 계산 (First-Principles)
        
        매핑 우선순위:
        1. 완전 일치 (Exact Match): 이전 할당 그대로
        2. 위협 제거 (Threat Removed): 무시
        3. 신규 위협 (New Threat): 휴리스틱 초기화
        4. 용량 변경 (Capacity Changed): Feasibility 검증
        """
        initial_values = {}
        
        if not self.previous_state:
            # 첫 실행: 모든 변수 0으로 초기화
            for key in variables.keys():
                initial_values[key] = 0.0
            return initial_values
        
        # 통계 초기화
        for k in self.mapping_stats:
            self.mapping_stats[k] = 0
        
        # 상층 변수 매핑
        for key, var in variables.get('x_upper', {}).items():
            asset_id, threat_id, system_id = key
            mapping_key = f"{asset_id}_{threat_id}"
            
            initial_values[key] = self._map_variable(
                mapping_key,
                system_id,
                threat_id,
                current_threats,
                current_systems,
                self.previous_state.upper_assignments,
                engagement_matrix
            )
        
        # 하층 변수 매핑
        for key, var in variables.get('x_lower', {}).items():
            asset_id, threat_id, system_id = key
            mapping_key = f"{asset_id}_{threat_id}"
            
            initial_values[key] = self._map_variable(
                mapping_key,
                system_id,
                threat_id,
                current_threats,
                current_systems,
                self.previous_state.lower_assignments,
                engagement_matrix
            )
        
        return initial_values
    
    def _map_variable(
        self,
        mapping_key: str,
        system_id: str,
        threat_id: str,
        current_threats: Set[str],
        current_systems: Dict[str, int],
        previous_assignments: Dict[str, str],
        engagement_matrix
    ) -> float:
        """
        개별 변수 매핑 로직 (계층적 우선순위)
        
        Returns:
            1.0: 할당 (이전 해 활용)
            0.0: 미할당
        """
        # 우선순위 1: 완전 일치 (Exact Match)
        if mapping_key in previous_assignments:
            prev_system = previous_assignments[mapping_key]
            
            if prev_system == system_id:
                # 동일 할당 유지 가능한지 검증
                if self._is_assignment_feasible(
                    threat_id,
                    system_id,
                    current_threats,
                    current_systems,
                    engagement_matrix
                ):
                    self.mapping_stats['exact_match'] += 1
                    return 1.0  # 이전 할당 유지 - 강한 선호
                else:
                    self.mapping_stats['infeasible'] += 1
                    return 0.4  # 불가능하지만 완전히 버리지 않음
        
        # 우선순위 2: 위협 제거 (Threat Removed)
        if threat_id not in current_threats:
            self.mapping_stats['threat_removed'] += 1
            return 0.0  # 제거된 위협은 할당 불가
        
        # 우선순위 3: 신규 위협 (New Threat)
        if threat_id not in self.previous_state.threats:
            # 휴리스틱: 가장 가까운 시스템 선택 (거리 기반)
            # 현재는 단순화하여 첫 번째 feasible 시스템 선택
            if self._is_assignment_feasible(
                threat_id,
                system_id,
                current_threats,
                current_systems,
                engagement_matrix
            ):
                self.mapping_stats['new_threat'] += 1
                return 0.4  # 신규 위협 - 중립적 선호 (0.5→0.4로 약간 낮춤)
            return 0.0
        
        # 우선순위 4: 용량 변경 (Capacity Changed)
        prev_capacity = self.previous_state.systems_capacity.get(system_id, 0)
        curr_capacity = current_systems.get(system_id, 0)
        
        if prev_capacity != curr_capacity:
            self.mapping_stats['capacity_changed'] += 1
            # 용량 감소 시 재검증
            if self._is_assignment_feasible(
                threat_id,
                system_id,
                current_threats,
                current_systems,
                engagement_matrix
            ):
                return 0.4  # 용량 변경 - 중립적 선호 (0.5→0.4)
        
        # 기본값: 약한 선호 (완전히 0이 아님)
        return 0.3  # 최적화 여지 제공 (0.0→0.3)
    
    def _is_assignment_feasible(
        self,
        threat_id: str,
        system_id: str,
        current_threats: Set[str],
        current_systems: Dict[str, int],
        engagement_matrix
    ) -> bool:
        """할당 가능성 검증"""
        # 1. 위협 존재 여부
        if threat_id not in current_threats:
            return False
        
        # 2. 시스템 용량 (최소 2발 필요)
        if current_systems.get(system_id, 0) < 2:
            return False
        
        # 3. 교전 가능성
        if engagement_matrix:
            if hasattr(engagement_matrix, 'is_feasible'):
                return engagement_matrix.is_feasible(system_id, threat_id)
            else:
                return engagement_matrix.get((system_id, threat_id), False)
        
        return True
    
    def save_state(
        self,
        threats: Set[str],
        systems_capacity: Dict[str, int],
        upper_assignments: Dict[str, str],
        lower_assignments: Dict[str, str],
        timestamp: int
    ):
        """현재 상태 저장 (다음 타임스텝용)"""
        self.previous_state = WarmStartState(
            threats=threats.copy(),
            systems_capacity=systems_capacity.copy(),
            upper_assignments=upper_assignments.copy(),
            lower_assignments=lower_assignments.copy(),
            timestamp=timestamp
        )
    
    def get_statistics(self) -> Dict[str, int]:
        """Warm-start 매핑 통계"""
        return self.mapping_stats.copy()
    
    def reset(self):
        """상태 초기화"""
        self.previous_state = None
        for k in self.mapping_stats:
            self.mapping_stats[k] = 0
