#!/usr/bin/env python3
"""
Monte Carlo CLI for DWTA System
CLI-based Monte Carlo simulation that replicates GUI simulation logic
"""

import json
import time
import random
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Any
import numpy as np
from dataclasses import dataclass

# Import DWTA components
try:
    from config_mip import mip_config
    from nonlinear_mip_optimizer import NonLinearMIPOptimizer, Asset, InterceptorSystem, Threat
    from uncertainty_modeling import UncertaintyModeling, UncertaintyConfig
    from defense_gap_analyzer import DefenseGapAnalyzer
    MIP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: MIP components not available: {e}")
    MIP_AVAILABLE = False
    # Fallback 클래스 정의
    from dataclasses import dataclass
    from typing import Tuple, List
    
    @dataclass
    class Asset:
        id: str
        position: Tuple[float, float]
        value: float
        priority: int = 1
        estimated_threat_missiles: List[str] = None
    
    @dataclass
    class InterceptorSystem:
        id: str
        system_type: str
        position: Tuple[float, float]
        available_missiles: int
        max_missiles_per_target: int
        intercept_probability: float
        engagement_range: float
    
    @dataclass
    class Threat:
        id: str
        target_asset_id: str
        current_position: Tuple[float, float, float]
        estimated_impact_time: float

class HeadlessTracker:
    """GUI 없는 순수 시뮬레이션 엔진 - MultiMissileTracker와 동일한 로직"""
    
    def __init__(self, scenario_data: Dict, uncertainty_config: Optional[Dict] = None):
        # GUI 버전과 동일한 초기화
        self.use_mip = MIP_AVAILABLE
        self.objective = 'MIN_DAMAGE'
        
        # 시나리오 데이터
        self.scenario_data = scenario_data
        self.assets = scenario_data.get('assets', [])
        self.batteries = scenario_data.get('batteries', [])
        self.initial_threats_config = scenario_data.get('threats', [])
        self.engagement_matrix = scenario_data.get('engagement_matrix', {})
        
        # 시뮬레이션 상태 (GUI와 동일)
        self.current_time_step = 0
        self.missiles = {}
        self.kill_results = {}
        self.optimization_history = []
        self.last_optimization_step = -1
        self.optimization_count = 0
        self.max_optimizations_per_timestep = 3
        self.last_objective_value = None
        self.last_predicted_objective = None  # 최적화 시점 예측값
        self.last_solve_time = 0
        
        # 디버깅 카운터
        self.dwta_call_count = 0
        self.optimizer_solve_count = 0
        self.optimization_statuses = []  # 최적화 상태 기록
        
        # 통계 (GUI와 동일)
        self.stats = {
            'total': 0,
            'active': 0,
            'intercepted': 0,
            'missed': 0,
            'launch_failures': 0,
            'tracked_misses': []
        }
        
        # 불확실성 모델링
        self.uncertainty_model = None
        self.monte_carlo_mode = True
        if uncertainty_config:
            config = UncertaintyConfig(**uncertainty_config)
            self.uncertainty_model = UncertaintyModeling(config)
        
        # MIP 최적화기 (GUI와 동일한 설정)
        if MIP_AVAILABLE:
            self.config = mip_config
        
        # 방어 공백 분석기
        self.gap_analyzer = DefenseGapAnalyzer()
        
        # 시나리오 시작
        self.start_scenario()
    
    def start_scenario(self):
        """시나리오 시작 - GUI 버전과 동일한 로직"""
        # 포대 초기화 (GUI와 동일)
        for battery in self.batteries:
            try:
                if 'specs' not in battery or 'battery_config' not in battery['specs']:
                    battery['available_missiles'] = 10
                else:
                    battery['available_missiles'] = battery['specs']['battery_config']['total_missiles']
                
                battery['status'] = 'OPERATIONAL'
                
                if 'position' not in battery:
                    battery['position'] = (0.0, 0.0)
                    
            except (KeyError, TypeError):
                battery['available_missiles'] = 10
                battery['status'] = 'OPERATIONAL'
                battery['position'] = (0.0, 0.0)
        
        # 미사일 초기화 (threats 키도 확인)
        threats_data = self.scenario_data.get('missiles', []) or self.scenario_data.get('threats', [])
        
        self.missiles = {}
        for missile_data in threats_data:
            missile_id = missile_data['id']
            self.missiles[missile_id] = {
                **missile_data,
                'active': False,  # 시작 시 비활성
                'launch_time': missile_data.get('launch_time', 0),
                'position': missile_data.get('position', [0, 0]),
                'target': missile_data.get('target', None),
                'target_asset': missile_data.get('target_asset') or missile_data.get('target_asset_id'),  # ✓ 추가
                'speed': missile_data.get('speed', 1.0),
                'flight_time': missile_data.get('flight_time', 100),  # ✓ 추가
                'flight_progress': 0.0,  # ✓ 추가
                'needs_reassignment': False,
                'assigned_interceptors': []
            }
        
        # 통계 초기화
        self.stats['total'] = len(self.missiles)
        self.stats['active'] = 0
        self.stats['intercepted'] = 0
        self.stats['missed'] = 0
        self.stats['launch_failures'] = 0
        self.stats['tracked_misses'] = []
        
        # 시뮬레이션 상태 초기화
        self.current_time_step = 0
        self.kill_results = {}
        self.primary_assignments = {}  # 할당 정보 (GUI와 동일)
        self.optimization_history = []
        self.last_optimization_step = -1
        self.optimization_count = 0
        
        # 디버깅 카운터 초기화
        self.dwta_call_count = 0
        self.optimizer_solve_count = 0
        self.optimization_statuses = []
    
    def run_realtime_dwta(self):
        """실시간 DWTA 최적화 - GUI 버전과 동일한 로직"""
        self.dwta_call_count += 1
        
        if not self.use_mip:
            print(f"[T={self.current_time_step}] MIP not available")
            return
            
        # 활성 위협 수 확인 (발사 예정 포함)
        active_or_launching = [m for m in self.missiles.values() 
                               if m['active'] or m.get('launch_time', 0) <= self.current_time_step]
        active_threats_count = len(active_or_launching)
        if self.current_time_step <= 10:
            print(f"[T={self.current_time_step}] Active/launching threats: {active_threats_count}")
        if active_threats_count == 0:
            return
        
        # 최적화 실행 제한 (deadlock 방지)
        if self.last_optimization_step == self.current_time_step:
            self.optimization_count += 1
            if self.optimization_count > self.max_optimizations_per_timestep:
                return
        else:
            self.optimization_count = 1
            self.last_optimization_step = self.current_time_step
        
        # 최적화 입력 준비 (GUI와 동일 - 객체 생성)
        # Assets 준비
        assets_opt = []
        for asset in self.assets:
            assets_opt.append(Asset(
                id=asset['id'],
                position=tuple(asset['position']),
                value=asset.get('value', 1.0),
                priority=asset.get('priority', 1),
                estimated_threat_missiles=[]
            ))
        
        # Interceptor Systems 준비
        systems_opt = []
        
        # DEBUG: 포대 상태 확인
        if self.current_time_step == 0:
            print(f"\n=== BATTERY STATUS [T={self.current_time_step}] ===")
            for battery in self.batteries:
                print(f"{battery['id']}: available_missiles={battery.get('available_missiles', 'NONE')}, status={battery.get('status', 'NONE')}")
        
        for battery in self.batteries:
            if battery.get('available_missiles', 0) <= 0:
                if self.current_time_step == 0:
                    print(f"  SKIPPED {battery['id']}: no missiles")
                continue
            
            # 시스템 스펙 추출
            if battery['system_type'] == 'LSAM':
                specs = battery['specs']['ballistic_missile_specs']
                Pk = specs['intercept_probability']
                Range = specs['engagement_range_km']['max']
                max_missiles = battery['specs']['battery_config'].get('simultaneous_engagements', 2)
            elif battery['system_type'] == 'MSAM':
                specs = battery['specs']['ballistic_missile_specs']
                Pk = specs['intercept_probability']
                Range = specs['engagement_range_km']['max']
                max_missiles = battery['specs']['battery_config'].get('simultaneous_engagements', 2)
            else:
                Pk = 0.95
                Range = 50.0
                max_missiles = 3
            
            systems_opt.append(InterceptorSystem(
                id=battery['id'],
                system_type=battery['system_type'],
                position=tuple(battery['position']),
                available_missiles=battery['available_missiles'],
                max_missiles_per_target=min(max_missiles, battery['available_missiles']),
                intercept_probability=Pk,
                engagement_range=Range
            ))
        
        # Threats 준비
        threats_opt = []
        for missile_id, missile in self.missiles.items():
            # 활성 미사일만 포함 (발사 예정은 제외)
            if missile.get('active', False):
                # 남은 비행 시간 계산
                remaining_time = max(0.1, missile['flight_time'] * (1.0 - missile.get('flight_progress', 0)))
                current_pos = missile.get('position', [0, 0])
                altitude = 10000.0 * (1.0 - missile.get('flight_progress', 0))
                
                threats_opt.append(Threat(
                    id=missile_id,
                    target_asset_id=missile.get('target_asset'),
                    current_position=(current_pos[0], current_pos[1], altitude),
                    estimated_impact_time=remaining_time
                ))
        
        if not threats_opt:
            return
        
        try:
            # 최적화 실행
            optimizer = NonLinearMIPOptimizer(self.config)
            optimizer.create_model(
                assets=assets_opt,
                interceptor_systems=systems_opt,
                threats=threats_opt,
                batteries=self.batteries,
                engagement_matrix=self.engagement_matrix
            )
            
            self.optimizer_solve_count += 1
            result = optimizer.solve()
            
            # 상태 기록 (처음 10개만)
            if len(self.optimization_statuses) < 10:
                self.optimization_statuses.append({
                    'time_step': self.current_time_step,
                    'feasible': result.get('feasible') if result else None,
                    'status': result.get('status') if result else None
                })
            
            # 결과 처리 (GUI와 동일)
            if result and result.get('feasible', False):
                # 최적화 시점의 예측 손실 (기댓값)
                predicted_objective = result.get('objective_value', 0.0)
                if predicted_objective != float('inf') and predicted_objective is not None:
                    self.last_predicted_objective = predicted_objective  # 예측값 저장
                    self.last_objective_value = predicted_objective  # 호환성 유지
                    self.optimization_history.append((self.current_time_step, predicted_objective))
                
                # 할당 정보 저장 (GUI와 동일)
                upper_assignments = result.get('upper_assignments', {})
                lower_assignments = result.get('lower_assignments', {})
                
                # DEBUG
                if self.current_time_step == 5:  # 첫 최적화 시점
                    print(f"\n=== DEBUG [T={self.current_time_step}] ===")
                    print(f"Upper assignments: {upper_assignments}")
                    print(f"Lower assignments: {lower_assignments}")
                
                if upper_assignments or lower_assignments:
                    new_assignments = {}
                    
                    # 상층 할당 (LSAM)
                    for assignment_key, system_id in upper_assignments.items():
                        # assignment_key 형식: "A05_T08" (자산_위협)
                        # system_id: 포대 ID (LSAM_01, etc.)
                        parts = assignment_key.split('_')
                        if len(parts) >= 2:
                            threat_id = parts[1]  # T08
                            new_assignments[system_id] = threat_id  # 포대 ID → 위협 ID
                    
                    # 하층 할당 (MSAM)
                    for assignment_key, system_id in lower_assignments.items():
                        # assignment_key 형식: "A05_T08" (자산_위협)
                        # system_id: 포대 ID (MSAM_01, etc.)
                        parts = assignment_key.split('_')
                        if len(parts) >= 2:
                            threat_id = parts[1]  # T08
                            new_assignments[system_id] = threat_id  # 포대 ID → 위협 ID
                    
                    self.primary_assignments = new_assignments
                    
                    # DEBUG
                    if self.current_time_step == 5:
                        print(f"Final primary_assignments: {self.primary_assignments}")
                        print("=" * 50)
                
        except Exception as e:
            # 예외 기록
            if len(self.optimization_statuses) < 10:
                self.optimization_statuses.append({
                    'time_step': self.current_time_step,
                    'error': str(e)
                })
            print(f"Optimization error at T={self.current_time_step}: {e}")
    
    def update_simulation(self):
        """시뮬레이션 업데이트 - GUI 버전과 동일한 로직"""
        # 미사일 발사 처리
        for missile_id, missile in self.missiles.items():
            if not missile.get('active', False) and missile.get('launch_time', 0) <= self.current_time_step:
                missile['active'] = True
                missile['flight_progress'] = 0.0
                self.stats['active'] += 1
        
        # 미사일 비행 진행 업데이트
        for missile_id, missile in self.missiles.items():
            if missile.get('active', False):
                elapsed = self.current_time_step - missile.get('launch_time', 0)
                flight_time = missile.get('flight_time', 100)
                missile['flight_progress'] = min(elapsed / flight_time, 1.0)
        
        # 요격 처리 (GUI와 동일한 로직 + 불확실성 모델링)
        for missile_id, missile in list(self.missiles.items()):
            if missile.get('active', False) and missile_id not in self.kill_results:
                # 할당된 포대 확인
                assigned_batteries = []
                for battery_id, assigned_threat_id in getattr(self, 'primary_assignments', {}).items():
                    if assigned_threat_id == missile_id:
                        battery = next((b for b in self.batteries if b['id'] == battery_id), None)
                        if battery and battery.get('status') == 'OPERATIONAL' and battery.get('available_missiles', 0) > 0:
                            assigned_batteries.append(battery)
                
                # 할당된 포대가 있으면 요격 시도
                if assigned_batteries:
                    P_survival = 1.0
                    missiles_fired = 0
                    
                    for battery in assigned_batteries:
                        # 포대별 요격 확률 (GUI와 동일)
                        try:
                            if battery['system_type'] == 'LSAM':
                                Pk = battery['specs']['ballistic_missile_specs']['intercept_probability']
                            elif battery['system_type'] == 'MSAM':
                                Pk = battery['specs']['ballistic_missile_specs']['intercept_probability']
                            else:
                                Pk = 0.98
                        except (KeyError, TypeError):
                            Pk = 0.98
                        
                        # 불확실성 적용 (몬테카를로만)
                        if self.uncertainty_model and self.monte_carlo_mode:
                            Pk = self.uncertainty_model.sample_intercept_probability(Pk)
                        
                        # 생존 확률 계산 (GUI와 동일)
                        P_survival *= (1 - Pk)
                        
                        # 미사일 발사
                        battery['available_missiles'] -= 1
                        missiles_fired += 1
                    
                    # 최종 요격 확률
                    P_kill = 1.0 - P_survival
                    P_kill = min(P_kill, 0.999)
                    
                    # 🆕 Deterministic Outcome (Stage 2 제거)
                    # 기댓값 기반 판정: 불확실성은 Stage 1(Beta 분포)에서만 적용
                    if P_kill >= 0.5 and missiles_fired > 0:
                        self.kill_results[missile_id] = ('INTERCEPTED', self.current_time_step)
                        missile['active'] = False
                        self.stats['active'] -= 1
                        self.stats['intercepted'] += 1
                    else:
                        # 요격 실패 - 미사일이 목표에 도달
                        if self.current_time_step > missile.get('launch_time', 0) + 50:
                            self.kill_results[missile_id] = ('MISSED', self.current_time_step)
                            missile['active'] = False
                            self.stats['active'] -= 1
                            self.stats['missed'] += 1
                else:
                    # 할당 없음 - 미사일이 목표에 도달
                    if self.current_time_step > missile.get('launch_time', 0) + 50:
                        self.kill_results[missile_id] = ('MISSED', self.current_time_step)
                        missile['active'] = False
                        self.stats['active'] -= 1
                        self.stats['missed'] += 1
        
        # 시간 진행
        self.current_time_step += 1
    
    def run_single_simulation(self) -> Dict:
        """단일 시뮬레이션 실행"""
        start_time = time.time()
        max_duration = 300  # 5분
        
        print(f"\n=== SIMULATION START ===")
        print(f"MIP_AVAILABLE: {MIP_AVAILABLE}")
        print(f"self.use_mip: {self.use_mip}")
        print(f"Total threats: {len(self.missiles)}")
        print("=" * 50)
        
        while self.current_time_step < max_duration:
            # DWTA 최적화 실행
            self.run_realtime_dwta()
            
            # 시뮬레이션 업데이트
            self.update_simulation()
            
            # 종료 조건 확인
            all_threats_launched = all(missile['launch_time'] <= self.current_time_step for missile in self.missiles.values())
            all_threats_resolved = len(self.kill_results) == self.stats['total']
            no_active_threats = self.stats['active'] == 0
            
            if all_threats_launched and all_threats_resolved and no_active_threats:
                break
        
        # 실제 달성된 자산 보호 가치 및 최종 손실 계산 (불확실성 반영)
        actual_protected_value = 0
        actual_damage = 0
        for asset in self.assets:
            asset_id = asset['id']
            asset_value = asset.get('value', 0)
            # 이 자산을 타겟으로 하는 미사일들 확인
            threats_to_asset = [m_id for m_id, m in self.missiles.items() if m.get('target_asset') == asset_id]
            # 모두 요격되었으면 자산 가치 보호
            if threats_to_asset and all(m_id in self.kill_results and self.kill_results[m_id] for m_id in threats_to_asset):
                actual_protected_value += asset_value
            elif threats_to_asset:  # 일부라도 요격 실패하면 자산 손실
                actual_damage += asset_value
        
        # 최종 목적함수 값 = 실제 손실 (스케일링 제거됨)
        final_objective_value = actual_damage
        
        # 결과 반환 (예측값과 실제값 모두 포함)
        return {
            'objective_value': final_objective_value,  # 시뮬레이션 후 실제 손실 (Monte Carlo)
            'predicted_objective': self.last_predicted_objective,  # 최적화 시점 예측 손실 (기댓값)
            'actual_objective': actual_damage,  # 시뮬레이션 후 실제 손실 (동일)
            'prediction_error': abs(self.last_predicted_objective - actual_damage) if self.last_predicted_objective else 0,  # 예측 오차
            'actual_protected_value': actual_protected_value,  # 실제 보호된 자산 가치
            'actual_damage': actual_damage,  # 실제 손실된 자산 가치
            'success_rate': self.stats['intercepted'] / self.stats['total'] if self.stats['total'] > 0 else 0,
            'intercepted': self.stats['intercepted'],
            'missed': self.stats['missed'],
            'total_threats': self.stats['total'],
            'simulation_time': time.time() - start_time,
            'final_time_step': self.current_time_step,
            # DEBUG
            'debug': {
                'mip_available': MIP_AVAILABLE,
                'use_mip': self.use_mip,
                'dwta_call_count': self.dwta_call_count,
                'optimizer_solve_count': self.optimizer_solve_count,
                'optimization_count': len(self.optimization_history),
                'primary_assignments_count': len(self.primary_assignments),
                'primary_assignments_sample': dict(list(self.primary_assignments.items())[:3]) if self.primary_assignments else {},
                'optimization_statuses': self.optimization_statuses
            }
        }


