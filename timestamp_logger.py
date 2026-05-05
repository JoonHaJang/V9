"""
타임스탬프 기반 상세 로그 시스템
================================
매 최적화 시점마다 할당 결정 과정을 상세히 기록

목적:
- 알고리즘별 의사결정 과정 추적
- 시간대별 성능 분석
- 할당 변화 패턴 파악
"""

import json
from datetime import datetime
from typing import Dict, List, Any
import os

class TimestampLogger:
    """타임스탬프 기반 상세 로그 시스템"""
    
    def __init__(self, scenario_name: str, algorithm: str, output_dir: str = "performance_results/logs"):
        self.scenario_name = scenario_name
        self.algorithm = algorithm
        self.output_dir = output_dir
        self.logs = []
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 로그 파일명
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = f"{output_dir}/{scenario_name}_{algorithm}_{timestamp}.jsonl"
    
    def log_optimization(self, time_step: int, optimization_data: Dict[str, Any]):
        """
        최적화 시점 로그 기록
        
        Args:
            time_step: 현재 시뮬레이션 시간 (초)
            optimization_data: 최적화 결과 데이터
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'time_step': time_step,
            'algorithm': self.algorithm,
            'scenario': self.scenario_name,
            **optimization_data
        }
        
        self.logs.append(log_entry)
        
        # 실시간 파일 저장 (JSONL 형식)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_assignment_decision(self, time_step: int, threat_id: str, asset_id: str, 
                                upper_system: str, lower_system: str, 
                                decision_metrics: Dict[str, float]):
        """
        할당 결정 상세 로그
        
        Args:
            time_step: 시뮬레이션 시간
            threat_id: 위협 ID
            asset_id: 자산 ID
            upper_system: 할당된 상층 시스템
            lower_system: 할당된 하층 시스템
            decision_metrics: 결정 근거 메트릭
        """
        self.log_optimization(time_step, {
            'event_type': 'assignment',
            'threat_id': threat_id,
            'asset_id': asset_id,
            'upper_system': upper_system,
            'lower_system': lower_system,
            'metrics': decision_metrics
        })
    
    def log_intercept_attempt(self, time_step: int, threat_id: str, 
                             system_id: str, success: bool, 
                             probability: float, attempt_number: int):
        """
        요격 시도 로그
        
        Args:
            time_step: 시뮬레이션 시간
            threat_id: 위협 ID
            system_id: 요격 시스템 ID
            success: 요격 성공 여부
            probability: 요격 확률
            attempt_number: 시도 횟수
        """
        self.log_optimization(time_step, {
            'event_type': 'intercept',
            'threat_id': threat_id,
            'system_id': system_id,
            'success': success,
            'probability': probability,
            'attempt_number': attempt_number
        })
    
    def log_resource_status(self, time_step: int, resource_data: Dict[str, Any]):
        """
        자원 상태 로그
        
        Args:
            time_step: 시뮬레이션 시간
            resource_data: 자원 상태 데이터
        """
        self.log_optimization(time_step, {
            'event_type': 'resource_status',
            **resource_data
        })
    
    def generate_summary_report(self) -> str:
        """
        로그 요약 보고서 생성
        
        Returns:
            요약 보고서 텍스트
        """
        if not self.logs:
            return "No logs available"
        
        # 이벤트 타입별 집계
        event_counts = {}
        for log in self.logs:
            event_type = log.get('event_type', 'optimization')
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # 시간대별 활동
        time_steps = [log['time_step'] for log in self.logs]
        min_time = min(time_steps) if time_steps else 0
        max_time = max(time_steps) if time_steps else 0
        
        report = f"""
{'='*80}
TIMESTAMP LOG SUMMARY REPORT
{'='*80}
Scenario: {self.scenario_name}
Algorithm: {self.algorithm}
Log File: {self.log_file}

Total Events: {len(self.logs)}
Time Range: T={min_time}s ~ T={max_time}s

Event Breakdown:
"""
        for event_type, count in sorted(event_counts.items()):
            report += f"  - {event_type}: {count}\n"
        
        report += f"\n{'='*80}\n"
        
        return report
    
    def export_to_csv(self, output_file: str = None):
        """
        로그를 CSV 형식으로 내보내기
        
        Args:
            output_file: 출력 파일 경로 (None이면 자동 생성)
        """
        if not self.logs:
            return
        
        if output_file is None:
            output_file = self.log_file.replace('.jsonl', '.csv')
        
        import csv
        
        # 모든 키 수집
        all_keys = set()
        for log in self.logs:
            all_keys.update(log.keys())
        
        # CSV 작성
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(self.logs)
        
        print(f"✓ 타임스탬프 로그 CSV 저장: {output_file}")


class LogAnalyzer:
    """로그 분석 도구"""
    
    @staticmethod
    def load_logs(log_file: str) -> List[Dict]:
        """JSONL 로그 파일 로드"""
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                logs.append(json.loads(line.strip()))
        return logs
    
    @staticmethod
    def analyze_decision_timeline(logs: List[Dict]) -> Dict[str, Any]:
        """의사결정 타임라인 분석"""
        assignments = [log for log in logs if log.get('event_type') == 'assignment']
        
        if not assignments:
            return {}
        
        # 시간대별 할당 수
        time_distribution = {}
        for log in assignments:
            t = log['time_step']
            time_bin = (t // 60) * 60  # 1분 단위
            time_distribution[time_bin] = time_distribution.get(time_bin, 0) + 1
        
        return {
            'total_assignments': len(assignments),
            'time_distribution': time_distribution,
            'first_assignment': min(a['time_step'] for a in assignments),
            'last_assignment': max(a['time_step'] for a in assignments)
        }
    
    @staticmethod
    def compare_algorithms(log_files: Dict[str, str]) -> str:
        """여러 알고리즘 로그 비교"""
        comparison = "ALGORITHM COMPARISON\n" + "="*80 + "\n\n"
        
        for algo, log_file in log_files.items():
            logs = LogAnalyzer.load_logs(log_file)
            timeline = LogAnalyzer.analyze_decision_timeline(logs)
            
            comparison += f"{algo}:\n"
            comparison += f"  Total Decisions: {timeline.get('total_assignments', 0)}\n"
            comparison += f"  Decision Period: T={timeline.get('first_assignment', 0)}s ~ T={timeline.get('last_assignment', 0)}s\n"
            comparison += "\n"
        
        return comparison


# 사용 예시
if __name__ == "__main__":
    # 로거 생성
    logger = TimestampLogger("DWTA_BALANCED", "MIP")
    
    # 최적화 로그 예시
    logger.log_optimization(5, {
        'event_type': 'optimization_start',
        'num_threats': 2,
        'num_variables': 40,
        'num_constraints': 120
    })
    
    # 할당 결정 로그 예시
    logger.log_assignment_decision(
        time_step=5,
        threat_id="T01",
        asset_id="A01",
        upper_system="LSAM_01",
        lower_system="MSAM_01",
        decision_metrics={
            'survival_probability': 0.98,
            'expected_loss': 30.0,
            'k_factor': 0.95
        }
    )
    
    # 요약 보고서
    print(logger.generate_summary_report())
    
    # CSV 내보내기
    logger.export_to_csv()
