"""
Warm-Start Integration Layer
=============================
NonLinearMIPOptimizer에 Warm-Start 엔진 통합

사용법:
    optimizer = NonLinearMIPOptimizer(config)
    optimizer.enable_warmstart()  # Warm-start 활성화
    
    # 첫 실행
    optimizer.create_model(...)
    result1 = optimizer.solve()
    
    # 두 번째 실행 (warm-start 자동 적용)
    optimizer.create_model(...)
    result2 = optimizer.solve()  # 이전 해 활용
"""

import pulp
from typing import Dict, Set
from warmstart_core import WarmStartEngine


def add_warmstart_methods(optimizer_class):
    """NonLinearMIPOptimizer에 warm-start 메서드 추가"""
    
    def _apply_warm_start(self):
        """
        이전 타임스텝 해를 현재 변수에 매핑
        First-Principles 기반 계층적 초기화
        """
        if not hasattr(self, 'warmstart_engine'):
            return
        
        # 현재 상태 추출
        current_threats = {getattr(t, 'id', '') for t in self.threats}
        current_systems = {
            getattr(s, 'id', ''): getattr(s, 'available_missiles', 0)
            for s in self.upper_systems + self.lower_systems
        }
        
        # 초기값 계산
        initial_values = self.warmstart_engine.compute_initial_values(
            variables=self.variables,
            current_threats=current_threats,
            current_systems=current_systems,
            engagement_matrix=self.engagement_matrix_cache or self.engagement_matrix
        )
        
        # 변수에 초기값 설정
        warmstart_count = 0
        k_warmstart_count = 0
        
        # x 변수 초기화
        for key, value in initial_values.items():
            if value > 0:
                if key in self.variables.get('x_upper', {}):
                    var = self.variables['x_upper'][key]
                    # 🔥 FIX: FBBT로 고정된 변수는 스킵 (upBound=0)
                    if var.upBound == 0:
                        continue
                    var.setInitialValue(value)
                    warmstart_count += 1
                    
                    # 🔧 OPTIMIZED: k 변수에도 초기값 설정
                    if key in self.variables.get('k_upper', {}) and self.k_factor_cache is not None:
                        threat_id = key[1]  # (asset_id, threat_id, system_id)
                        system_id = key[2]
                        k_value = self.k_factor_cache.get_k_value(threat_id, system_id)
                        if k_value is not None:
                            self.variables['k_upper'][key].setInitialValue(k_value)
                            k_warmstart_count += 1
                    
                elif key in self.variables.get('x_lower', {}):
                    var = self.variables['x_lower'][key]
                    # 🔥 FIX: FBBT로 고정된 변수는 스킵 (upBound=0)
                    if var.upBound == 0:
                        continue
                    var.setInitialValue(value)
                    warmstart_count += 1
                    
                    # 🔧 OPTIMIZED: k 변수에도 초기값 설정
                    if key in self.variables.get('k_lower', {}) and self.k_factor_cache is not None:
                        threat_id = key[1]
                        system_id = key[2]
                        k_value = self.k_factor_cache.get_k_value(threat_id, system_id)
                        if k_value is not None:
                            self.variables['k_lower'][key].setInitialValue(k_value)
                            k_warmstart_count += 1
        
        # 통계 출력
        stats = self.warmstart_engine.get_statistics()
        print(f"🔥 Warm-start applied: {warmstart_count} x variables, {k_warmstart_count} k variables initialized")
        print(f"   Exact match: {stats['exact_match']}, New threats: {stats['new_threat']}, "
              f"Removed: {stats['threat_removed']}, Infeasible: {stats['infeasible']}")
        
        # 🆕 Warm-start 통계 저장 (GUI 표시용)
        self.warmstart_stats = {
            'applied': warmstart_count > 0,
            'count': warmstart_count + k_warmstart_count,
            'x_vars': warmstart_count,
            'k_vars': k_warmstart_count
        }
    
    def _save_solution_for_warmstart(self, result: Dict):
        """
        현재 해를 저장 (다음 타임스텝용)
        """
        if not hasattr(self, 'warmstart_engine'):
            return
        
        # 현재 상태 추출
        current_threats = {getattr(t, 'id', '') for t in self.threats}
        current_systems = {
            getattr(s, 'id', ''): getattr(s, 'available_missiles', 0)
            for s in self.upper_systems + self.lower_systems
        }
        
        # 할당 결과 추출
        upper_assignments = result.get('upper_assignments', {})
        lower_assignments = result.get('lower_assignments', {})
        
        # 🔧 CRITICAL: self.previous_solution 업데이트 (Warm-start 조건 만족)
        self.previous_solution = {
            'upper_assignments': upper_assignments,
            'lower_assignments': lower_assignments,
            'threats': current_threats,
            'systems_capacity': current_systems
        }
        
        # 상태 저장
        self.warmstart_engine.save_state(
            threats=current_threats,
            systems_capacity=current_systems,
            upper_assignments=upper_assignments,
            lower_assignments=lower_assignments,
            timestamp=self.current_time_step if hasattr(self, 'current_time_step') else 0
        )
    
    def enable_warmstart(self):
        """Warm-start 엔진 활성화"""
        self.warmstart_engine = WarmStartEngine()
        self.use_warm_start = True
        print("[OK] Warm-start engine enabled")
    
    def disable_warmstart(self):
        """Warm-start 비활성화"""
        if hasattr(self, 'warmstart_engine'):
            self.warmstart_engine.reset()
        self.use_warm_start = False
        print("[DISABLED] Warm-start engine disabled")
    
    def get_warmstart_stats(self) -> Dict:
        """Warm-start 통계 조회"""
        if hasattr(self, 'warmstart_engine'):
            return self.warmstart_engine.get_statistics()
        return {}
    
    # 메서드 추가
    optimizer_class._apply_warm_start = _apply_warm_start
    optimizer_class._save_solution_for_warmstart = _save_solution_for_warmstart
    optimizer_class.enable_warmstart = enable_warmstart
    optimizer_class.disable_warmstart = disable_warmstart
    optimizer_class.get_warmstart_stats = get_warmstart_stats
    
    return optimizer_class
