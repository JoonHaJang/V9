# defense_gap_analyzer.py
"""
방어 공백 시간 측정 모듈
특정 중요 자산이 어떠한 포대에도 할당되지 않은 시간의 총합을 계산
"""

import numpy as np
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import json
from datetime import datetime

@dataclass
class DefenseGapRecord:
    """방어 공백 기록"""
    asset_id: str
    start_time: int
    end_time: int
    duration: int
    threat_ids: List[str]
    asset_value: float
    gap_severity: str  # "critical", "high", "medium", "low"

@dataclass
class ThreatCoverageRecord:
    """위협 커버리지 기록"""
    time_step: int
    threat_id: str
    asset_id: str
    assigned_systems: List[str]
    is_covered: bool

class DefenseGapAnalyzer:
    """방어 공백 분석기"""
    
    def __init__(self):
        self.coverage_history = []
        self.gap_records = []
        self.asset_values = {}
        self.time_step_coverage = defaultdict(dict)
        
    def record_coverage(self, time_step: int, active_threats: Dict[str, str], 
                       assignments: Dict[str, List[str]], asset_values: Dict[str, float]):
        """커버리지 상태 기록"""
        self.asset_values.update(asset_values)
        
        # 위협별 할당 상태 역매핑
        threat_assignments = defaultdict(list)
        for system_id, assigned_threats in assignments.items():
            for threat_id in assigned_threats:
                threat_assignments[threat_id].append(system_id)
        
        # 각 위협에 대한 커버리지 기록
        for threat_id, asset_id in active_threats.items():
            assigned_systems = threat_assignments.get(threat_id, [])
            is_covered = len(assigned_systems) > 0
            
            record = ThreatCoverageRecord(
                time_step=time_step,
                threat_id=threat_id,
                asset_id=asset_id,
                assigned_systems=assigned_systems,
                is_covered=is_covered
            )
            
            self.coverage_history.append(record)
            
            # 시간별 커버리지 상태 저장
            if asset_id not in self.time_step_coverage[time_step]:
                self.time_step_coverage[time_step][asset_id] = {
                    'threats': [],
                    'covered_threats': [],
                    'uncovered_threats': []
                }
            
            self.time_step_coverage[time_step][asset_id]['threats'].append(threat_id)
            
            if is_covered:
                self.time_step_coverage[time_step][asset_id]['covered_threats'].append(threat_id)
            else:
                self.time_step_coverage[time_step][asset_id]['uncovered_threats'].append(threat_id)
    
    def analyze_defense_gaps(self, total_simulation_time: int) -> Dict:
        """방어 공백 분석 수행"""
        if not self.time_step_coverage:
            return self._empty_analysis_result()
        
        # 자산별 방어 공백 구간 찾기
        asset_gaps = defaultdict(list)
        
        for asset_id in self.asset_values.keys():
            gaps = self._find_asset_defense_gaps(asset_id, total_simulation_time)
            asset_gaps[asset_id] = gaps
        
        # 전체 통계 계산
        total_gap_time = 0
        critical_gaps = []
        high_value_gaps = []
        
        for asset_id, gaps in asset_gaps.items():
            asset_value = self.asset_values.get(asset_id, 0)
            
            for gap in gaps:
                total_gap_time += gap.duration
                
                # 심각도 분류
                if gap.gap_severity == "critical":
                    critical_gaps.append(gap)
                
                if asset_value >= 900:  # 고가치 자산
                    high_value_gaps.append(gap)
        
        # 결과 구성
        result = {
            "total_gap_time": total_gap_time,
            "gap_percentage": (total_gap_time / max(total_simulation_time, 1)) * 100,
            "asset_gaps": dict(asset_gaps),
            "critical_gaps_count": len(critical_gaps),
            "high_value_gaps_count": len(high_value_gaps),
            "statistics": self._calculate_gap_statistics(asset_gaps),
            "severity_breakdown": self._calculate_severity_breakdown(asset_gaps),
            "recommendations": self._generate_recommendations(asset_gaps)
        }
        
        return result
    
    def _find_asset_defense_gaps(self, asset_id: str, total_time: int) -> List[DefenseGapRecord]:
        """특정 자산의 방어 공백 구간 찾기"""
        gaps = []
        current_gap_start = None
        current_gap_threats = set()
        
        for time_step in range(total_time):
            coverage_data = self.time_step_coverage.get(time_step, {}).get(asset_id, {})
            uncovered_threats = coverage_data.get('uncovered_threats', [])
            
            if uncovered_threats:
                # 방어 공백 시작 또는 지속
                if current_gap_start is None:
                    current_gap_start = time_step
                    current_gap_threats = set(uncovered_threats)
                else:
                    current_gap_threats.update(uncovered_threats)
            else:
                # 방어 공백 종료
                if current_gap_start is not None:
                    gap_duration = time_step - current_gap_start
                    
                    if gap_duration > 0:  # 최소 1 시간 단위 공백만 기록
                        gap_record = DefenseGapRecord(
                            asset_id=asset_id,
                            start_time=current_gap_start,
                            end_time=time_step - 1,
                            duration=gap_duration,
                            threat_ids=list(current_gap_threats),
                            asset_value=self.asset_values.get(asset_id, 0),
                            gap_severity=self._calculate_gap_severity(
                                gap_duration, len(current_gap_threats), 
                                self.asset_values.get(asset_id, 0)
                            )
                        )
                        gaps.append(gap_record)
                    
                    current_gap_start = None
                    current_gap_threats.clear()
        
        # 시뮬레이션 끝까지 공백이 지속된 경우
        if current_gap_start is not None:
            gap_duration = total_time - current_gap_start
            gap_record = DefenseGapRecord(
                asset_id=asset_id,
                start_time=current_gap_start,
                end_time=total_time - 1,
                duration=gap_duration,
                threat_ids=list(current_gap_threats),
                asset_value=self.asset_values.get(asset_id, 0),
                gap_severity=self._calculate_gap_severity(
                    gap_duration, len(current_gap_threats), 
                    self.asset_values.get(asset_id, 0)
                )
            )
            gaps.append(gap_record)
        
        return gaps
    
    def _calculate_gap_severity(self, duration: int, threat_count: int, asset_value: float) -> str:
        """방어 공백 심각도 계산"""
        # 점수 기반 심각도 계산
        severity_score = 0
        
        # 지속 시간 점수 (최대 40점)
        if duration >= 50:
            severity_score += 40
        elif duration >= 20:
            severity_score += 30
        elif duration >= 10:
            severity_score += 20
        else:
            severity_score += duration
        
        # 위협 수 점수 (최대 30점)
        severity_score += min(threat_count * 10, 30)
        
        # 자산 가치 점수 (최대 30점)
        if asset_value >= 1000:
            severity_score += 30
        elif asset_value >= 900:
            severity_score += 25
        elif asset_value >= 500:
            severity_score += 15
        else:
            severity_score += 5
        
        # 심각도 분류
        if severity_score >= 80:
            return "critical"
        elif severity_score >= 60:
            return "high"
        elif severity_score >= 30:
            return "medium"
        else:
            return "low"
    
    def _calculate_gap_statistics(self, asset_gaps: Dict) -> Dict:
        """방어 공백 통계 계산"""
        all_gaps = []
        for gaps in asset_gaps.values():
            all_gaps.extend(gaps)
        
        if not all_gaps:
            return {"count": 0, "avg_duration": 0, "max_duration": 0, "total_threats": 0}
        
        durations = [gap.duration for gap in all_gaps]
        threat_counts = [len(gap.threat_ids) for gap in all_gaps]
        
        return {
            "count": len(all_gaps),
            "avg_duration": np.mean(durations),
            "max_duration": max(durations),
            "min_duration": min(durations),
            "std_duration": np.std(durations),
            "total_threats_affected": sum(threat_counts),
            "avg_threats_per_gap": np.mean(threat_counts),
            "assets_with_gaps": len([gaps for gaps in asset_gaps.values() if gaps])
        }
    
    def _calculate_severity_breakdown(self, asset_gaps: Dict) -> Dict:
        """심각도별 분류 통계"""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        severity_durations = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for gaps in asset_gaps.values():
            for gap in gaps:
                severity_counts[gap.gap_severity] += 1
                severity_durations[gap.gap_severity] += gap.duration
        
        return {
            "counts": severity_counts,
            "total_durations": severity_durations,
            "percentages": {
                severity: (count / max(sum(severity_counts.values()), 1)) * 100
                for severity, count in severity_counts.items()
            }
        }
    
    def _generate_recommendations(self, asset_gaps: Dict) -> List[str]:
        """개선 권고사항 생성"""
        recommendations = []
        
        # 심각한 공백이 있는 자산들
        critical_assets = []
        for asset_id, gaps in asset_gaps.items():
            critical_gaps = [g for g in gaps if g.gap_severity in ["critical", "high"]]
            if critical_gaps:
                critical_assets.append((asset_id, len(critical_gaps), sum(g.duration for g in critical_gaps)))
        
        if critical_assets:
            # 가장 심각한 자산 3개
            critical_assets.sort(key=lambda x: x[2], reverse=True)
            top_critical = critical_assets[:3]
            
            recommendations.append(
                f"긴급 조치 필요: {', '.join([asset[0] for asset in top_critical])} 자산의 방어 공백 해결"
            )
        
        # 전체적인 권고사항
        total_gaps = sum(len(gaps) for gaps in asset_gaps.values())
        if total_gaps > 10:
            recommendations.append("포대 배치 재검토 또는 추가 방어 시스템 도입 검토")
        
        if total_gaps > 5:
            recommendations.append("동적 재할당 알고리즘 최적화 필요")
        
        # 고가치 자산 보호 강화
        high_value_gaps = []
        for asset_id, gaps in asset_gaps.items():
            if self.asset_values.get(asset_id, 0) >= 900 and gaps:
                high_value_gaps.append(asset_id)
        
        if high_value_gaps:
            recommendations.append(f"고가치 자산 {', '.join(high_value_gaps)} 우선 방어 체계 강화")
        
        return recommendations if recommendations else ["현재 방어 체계가 적절히 운용되고 있습니다"]
    
    def _empty_analysis_result(self) -> Dict:
        """빈 분석 결과"""
        return {
            "total_gap_time": 0,
            "gap_percentage": 0.0,
            "asset_gaps": {},
            "critical_gaps_count": 0,
            "high_value_gaps_count": 0,
            "statistics": {"count": 0, "avg_duration": 0, "max_duration": 0, "total_threats": 0},
            "severity_breakdown": {"counts": {"critical": 0, "high": 0, "medium": 0, "low": 0}},
            "recommendations": ["분석할 데이터가 없습니다"]
        }
    
    def save_analysis_results(self, results: Dict, filename: str = None) -> str:
        """분석 결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"defense_gap_analysis_{timestamp}.json"
        
        # JSON 직렬화 가능한 형태로 변환
        serializable_results = self._make_json_serializable(results)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"Defense gap analysis saved to: {filename}")
        return filename
    
    def _make_json_serializable(self, obj):
        """JSON 직렬화 가능한 형태로 변환"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, DefenseGapRecord):
            return {
                'asset_id': obj.asset_id,
                'start_time': obj.start_time,
                'end_time': obj.end_time,
                'duration': obj.duration,
                'threat_ids': obj.threat_ids,
                'asset_value': obj.asset_value,
                'gap_severity': obj.gap_severity
            }
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    def print_analysis_summary(self, results: Dict):
        """분석 결과 요약 출력"""
        print("\n" + "="*60)
        print("DEFENSE GAP ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"Total Gap Time: {results['total_gap_time']} time steps")
        print(f"Gap Percentage: {results['gap_percentage']:.2f}%")
        print(f"Critical Gaps: {results['critical_gaps_count']}")
        print(f"High-Value Asset Gaps: {results['high_value_gaps_count']}")
        
        print("\nSeverity Breakdown:")
        for severity, count in results['severity_breakdown']['counts'].items():
            percentage = results['severity_breakdown']['percentages'][severity]
            print(f"  {severity.capitalize()}: {count} ({percentage:.1f}%)")
        
        print("\nStatistics:")
        stats = results['statistics']
        print(f"  Total Gap Events: {stats['count']}")
        if stats['count'] > 0:
            print(f"  Average Duration: {stats['avg_duration']:.1f} time steps")
            print(f"  Maximum Duration: {stats['max_duration']} time steps")
            print(f"  Assets Affected: {stats['assets_with_gaps']}")
        
        print("\nRecommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")
        print()

# 테스트 함수
def test_defense_gap_analyzer():
    """방어 공백 분석기 테스트"""
    analyzer = DefenseGapAnalyzer()
    
    # 테스트 데이터
    asset_values = {"ASSET_01": 1000, "ASSET_02": 500, "ASSET_03": 800}
    
    # 시뮬레이션 데이터 생성
    for time_step in range(100):
        active_threats = {
            f"T{time_step%3+1}": f"ASSET_{(time_step%3)+1:02d}"
        }
        
        # 일부 시간에서 할당 누락 시뮬레이션
        if time_step % 10 < 3:  # 30% 시간 동안 공백
            assignments = {}
        else:
            assignments = {"LSAM_01": [list(active_threats.keys())[0]]}
        
        analyzer.record_coverage(time_step, active_threats, assignments, asset_values)
    
    # 분석 수행
    results = analyzer.analyze_defense_gaps(100)
    analyzer.print_analysis_summary(results)
    
    return results

if __name__ == "__main__":
    test_defense_gap_analyzer()
