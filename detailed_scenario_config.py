"""
Detailed Scenario Configuration
===============================
위협별 세밀한 타임라인 설계를 위한 확장 설정
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

@dataclass
class ThreatPhase:
    """위협 단계별 상세 정보"""
    phase_name: str
    start_time: int  # 초
    end_time: int    # 초
    description: str
    threat_level: str  # LOW, MEDIUM, HIGH, CRITICAL

@dataclass
class DetailedThreatEvent:
    """세밀한 위협 이벤트 정의"""
    threat_id: str
    event_type: str  # LAUNCH, MIDCOURSE, TERMINAL, IMPACT, RETARGET
    event_time: int  # 초
    event_description: str
    coordinates: Tuple[float, float]  # (x, y)
    altitude_km: float
    velocity_ms: float
    additional_data: Dict = None

class ScenarioPhases(Enum):
    """시나리오 단계"""
    PREPARATION = "preparation"      # T-300 ~ T+0: 준비 단계
    FIRST_WAVE = "first_wave"       # T+0 ~ T+120: 1차 공격파
    TRANSITION = "transition"        # T+120 ~ T+180: 전환 단계  
    SECOND_WAVE = "second_wave"     # T+180 ~ T+300: 2차 공격파
    CLEANUP = "cleanup"             # T+300 ~ T+600: 정리 단계

class DetailedScenarioConfig:
    """세밀한 시나리오 설정"""
    
    @staticmethod
    def get_scenario_phases() -> List[ThreatPhase]:
        """시나리오 단계별 정보"""
        return [
            ThreatPhase("준비단계", -300, 0, "방어시스템 준비 및 감시체계 가동", "LOW"),
            ThreatPhase("1차 공격파", 0, 120, "노동 미사일 8발 순차 발사", "HIGH"),
            ThreatPhase("전환단계", 120, 180, "1차파 요격 및 2차파 준비", "MEDIUM"),
            ThreatPhase("2차 공격파", 180, 300, "Scud-B 미사일 7발 집중 발사", "CRITICAL"),
            ThreatPhase("정리단계", 300, 600, "잔여 위협 처리 및 피해 평가", "MEDIUM")
        ]
    
    @staticmethod
    def get_detailed_threat_timeline() -> List[DetailedThreatEvent]:
        """위협별 세밀한 타임라인"""
        events = []
        
        # 1차 공격파 - 노동 미사일 (15초 간격 순차 발사)
        nodong_threats = [
            ("T01", "A01", 0, (0, 150), 480),
            ("T02", "A02", 15, (-20, 140), 465),
            ("T03", "A04", 30, (25, 160), 450),
            ("T04", "A06", 45, (10, 145), 470),
            ("T05", "A08", 60, (15, 155), 485),
            ("T06", "A09", 75, (-15, 135), 460),
            ("T07", "A10", 90, (30, 165), 475),
            ("T08", "A05", 105, (-10, 150), 455)
        ]
        
        for threat_id, target, launch_time, launch_pos, flight_time in nodong_threats:
            # 발사 이벤트
            events.append(DetailedThreatEvent(
                threat_id=threat_id,
                event_type="LAUNCH",
                event_time=launch_time,
                event_description=f"노동 미사일 {threat_id} 발사 → {target}",
                coordinates=launch_pos,
                altitude_km=0.0,
                velocity_ms=0.0,
                additional_data={"target": target, "missile_type": "NODONG"}
            ))
            
            # 중간 코스 이벤트 (발사 후 1/3 지점)
            midcourse_time = launch_time + flight_time // 3
            events.append(DetailedThreatEvent(
                threat_id=threat_id,
                event_type="MIDCOURSE",
                event_time=midcourse_time,
                event_description=f"{threat_id} 중간 코스 진입",
                coordinates=(launch_pos[0] * 0.7, launch_pos[1] * 0.7),
                altitude_km=45.0,
                velocity_ms=1200.0,
                additional_data={"phase": "midcourse", "optimal_intercept_window": True}
            ))
            
            # 터미널 단계 이벤트 (발사 후 2/3 지점)
            terminal_time = launch_time + (flight_time * 2) // 3
            events.append(DetailedThreatEvent(
                threat_id=threat_id,
                event_type="TERMINAL",
                event_time=terminal_time,
                event_description=f"{threat_id} 터미널 단계 진입",
                coordinates=(launch_pos[0] * 0.3, launch_pos[1] * 0.3),
                altitude_km=15.0,
                velocity_ms=1800.0,
                additional_data={"phase": "terminal", "last_intercept_chance": True}
            ))
            
            # 예상 충돌 이벤트
            impact_time = launch_time + flight_time
            events.append(DetailedThreatEvent(
                threat_id=threat_id,
                event_type="IMPACT",
                event_time=impact_time,
                event_description=f"{threat_id} 예상 충돌 시점",
                coordinates=(0, 0),  # 목표 좌표
                altitude_km=0.0,
                velocity_ms=2000.0,
                additional_data={"target": target, "criticality": "HIGH"}
            ))
        
        # 2차 공격파 - Scud-B 미사일 (15초 간격 집중 발사)
        scud_threats = [
            ("T09", "A03", 120, (5, 80), 240),
            ("T10", "A07", 135, (-8, 75), 235),
            ("T11", "A01", 150, (12, 85), 245),
            ("T12", "A02", 165, (-12, 70), 230),
            ("T13", "A04", 180, (18, 90), 250),
            ("T14", "A06", 195, (-5, 65), 225),
            ("T15", "A08", 210, (8, 78), 240)
        ]
        
        for threat_id, target, launch_time, launch_pos, flight_time in scud_threats:
            # 발사 이벤트
            events.append(DetailedThreatEvent(
                threat_id=threat_id,
                event_type="LAUNCH",
                event_time=launch_time,
                event_description=f"Scud-B 미사일 {threat_id} 발사 → {target}",
                coordinates=launch_pos,
                altitude_km=0.0,
                velocity_ms=0.0,
                additional_data={"target": target, "missile_type": "SCUD_B"}
            ))
            
            # 중간 코스 (더 짧은 비행시간)
            midcourse_time = launch_time + flight_time // 2
            events.append(DetailedThreatEvent(
                threat_id=threat_id,
                event_type="MIDCOURSE",
                event_time=midcourse_time,
                event_description=f"{threat_id} 중간 코스",
                coordinates=(launch_pos[0] * 0.5, launch_pos[1] * 0.5),
                altitude_km=25.0,
                velocity_ms=800.0,
                additional_data={"phase": "midcourse"}
            ))
            
            # 예상 충돌
            impact_time = launch_time + flight_time
            events.append(DetailedThreatEvent(
                threat_id=threat_id,
                event_type="IMPACT",
                event_time=impact_time,
                event_description=f"{threat_id} 예상 충돌",
                coordinates=(0, 0),
                altitude_km=0.0,
                velocity_ms=1200.0,
                additional_data={"target": target, "criticality": "CRITICAL"}
            ))
        
        # 시간순 정렬
        events.sort(key=lambda x: x.event_time)
        return events
    
    @staticmethod
    def get_critical_decision_points() -> List[Dict]:
        """중요 의사결정 시점"""
        return [
            {
                "time": 0,
                "event": "1차 공격파 시작",
                "decision": "상층 방어체계 활성화",
                "priority": "HIGH"
            },
            {
                "time": 60,
                "event": "1차파 중간 시점",
                "decision": "자원 재배치 검토",
                "priority": "MEDIUM"
            },
            {
                "time": 120,
                "event": "2차 공격파 시작",
                "decision": "하층 방어체계 집중 운용",
                "priority": "CRITICAL"
            },
            {
                "time": 180,
                "event": "최대 위협 시점",
                "decision": "모든 가용 자원 투입",
                "priority": "CRITICAL"
            },
            {
                "time": 300,
                "event": "주요 위협 종료",
                "decision": "피해 평가 및 복구",
                "priority": "MEDIUM"
            }
        ]
    
    @staticmethod
    def get_retargeting_scenarios() -> List[Dict]:
        """재목표 설정 시나리오"""
        return [
            {
                "time": 150,
                "threat_id": "T05",
                "original_target": "A08",
                "new_target": "A04",
                "reason": "controlled_retargeting",
                "probability": 0.3
            },
            {
                "time": 200,
                "threat_id": "T10", 
                "original_target": "A07",
                "new_target": "A06",
                "reason": "random_retargeting",
                "probability": 0.1
            }
        ]

# 사용 예시
if __name__ == "__main__":
    config = DetailedScenarioConfig()
    
    print("=== 시나리오 단계 ===")
    for phase in config.get_scenario_phases():
        print(f"{phase.phase_name}: T{phase.start_time}~T{phase.end_time} ({phase.threat_level})")
        print(f"  {phase.description}")
    
    print("\n=== 세밀한 위협 타임라인 ===")
    events = config.get_detailed_threat_timeline()
    for event in events[:10]:  # 처음 10개만 출력
        print(f"T+{event.event_time:3d}s: {event.event_description}")
    
    print(f"\n총 {len(events)}개 이벤트 정의됨")
