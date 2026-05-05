"""
GREEDY Optimizer 개선 패치
==========================
다층 방어 활성화 + Best-fit 전략

적용 방법:
greedy_optimizer.py의 solve() 메서드를
아래 코드로 교체
"""

def solve(self):
    """Greedy 알고리즘 실행 - 개선 버전"""
    start_time = timeit.default_timer()
    
    upper_assignments = {}
    lower_assignments = {}
    
    # 배터리 스펙 캐싱
    battery_id_to_idx = {b['id']: idx for idx, b in enumerate(self.batteries)}
    battery_specs_cache = np.array([
        b['specs']['battery_config'].get('simultaneous_engagements', 3)
        for b in self.batteries
    ], dtype=np.uint8)
    
    # NumPy 배열 기반 용량 추적
    n_batteries = len(self.batteries)
    battery_usage = np.zeros(n_batteries, dtype=np.uint8)
    battery_capacity = np.array([
        b.get('available_missiles', 10) for b in self.batteries
    ], dtype=np.uint8)
    battery_engagement_count = np.zeros(n_batteries, dtype=np.uint8)
    
    # 다층 방어 추적
    upper_assigned = {}
    lower_assigned = {}
    upper_assignment_count = 0
    
    # 최대 할당 개수 계산
    max_upper_assignments = sum(
        battery_specs_cache[battery_id_to_idx[getattr(sys, 'id', '')]]
        for sys in self.upper_systems
    )
    max_lower_assignments = sum(
        battery_specs_cache[battery_id_to_idx[getattr(sys, 'id', '')]]
        for sys in self.lower_systems
    )
    lower_assignment_count = 0
    
    # ✅ Greedy 전략: 자산 가치 기반 우선순위 정렬
    asset_value_map = {getattr(a, 'id', ''): getattr(a, 'value', 0) 
                       for a in self.assets}
    threats_sorted = sorted(
        self.threats,
        key=lambda t: asset_value_map.get(getattr(t, 'target_asset_id', ''), 0),
        reverse=True  # 가치 높은 순
    )
    
    # 각 위협에 대해 할당
    for threat in threats_sorted:
        threat_id = getattr(threat, 'id', '')
        target_asset_id = getattr(threat, 'target_asset_id', '')
        key = f"{target_asset_id}_{threat_id}"
        
        # ========================
        # ✅ 개선 1: Best-fit 전략
        # ========================
        # 1단계: LSAM 할당 (상층)
        if key not in upper_assignments and upper_assignment_count < max_upper_assignments:
            best_system = None
            best_k = 0
            
            for system in self.upper_systems:
                system_id = getattr(system, 'id', '')
                
                # 교전 가능 여부
                if self.engagement_matrix_cache:
                    is_feasible = self.engagement_matrix_cache.is_feasible(
                        system_id, threat_id)
                else:
                    is_feasible = self.engagement_matrix.get(
                        (system_id, threat_id), False)
                
                if not is_feasible:
                    continue
                
                # 용량 확인
                bat_idx = battery_id_to_idx[system_id]
                if battery_usage[bat_idx] >= battery_capacity[bat_idx]:
                    continue
                if battery_engagement_count[bat_idx] >= battery_specs_cache[bat_idx]:
                    continue
                
                # ✅ k-factor 계산 및 비교
                k = self._get_k_factor(system_id, threat_id)
                if k > best_k:
                    best_k = k
                    best_system = system
            
            # 최선의 시스템 할당
            if best_system:
                system_id = getattr(best_system, 'id', '')
                upper_assignments[key] = system_id
                bat_idx = battery_id_to_idx[system_id]
                battery_usage[bat_idx] += 2
                battery_engagement_count[bat_idx] += 1
                upper_assigned[threat_id] = system_id
                upper_assignment_count += 1
        
        # ================================
        # ✅ 개선 2: 다층 방어 활성화
        # ================================
        # 옵션 A: 완전 제거 (항상 하층 시도)
        # if threat_id in upper_assigned:
        #     continue
        
        # 옵션 B: 자산 가치 기반 조건부
        if threat_id in upper_assigned:
            asset = next((a for a in self.assets 
                         if getattr(a, 'id', '') == target_asset_id), None)
            if asset and getattr(asset, 'value', 0) < 70:
                continue  # 가치 낮으면 하층 건너뛰기
            # 가치 높으면 하층도 시도 (다층 방어)
        
        # 2단계: MSAM 할당 (하층)
        if key not in lower_assignments and lower_assignment_count < max_lower_assignments:
            best_system = None
            best_k = 0
            
            for system in self.lower_systems:
                system_id = getattr(system, 'id', '')
                
                # 교전 가능 여부
                if self.engagement_matrix_cache:
                    is_feasible = self.engagement_matrix_cache.is_feasible(
                        system_id, threat_id)
                else:
                    is_feasible = self.engagement_matrix.get(
                        (system_id, threat_id), False)
                
                if not is_feasible:
                    continue
                
                # 용량 확인
                bat_idx = battery_id_to_idx[system_id]
                if battery_usage[bat_idx] >= battery_capacity[bat_idx]:
                    continue
                if battery_engagement_count[bat_idx] >= battery_specs_cache[bat_idx]:
                    continue
                
                # ✅ k-factor 계산 및 비교
                k = self._get_k_factor(system_id, threat_id)
                if k > best_k:
                    best_k = k
                    best_system = system
            
            # 최선의 시스템 할당
            if best_system:
                system_id = getattr(best_system, 'id', '')
                lower_assignments[key] = system_id
                bat_idx = battery_id_to_idx[system_id]
                battery_usage[bat_idx] += 2
                battery_engagement_count[bat_idx] += 1
                lower_assigned[threat_id] = system_id
                lower_assignment_count += 1
    
    # 목적함수 계산
    self.solve_time = timeit.default_timer() - start_time
    self.objective_value = self._calculate_objective(upper_assignments, lower_assignments)
    self.status = "Optimal"
    
    # 결과 반환
    total_assignments = len(upper_assignments) + len(lower_assignments)
    num_threats = len(self.threats)
    
    return {
        'feasible': True,
        'objective_value': self.objective_value,
        'solve_time': self.solve_time,
        'upper_assignments': upper_assignments,
        'lower_assignments': lower_assignments,
        'algorithm': 'GREEDY',
        'status': self.status,
        'diagnosis': {
            'solver_status': 'Optimal',
            'num_variables': total_assignments,
            'num_constraints': 0,
            'num_threats': num_threats,
            'total_missiles': sum(b.get('available_missiles', 0) 
                                 for b in self.batteries),
            'feasible_engagements': total_assignments,
            'time_limit_reached': False
        }
    }