class MonteCarloRunner:
    """몬테카를로 시뮬레이션 실행기"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.results = []
    
    def run_monte_carlo(self, num_runs: int, num_processes: Optional[int] = None) -> Dict:
        """몬테카를로 시뮬레이션 실행"""
        if num_processes is None:
            num_processes = min(mp.cpu_count(), num_runs)
        
        print(f"몬테카를로 시뮬레이션 시작: {num_runs}회, {num_processes} 프로세스")
        start_time = time.time()
        
        # 프로세스 풀로 병렬 실행
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = []
            
            for i in range(num_runs):
                future = executor.submit(self._run_single_monte_carlo, i)
                futures.append(future)
            
            # 결과 수집
            results = []
            for i, future in enumerate(futures):
                try:
                    result = future.result(timeout=600)  # 10분 타임아웃
                    results.append(result)
                    if (i + 1) % 10 == 0:
                        print(f"완료: {i + 1}/{num_runs}")
                except Exception as e:
                    print(f"Run {i} failed: {e}")
        
        total_time = time.time() - start_time
        
        # 통계 계산
        stats = self._calculate_statistics(results)
        stats['total_execution_time'] = total_time
        stats['num_runs'] = len(results)
        
        return {
            'results': results,
            'statistics': stats
        }
    
    def _run_single_monte_carlo(self, run_id: int) -> Dict:
        """단일 몬테카를로 실행"""
        try:
            # 시나리오 생성 (GUI와 동일한 방식)
            from config_mip import mip_config
            scenario = mip_config.create_realistic_scenario()
            
            # 불확실성 설정 (GUI와 동일한 시나리오, 불확실성만 추가)
            uncertainty_config = {
                'beta_alpha': 9,  # 평균 0.9 (GUI 고정 확률과 유사)
                'beta_beta': 1,   # 높은 성공 편향
                'normal_std': 0.05
            }
            
            # 시뮬레이션 실행
            tracker = HeadlessTracker(scenario, uncertainty_config)
            result = tracker.run_single_simulation()
            result['run_id'] = run_id
            
            return result
            
        except Exception as e:
            print(f"Monte Carlo run {run_id} error: {e}")
            return {
                'run_id': run_id,
                'error': str(e),
                'objective_value': 0,
                'success_rate': 0,
                'intercepted': 0,
                'missed': 0,
                'total_threats': 0,
                'simulation_time': 0,
                'final_time_step': 0
            }
    
    def _calculate_statistics(self, results: List[Dict]) -> Dict:
        """통계 계산"""
        if not results:
            return {}
        
        # 유효한 결과만 필터링
        valid_results = [r for r in results if 'error' not in r]
        
        if not valid_results:
            return {'error': 'No valid results'}
        
        # 기본 통계 (예측값과 실제값 분리)
        objectives = [r['objective_value'] for r in valid_results]  # 실제 손실
        predicted_objectives = [r.get('predicted_objective', 0) for r in valid_results]  # 예측 손실
        actual_objectives = [r.get('actual_objective', 0) for r in valid_results]  # 실제 손실 (동일)
        prediction_errors = [r.get('prediction_error', 0) for r in valid_results]  # 예측 오차
        actual_values = [r['actual_protected_value'] for r in valid_results]
        actual_damages = [r.get('actual_damage', 0) for r in valid_results]
        success_rates = [r['success_rate'] for r in valid_results]
        
        stats = {
            # 실제 손실 (시뮬레이션 후)
            'objective_mean': np.mean(objectives),
            'objective_std': np.std(objectives),
            'objective_min': np.min(objectives),
            'objective_max': np.max(objectives),
            # 예측 손실 (최적화 시점)
            'predicted_objective_mean': np.mean(predicted_objectives),
            'predicted_objective_std': np.std(predicted_objectives),
            'predicted_objective_min': np.min(predicted_objectives),
            'predicted_objective_max': np.max(predicted_objectives),
            # 예측 오차
            'prediction_error_mean': np.mean(prediction_errors),
            'prediction_error_std': np.std(prediction_errors),
            'prediction_error_min': np.min(prediction_errors),
            'prediction_error_max': np.max(prediction_errors),
            'actual_value_mean': np.mean(actual_values),
            'actual_value_std': np.std(actual_values),
            'actual_value_min': np.min(actual_values),
            'actual_value_max': np.max(actual_values),
            'actual_damage_mean': np.mean(actual_damages),
            'actual_damage_std': np.std(actual_damages),
            'success_rate_mean': np.mean(success_rates),
            'success_rate_std': np.std(success_rates),
            'success_rate_min': np.min(success_rates),
            'success_rate_max': np.max(success_rates),
            'valid_runs': len(valid_results),
            'failed_runs': len(results) - len(valid_results)
        }
        
        # 신뢰구간 계산 (95%)
        if len(valid_results) > 1:
            try:
                from scipy import stats as scipy_stats
                obj_ci = scipy_stats.t.interval(0.95, len(objectives)-1, 
                                              loc=np.mean(objectives), 
                                              scale=scipy_stats.sem(objectives))
                actual_ci = scipy_stats.t.interval(0.95, len(actual_values)-1,
                                                  loc=np.mean(actual_values),
                                                  scale=scipy_stats.sem(actual_values))
                sr_ci = scipy_stats.t.interval(0.95, len(success_rates)-1,
                                             loc=np.mean(success_rates),
                                             scale=scipy_stats.sem(success_rates))
                
                stats['objective_ci_95'] = obj_ci
                stats['actual_value_ci_95'] = actual_ci
                stats['success_rate_ci_95'] = sr_ci
            except ImportError:
                print("Warning: scipy not available for confidence intervals")
        
        return stats


def convert_numpy_types(obj):
    """NumPy 타입을 JSON 직렬화 가능한 타입으로 변환"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    return obj


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DWTA Monte Carlo Simulation')
    parser.add_argument('--runs', type=int, default=30, help='Number of Monte Carlo runs')
    parser.add_argument('--processes', type=int, default=None, help='Number of processes')
    parser.add_argument('--output', type=str, default='monte_carlo_results.json', help='Output file')
    
    args = parser.parse_args()
    
    # 몬테카를로 실행
    runner = MonteCarloRunner({})
    results = runner.run_monte_carlo(args.runs, args.processes)
    
    # 결과 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(convert_numpy_types(results), f, indent=2, ensure_ascii=False)
    
    # 결과 출력
    stats = results['statistics']
    print("\n=== Monte Carlo Simulation Results ===")
    print(f"Total runs: {stats.get('valid_runs', 0)} valid, {stats.get('failed_runs', 0)} failed")
    print(f"Final objective value (actual damage): {stats.get('objective_mean', 0):.3f} ± {stats.get('objective_std', 0):.3f}")
    print(f"Actual damage (asset value): {stats.get('actual_damage_mean', 0):.1f} ± {stats.get('actual_damage_std', 0):.1f}")
    print(f"Actual protected value: {stats.get('actual_value_mean', 0):.1f} ± {stats.get('actual_value_std', 0):.1f}")
    print(f"Success rate: {stats.get('success_rate_mean', 0):.3f} ± {stats.get('success_rate_std', 0):.3f}")
    print(f"Total execution time: {stats.get('total_execution_time', 0):.2f} seconds")
    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
