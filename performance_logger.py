"""
Performance Logger for DWTA Comparison
=======================================
성능 측정, 기록, 비교, 시각화
"""

import json
import csv
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import os

@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    # 실험 정보
    scenario: str
    algorithm: str
    timestamp: str
    
    # 방어 효과성
    total_assets: int
    survived_assets: int
    survival_rate: float  # %
    total_asset_value: float
    survived_value: float
    value_preservation_rate: float  # %
    
    # 요격 성능
    total_threats: int
    intercepted: int
    missed: int
    intercept_rate: float  # %
    
    # 자원 효율성
    total_missiles_available: int
    missiles_used: int
    usage_rate: float  # %
    missiles_per_threat: float
    successful_intercepts_per_missile: float
    
    # 계산 성능
    avg_solve_time: float
    max_solve_time: float
    min_solve_time: float
    std_solve_time: float
    total_optimizations: int
    total_optimization_time: float
    
    # 문제 크기
    num_variables: int = 0
    num_constraints: int = 0
    memory_usage_mb: float = 0
    
    # 추가 정보
    convergence_history: Optional[List[float]] = None
    extra_info: Optional[Dict] = None


class PerformanceLogger:
    """성능 로깅 및 비교 분석"""
    
    def __init__(self, output_dir: str = "performance_results"):
        self.output_dir = output_dir
        self.metrics_history = []
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"[OK] PerformanceLogger 초기화 완료: {output_dir}")
    
    def log_simulation(self, scenario: str, algorithm: str, tracker, result: Dict):
        """시뮬레이션 결과 로깅"""
        
        # 자산 정보
        total_assets = len(tracker.assets)
        
        # 미사일로부터 위협받은 자산 ID 수집 (안전하게)
        threatened_assets = set()
        for m in tracker.missiles.values():
            if not m.get('intercepted', True):  # 요격 실패한 미사일
                # target_asset_id 안전하게 가져오기
                target_id = m.get('target_asset_id', None)
                if target_id:
                    threatened_assets.add(target_id)
        
        survived_assets = sum(1 for a in tracker.assets if a['id'] not in threatened_assets)
        survival_rate = (survived_assets / total_assets * 100) if total_assets > 0 else 0
        
        total_value = sum(a['value'] for a in tracker.assets)
        survived_value = sum(a['value'] for a in tracker.assets if a['id'] not in threatened_assets)
        value_preservation_rate = (survived_value / total_value * 100) if total_value > 0 else 0
        
        # 위협 정보
        total_threats = tracker.stats['total']
        intercepted = tracker.stats['intercepted']
        missed = tracker.stats['missed']
        intercept_rate = (intercepted / total_threats * 100) if total_threats > 0 else 0
        
        # 미사일 사용 (안전하게 접근)
        systems = getattr(tracker, 'interceptor_systems', None) or getattr(tracker, 'systems', [])
        total_missiles = sum(getattr(s, 'max_missiles', 10) for s in systems) if systems else 0
        missiles_used = len([m for m in tracker.missiles.values() if m.get('launched', False)])
        usage_rate = (missiles_used / total_missiles * 100) if total_missiles > 0 else 0
        missiles_per_threat = missiles_used / total_threats if total_threats > 0 else 0
        efficiency = intercepted / missiles_used if missiles_used > 0 else 0
        
        # 최적화 시간
        solve_times = [h['solve_time'] for h in tracker.optimization_history if 'solve_time' in h]
        avg_solve_time = np.mean(solve_times) if solve_times else 0
        max_solve_time = np.max(solve_times) if solve_times else 0
        min_solve_time = np.min(solve_times) if solve_times else 0
        std_solve_time = np.std(solve_times) if solve_times else 0
        total_opt_time = sum(solve_times) if solve_times else 0
        
        # 메트릭 생성
        metrics = PerformanceMetrics(
            scenario=scenario,
            algorithm=algorithm,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            
            total_assets=total_assets,
            survived_assets=survived_assets,
            survival_rate=survival_rate,
            total_asset_value=total_value,
            survived_value=survived_value,
            value_preservation_rate=value_preservation_rate,
            
            total_threats=total_threats,
            intercepted=intercepted,
            missed=missed,
            intercept_rate=intercept_rate,
            
            total_missiles_available=total_missiles,
            missiles_used=missiles_used,
            usage_rate=usage_rate,
            missiles_per_threat=missiles_per_threat,
            successful_intercepts_per_missile=efficiency,
            
            avg_solve_time=avg_solve_time,
            max_solve_time=max_solve_time,
            min_solve_time=min_solve_time,
            std_solve_time=std_solve_time,
            total_optimizations=len(solve_times),
            total_optimization_time=total_opt_time,
            
            convergence_history=result.get('convergence_history', None),
            extra_info=result.get('extra_info', None)
        )
        
        self.metrics_history.append(metrics)
        
        print(f"\n[OK] 성능 로깅 완료: {scenario} - {algorithm}")
        print(f"  생존율: {survival_rate:.1f}%, 요격률: {intercept_rate:.1f}%, 평균 시간: {avg_solve_time:.3f}s")
        
        return metrics
    
    def export_to_csv(self, filename: str = None):
        """CSV 파일로 내보내기"""
        if not filename:
            filename = f"{self.output_dir}/performance_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not self.metrics_history:
            print("저장할 메트릭이 없습니다.")
            return
        
        # CSV 작성
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            # 헤더
            fieldnames = [k for k in asdict(self.metrics_history[0]).keys() if k not in ['convergence_history', 'extra_info']]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # 데이터
            for metrics in self.metrics_history:
                row = {k: v for k, v in asdict(metrics).items() if k in fieldnames}
                writer.writerow(row)
        
        print(f"[OK] CSV 저장 완료: {filename}")
        return filename
    
    def export_to_json(self, filename: str = None):
        """JSON 파일로 내보내기"""
        if not filename:
            filename = f"{self.output_dir}/performance_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if not self.metrics_history:
            print("저장할 메트릭이 없습니다.")
            return
        
        # JSON 작성
        data = [asdict(m) for m in self.metrics_history]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] JSON 저장 완료: {filename}")
        return filename
    
    def log_timestep(self, scenario: str, algorithm: str, timestep: int, data: Dict):
        """매 time step마다 상세 로깅"""
        log_entry = {
            'scenario': scenario,
            'algorithm': algorithm,
            'timestep': timestep,
            'active_threats': data.get('active_threats', 0),
            'intercepted_cumulative': data.get('intercepted', 0),
            'missed_cumulative': data.get('missed', 0),
            'objective_value': data.get('objective_value', 0),
            'solve_time': data.get('solve_time', 0),
            'assignments_count': data.get('assignments_count', 0)
        }
        
        # CSV 파일에 append
        filename = f"{self.output_dir}/timestep_log_{scenario}_{algorithm}.csv"
        
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=log_entry.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(log_entry)
        
        return log_entry
    
    def export_timestep_summary(self, scenario: str, algorithms: List[str]):
        """Time step 로그 요약 생성"""
        summary = {}
        
        for algo in algorithms:
            filename = f"{self.output_dir}/timestep_log_{scenario}_{algo}.csv"
            
            if not os.path.exists(filename):
                continue
            
            import pandas as pd
            try:
                df = pd.read_csv(filename)
                summary[algo] = {
                    'total_timesteps': len(df),
                    'avg_solve_time': df['solve_time'].mean(),
                    'max_solve_time': df['solve_time'].max(),
                    'final_intercepted': df['intercepted_cumulative'].iloc[-1] if len(df) > 0 else 0,
                    'final_missed': df['missed_cumulative'].iloc[-1] if len(df) > 0 else 0
                }
            except:
                pass
        
        return summary
    
    def generate_latex_table(self, filename: str = None):
        """LaTeX 표 생성"""
        if not filename:
            filename = f"{self.output_dir}/performance_table.tex"
        
        if not self.metrics_history:
            print("표를 생성할 메트릭이 없습니다.")
            return
        
        # LaTeX 표 생성
        latex = "\\begin{table}[htbp]\n"
        latex += "\\centering\n"
        latex += "\\caption{DWTA Algorithm Performance Comparison}\n"
        latex += "\\label{tab:performance}\n"
        latex += "\\begin{tabular}{lllrrr}\n"
        latex += "\\hline\n"
        latex += "Scenario & Algorithm & Survival (\\%) & Intercept (\\%) & Efficiency & Time (s) \\\\\n"
        latex += "\\hline\n"
        
        for m in self.metrics_history:
            latex += f"{m.scenario} & {m.algorithm} & {m.survival_rate:.1f} & {m.intercept_rate:.1f} & {m.successful_intercepts_per_missile:.3f} & {m.avg_solve_time:.3f} \\\\\n"
        
        latex += "\\hline\n"
        latex += "\\end{tabular}\n"
        latex += "\\end{table}\n"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(latex)
        
        print(f"[OK] LaTeX 표 저장: {filename}")
        return filename