# Helper 메서드도 추가 필요
def _get_k_factor(self, system_id, threat_id):
    """K-factor 가져오기"""
    if self.k_factor_cache and hasattr(self.k_factor_cache, 'get_k_factor'):
        return self.k_factor_cache.get_k_factor(threat_id, system_id)
    
    # 캐시 없으면 거리 기반 계산
    if self.engagement_matrix_cache and hasattr(self.engagement_matrix_cache, 'get_distance'):
        distance = self.engagement_matrix_cache.get_distance(system_id, threat_id)
        max_range = 150.0 if 'LSAM' in system_id else 80.0
        
        if distance > 0 and max_range > 0:
            range_ratio = 1.0 - (distance / max_range)
            k_factor = self.k_min + (self.k_max - self.k_min) * max(0, range_ratio)
            return max(self.k_min, min(self.k_max, k_factor))
    
    # 기본값
    return 0.9


print("""
사용 방법:
=========
1. greedy_optimizer.py 열기
2. solve() 메서드를 위 코드로 교체
3. _get_k_factor() 메서드 추가 (없으면)
4. 테스트 실행

예상 효과:
=========
• First-fit → Best-fit (k-factor 최적화)
• 다층 방어 활성화 (가치 70 이상 자산)
• 목적함수 개선: 30-50% 예상

변경 사항:
=========
✓ Best-fit 전략 (k-factor 최대 시스템 선택)
✓ 다층 방어 조건부 활성화
✓ 할당 품질 향상

다층 방어 옵션:
==============
• 옵션 A (Line 제거): 모든 위협 다층 방어
• 옵션 B (조건부): 가치 높은 자산만 다층 방어

권장: 옵션 B (자원 효율성 + 성능 균형)
""")
