"""
config_mip.py
=============
MIP 최적화 전용 설정 파일

기존 config.py를 확장하여 MIP 모델에 특화된 설정들을 관리합니다.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Tuple, Optional, Set
import numpy as np
import itertools
from config import Config as BaseConfig

class MIPSolverConfig(BaseModel):
    """MIP 솔버 설정 (최적해 탐색 우선)"""
    solver_name: str = Field("pulp", description="사용할 솔버 (pulp, gurobi, cplex, ortools)")
    time_limit_sec: int = Field(5, description="솔버 시간 제한 (초) - GUI 응답성 우선 (60→5)")
    gap_tolerance: float = Field(0.01, description="최적성 갭 허용치 - 빠른 해 탐색 (0.0→0.01)")
    threads: int = Field(4, description="병렬 처리 스레드 수 - GUI 응답성 (4)")
    verbose: bool = Field(False, description="상세 로그 출력 여부 - GUI 성능 (True→False)")

class SLSConfig(BaseModel):
    """Shoot-Look-Shoot 설정 (실제 살보 발사 방식)"""
    evaluation_delay_sec: float = Field(3.0, description="살보 발사 간격 (첫발 → 3초 → 둘째발)")
    re_engagement_factor: float = Field(0.9, description="재교전 확률 보정 계수")
    discount_factor: float = Field(0.8, description="예비 교전 할인 계수 (δ)")
    max_engagements_per_target: int = Field(2, description="표적당 최대 교전 횟수 (살보 발사)")

class InterceptorSystemConfig(BaseModel):
    """요격 시스템 상세 스펙 설정"""
    
    @staticmethod
    def get_lsam_specs() -> Dict:
        """L-SAM (장거리 지대공 미사일) 실제 스펙"""
        return {
            "system_type": "LSAM",
            "layer": "UPPER",
            "ballistic_missile_specs": {  # 탄도탄 요격 미사일 (ABM)
                "engagement_altitude_km": {"min": 40, "max": 80},
                "engagement_range_km": {"min": 150, "max": 300},
                "simultaneous_engagements": 10,
                "intercept_probability_single": 0.85,  # 단발 요격 확률
                "intercept_probability_salvo": 0.9775,  # 2발 살보 요격 확률 (1-(1-0.85)^2)
                "missiles_per_engagement": 2  # 살보 미사일 수
            },
            "aircraft_specs": {  # 항공기 요격 미사일 (AAM)
                "engagement_altitude_km": {"min": 40, "max": 80},
                "engagement_range_km": {"min": 150, "max": 300},
                "simultaneous_engagements": 20,  # 추정
                "intercept_probability_single": 0.85,  # 단발 요격 확률
                "intercept_probability_salvo": 0.9775,  # 2발 살보 요격 확률
                "missiles_per_engagement": 2
            },
            "radar_specs": {
                "type": "S-band AESA",
                "aircraft_tracking": 100,
                "ballistic_tracking": 10,
                "detection_range_km": 400
            },
            "battery_config": {
                "launchers": 4,
                "missiles_per_launcher": 6,
                "total_missiles": 24,
                "simultaneous_engagements": 3
            }
        }
    
    @staticmethod
    def get_msam_specs() -> Dict:
        """M-SAM (중거리 지대공 미사일) 실제 스펙 - 한국형 천궁-II"""
        return {
            "system_type": "MSAM",
            "layer": "LOWER",
            "ballistic_specs": {
                "engagement_altitude_km": {"min": 0.05, "max": 50},  # MSAM 고도 확장 (NODONG 조기 교전)
                "engagement_range_km": {"min": 5, "max": 50},
                "simultaneous_engagements": 8,  # 6-8개 표적
                "intercept_probability_single": 0.80,  # 단발 요격 확률
                "intercept_probability_salvo": 0.96,  # 2발 살보 요격 확률 (1-(1-0.80)^2)
                "missiles_per_engagement": 2
            },
            "ballistic_missile_specs": {
                "engagement_altitude_km": {"min": 0.05, "max": 50},  # MSAM 고도 확장 (NODONG 조기 교전)
                "engagement_range_km": {"min": 5, "max": 50},
                "simultaneous_engagements": 10,
                "intercept_probability_single": 0.80,  # 단발 요격 확률
                "intercept_probability_salvo": 0.96,  # 2발 살보 요격 확률
                "missiles_per_engagement": 2
            },
            "radar_specs": {
                "type": "X-band PESA",
                "target_tracking": 40,
                "detection_range_km": 100,
                "rotation_rpm": 40,
                "elevation_coverage": 80
            },
            "battery_config": {
                "launchers": 6,  # 4-6개
                "missiles_per_launcher": 8,
                "total_missiles": 48,
                "simultaneous_engagements": 3
            }
        }

class ProbabilityConfig(BaseModel):
    """교전 타임 윈도우 기반 확률 계산 설정"""
    
    # 기본 요격 확률 (이상적 교전 조건 하)
    base_probabilities: Dict[str, float] = Field(
        default_factory=lambda: {
            "LSAM_ABM": 0.85,    # 상층 탄도탄 요격 (이상적 조건)
            "LSAM_AAM": 0.85,    # 상층 항공기 요격 (이상적 조건)
            "MSAM_AIRCRAFT": 0.78,  # 하층 항공기 요격 (이상적 조건)
            "MSAM_BALLISTIC": 0.78   # 하층 탄도탄 요격 (이상적 조건)
        },
        description="무기체계별 기본 요격 확률 (이상적 교전 조건)"
    )
    
    # 교전 타임 윈도우 모델링 파라미터 (높은 요격률 유지)
    engagement_window_config: Dict[str, Dict] = Field(
        default_factory=lambda: {
            "LSAM": {
                "optimal_window_sec": 35.0,      # 최적 교전 윈도우 (초)
                "minimum_window_sec": 12.0,      # 최소 교전 윈도우 (초)
                "maximum_range_km": 300,         # 최대 교전 거리 (km)
                "optimal_altitude_km": 55,       # 최적 교전 고도 (km) - 40-70km 범위 중앙
                "window_efficiency_factor": 0.95  # 윈도우 효율성 계수 - 높은 요격률 유지
            },
            "MSAM": {
                "optimal_window_sec": 20.0,      # 최적 교전 윈도우 (초)
                "minimum_window_sec": 8.0,       # 최소 교전 윈도우 (초)
                "maximum_range_km": 50,          # 최대 교전 거리 (km)
                "optimal_altitude_km": 12.5,     # 최적 교전 고도 (km) - 10-15km 범위 중앙
                "window_efficiency_factor": 0.92  # 윈도우 효율성 계수 - 높은 요격률 유지
            }
        },
        description="교전 타임 윈도우 모델링 설정 (높은 요격률 유지)"
    )
    
    # 다층 방어 협력 효과 계수
    layered_defense_bonus: Dict[str, float] = Field(
        default_factory=lambda: {
            "upper_lower_coordination": 0.15,  # 상층-하층 협력 보너스
            "sequential_engagement": 0.12,     # 순차적 교전 보너스
            "overlapping_coverage": 0.08       # 중첩 커버리지 보너스
        },
        description="다층 방어 협력 효과"
    )
    
    # 동적 요소 튜닝 계수 (교전 성공률 향상을 위한 조정)
    distance_factor_beta: float = Field(1.2, description="거리 요소 지수 - 완화")
    speed_factor_beta: float = Field(0.4, description="속도 요소 계수 - 완화")
    altitude_factor_gamma: float = Field(0.3, description="고도 요소 계수 - 완화")
    rcs_factor_lambda: float = Field(0.15, description="RCS 요소 계수 - 완화")
    
    # 최소/최대 확률 제한 (높은 요격률 보장)
    min_probability: float = Field(0.45, description="최소 요격 확률 - 높은 요격률 보장")
    max_probability: float = Field(0.98, description="최대 요격 확률")

class BatteryDeploymentConfig(BaseModel):
    """전구 방어 기반 포대 배치 설정 (10개 고정: 상층 5개, 하층 5개)"""
    
    @staticmethod
    def create_battery_deployment() -> List[Dict]:
        """전구 방어 구역 기반 포대 배치 - 각 자산당 전담 상층/하층 시스템 배정"""
        
        # 전구 방어 구역 정의 (중복 제거)
        defense_zones = {
            "ZONE_1_SEOUL": {
                "center": (0, 0),
                "primary_assets": ["A01", "A02", "A03"],  # 청와대, 국방부, 국정원
                "upper_battery": "LSAM_01",
                "lower_battery": "MSAM_01"
            },
            "ZONE_2_GYEONGGI": {
                "center": (-15, 10),
                "primary_assets": ["A07", "A09", "A10"],  # 인천공항, 인천항, 김포공항
                "upper_battery": "LSAM_02",
                "lower_battery": "MSAM_02"
            },
            "ZONE_3_CHUNGNAM": {
                "center": (15, -25),
                "primary_assets": ["A04", "A05"],  # 계룡대, 평택 미군기지
                "upper_battery": "LSAM_03",
                "lower_battery": "MSAM_03"
            },
            "ZONE_4_GYEONGBUK": {
                "center": (40, -35),
                "primary_assets": ["A06"],  # 오산 공군기지
                "upper_battery": "LSAM_04",
                "lower_battery": "MSAM_04"
            },
            "ZONE_5_BUSAN": {
                "center": (55, -70),
                "primary_assets": ["A08"],  # 부산항
                "upper_battery": "LSAM_05",
                "lower_battery": "MSAM_05"
            }
        }
        
        batteries = [
            # 상층 방어 (L-SAM) - 전구 방어 구역별 전담 배치
            {
                "id": "LSAM_01",
                "name": "Seoul_Theater_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (0, 0),  # 서울 전구 방어 구역
                "coverage_radius_km": 150,  # 전구 방어: 중복 제거로 반경 축소
                "defense_zone": "ZONE_1_SEOUL",
                "dedicated_assets": ["A01", "A02", "A03"],
                "specs": InterceptorSystemConfig.get_lsam_specs()
            },
            {
                "id": "LSAM_02",
                "name": "Gyeonggi_Theater_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (-15, 10),  # 경기도 전구 방어 구역
                "coverage_radius_km": 150,  # 전구 방어: 중복 제거로 반경 축소
                "defense_zone": "ZONE_2_GYEONGGI",
                "dedicated_assets": ["A07", "A09", "A10"],
                "specs": InterceptorSystemConfig.get_lsam_specs()
            },
            {
                "id": "LSAM_03",
                "name": "Chungnam_Theater_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (15, -25),  # 충남 전구 방어 구역
                "coverage_radius_km": 150,  # 전구 방어: 중복 제거로 반경 축소
                "defense_zone": "ZONE_3_CHUNGNAM",
                "dedicated_assets": ["A04", "A05"],
                "specs": InterceptorSystemConfig.get_lsam_specs()
            },
            {
                "id": "LSAM_04",
                "name": "Gyeongbuk_Theater_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (40, -35),  # 경북 전구 방어 구역
                "coverage_radius_km": 150,  # 전구 방어: 중복 제거로 반경 축소
                "defense_zone": "ZONE_4_GYEONGBUK",
                "dedicated_assets": ["A06"],
                "specs": InterceptorSystemConfig.get_lsam_specs()
            },
            {
                "id": "LSAM_05",
                "name": "Busan_Theater_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (55, -70),  # 부산 전구 방어 구역
                "coverage_radius_km": 150,  # 전구 방어: 중복 제거로 반경 축소
                "defense_zone": "ZONE_5_BUSAN",
                "dedicated_assets": ["A08"],
                "specs": InterceptorSystemConfig.get_lsam_specs()
            },
            
            # 하층 방어 (M-SAM) - 전구 방어 구역별 전담 배치
            {
                "id": "MSAM_01",
                "name": "Seoul_Theater_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (7, -5),  # 서울 전구 방어 구역 (최종 방어선)
                "coverage_radius_km": 40,  # 전구 방어: 정밀 방어를 위한 반경 조정
                "defense_zone": "ZONE_1_SEOUL",
                "dedicated_assets": ["A01", "A02", "A03"],
                "specs": InterceptorSystemConfig.get_msam_specs()
            },
            {
                "id": "MSAM_02",
                "name": "Gyeonggi_Theater_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (-20, 15),  # 경기도 전구 방어 구역 (최종 방어선)
                "coverage_radius_km": 40,  # 전구 방어: 정밀 방어를 위한 반경 조정
                "defense_zone": "ZONE_2_GYEONGGI",
                "dedicated_assets": ["A07", "A09", "A10"],
                "specs": InterceptorSystemConfig.get_msam_specs()
            },
            {
                "id": "MSAM_03",
                "name": "Chungnam_Theater_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (20, -30),  # 충남 전구 방어 구역 (최종 방어선)
                "coverage_radius_km": 40,  # 전구 방어: 정밀 방어를 위한 반경 조정
                "defense_zone": "ZONE_3_CHUNGNAM",
                "dedicated_assets": ["A04", "A05"],
                "specs": InterceptorSystemConfig.get_msam_specs()
            },
            {
                "id": "MSAM_04",
                "name": "Gyeongbuk_Theater_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (45, -40),  # 경북 전구 방어 구역 (최종 방어선)
                "coverage_radius_km": 40,  # 전구 방어: 정밀 방어를 위한 반경 조정
                "defense_zone": "ZONE_4_GYEONGBUK",
                "dedicated_assets": ["A06"],
                "specs": InterceptorSystemConfig.get_msam_specs()
            },
            {
                "id": "MSAM_05",
                "name": "Busan_Theater_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (60, -75),  # 부산 전구 방어 구역 (최종 방어선)
                "coverage_radius_km": 40,  # 전구 방어: 정밀 방어를 위한 반경 조정
                "defense_zone": "ZONE_5_BUSAN",
                "dedicated_assets": ["A08"],
                "specs": InterceptorSystemConfig.get_msam_specs()
            }
        ]
        return batteries


class AssetConfig(BaseModel):
    """방어 자산 설정 (10개 선택 - 우선순위 기반)"""
    
    @staticmethod
    def create_priority_defense_assets() -> List[Dict]:
        """우선순위 기반 주요 방어 자산 10개 선택"""
        # 전략적 가치 재정의: 군사적 중요도와 전시 운용 가치 반영
        assets = [
            # 최고 우선순위 (Priority 1) - 국가 중추 기관
            {"id": "A01", "name": "Blue_House", "position": (0, 0), "value": 1500, "priority": 1},  # 국가 상징성 강화
            {"id": "A02", "name": "Defense_Ministry", "position": (2, -1), "value": 900, "priority": 1},
            {"id": "A03", "name": "Intelligence_Service", "position": (-3, 1), "value": 850, "priority": 1},
            
            # 높은 우선순위 (Priority 2) - 전략적 가치 순 재정렬
            {"id": "A04", "name": "Gyeryong_Command", "position": (15, -25), "value": 950, "priority": 2},  # 군 지휘부 최고 우선순위
            {"id": "A05", "name": "Pyeongtaek_US_Base", "position": (5, -15), "value": 900, "priority": 2},  # 동맹 군사기지 강화
            {"id": "A06", "name": "Osan_Air_Base", "position": (8, -20), "value": 850, "priority": 2},  # 공군 작전 기지
            {"id": "A07", "name": "Incheon_Airport", "position": (-25, 15), "value": 800, "priority": 2},  # 국제 공항
            {"id": "A08", "name": "Busan_Port", "position": (50, -80), "value": 750, "priority": 2},  # 주요 항구
            {"id": "A09", "name": "Incheon_Port", "position": (-20, 10), "value": 700, "priority": 2},  # 수도권 항구
            {"id": "A10", "name": "Gimpo_Airport", "position": (-10, 5), "value": 650, "priority": 2}   # 국내 공항
        ]
        
        # 우선순위별 가중치 적용
        priority_weights = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4}
        for asset in assets:
            asset["weighted_value"] = asset["value"] * priority_weights[asset["priority"]]
        return assets

class ThreatMissileConfig(BaseModel):
    """위협 미사일 설정 (15발 탄도탄)"""
    
    @staticmethod
    def create_ballistic_missile_threats() -> List[Dict]:
        """세밀한 시간 기반 북한 탄도탄 15발 시나리오 (노동 + Scud-B)"""
        threats = [
            # === 1차 공격파 (노동 미사일) - 8발 ===
            # 15초 간격 순차 발사, 장거리 탄도탄으로 8분 비행시간 (최소 80km 거리 보장)
            {"id": "T01", "name": "Nodong_1", "type": "NODONG", 
             "target_asset_id": "A01", "launch_time": 0, "flight_time": 480,
             "launch_position": (0, 180), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 160,    # 발사 후 1/3 지점 (최적 요격 구간)
                 "terminal_time": 320,     # 발사 후 2/3 지점 (마지막 요격 기회)
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800
             }},
            {"id": "T02", "name": "Nodong_2", "type": "NODONG", 
             "target_asset_id": "A02", "launch_time": 15, "flight_time": 465,
             "launch_position": (-30, 170), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 170,
                 "terminal_time": 325,
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800
             }},
            {"id": "T03", "name": "Nodong_3", "type": "NODONG", 
             "target_asset_id": "A04", "launch_time": 30, "flight_time": 450,
             "launch_position": (35, 190), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 180,
                 "terminal_time": 330,
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800
             }},
            {"id": "T04", "name": "Nodong_4", "type": "NODONG", 
             "target_asset_id": "A06", "launch_time": 45, "flight_time": 470,
             "launch_position": (15, 175), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 202,
                 "terminal_time": 358,
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800
             }},
            {"id": "T05", "name": "Nodong_5", "type": "NODONG", 
             "target_asset_id": "A08", "launch_time": 60, "flight_time": 485,
             "launch_position": (20, 185), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 222,
                 "terminal_time": 383,
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800,
                 "retarget_opportunity": 150  # T+150초에 재목표 가능성
             }},
            {"id": "T06", "name": "Nodong_6", "type": "NODONG", 
             "target_asset_id": "A09", "launch_time": 75, "flight_time": 460,
             "launch_position": (-25, 165), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 228,
                 "terminal_time": 382,
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800
             }},
            {"id": "T07", "name": "Nodong_7", "type": "NODONG", 
             "target_asset_id": "A10", "launch_time": 90, "flight_time": 475,
             "launch_position": (40, 195), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 248,
                 "terminal_time": 407,
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800
             }},
            {"id": "T08", "name": "Nodong_8", "type": "NODONG", 
             "target_asset_id": "A05", "launch_time": 105, "flight_time": 455,
             "launch_position": (-15, 180), "trajectory_type": "ballistic", "rcs": 1.5,
             "phase_events": {
                 "midcourse_time": 257,
                 "terminal_time": 408,
                 "critical_altitude_km": 45.0,
                 "terminal_velocity_ms": 1800
             }},
             
            # === 2차 공격파 (Scud-B 미사일) - 7발 ===
            # 15초 간격 집중 발사, 단거리 탄도탄으로 4분 비행시간 (최소 80km 거리 보장)
            {"id": "T09", "name": "ScudB_1", "type": "SCUD_B", 
             "target_asset_id": "A03", "launch_time": 120, "flight_time": 240,
             "launch_position": (10, 110), "trajectory_type": "ballistic", "rcs": 0.8,
             "phase_events": {
                 "midcourse_time": 240,    # 중간 코스 (더 짧은 비행시간)
                 "terminal_time": 300,     # 터미널 단계
                 "critical_altitude_km": 25.0,
                 "terminal_velocity_ms": 1200
             }},
            {"id": "T10", "name": "ScudB_2", "type": "SCUD_B", 
             "target_asset_id": "A07", "launch_time": 135, "flight_time": 235,
             "launch_position": (-15, 105), "trajectory_type": "ballistic", "rcs": 0.8,
             "phase_events": {
                 "midcourse_time": 252,
                 "terminal_time": 313,
                 "critical_altitude_km": 25.0,
                 "terminal_velocity_ms": 1200,
                 "retarget_opportunity": 200  # T+200초에 재목표 가능성
             }},
            {"id": "T11", "name": "ScudB_3", "type": "SCUD_B", 
             "target_asset_id": "A01", "launch_time": 150, "flight_time": 245,
             "launch_position": (20, 115), "trajectory_type": "ballistic", "rcs": 0.8,
             "phase_events": {
                 "midcourse_time": 272,
                 "terminal_time": 333,
                 "critical_altitude_km": 25.0,
                 "terminal_velocity_ms": 1200
             }},
            {"id": "T12", "name": "ScudB_4", "type": "SCUD_B", 
             "target_asset_id": "A02", "launch_time": 165, "flight_time": 230,
             "launch_position": (-20, 100), "trajectory_type": "ballistic", "rcs": 0.8,
             "phase_events": {
                 "midcourse_time": 280,
                 "terminal_time": 342,
                 "critical_altitude_km": 25.0,
                 "terminal_velocity_ms": 1200
             }},
            {"id": "T13", "name": "ScudB_5", "type": "SCUD_B", 
             "target_asset_id": "A04", "launch_time": 180, "flight_time": 250,
             "launch_position": (25, 120), "trajectory_type": "ballistic", "rcs": 0.8,
             "phase_events": {
                 "midcourse_time": 305,
                 "terminal_time": 363,
                 "critical_altitude_km": 25.0,
                 "terminal_velocity_ms": 1200
             }},
            {"id": "T14", "name": "ScudB_6", "type": "SCUD_B", 
             "target_asset_id": "A06", "launch_time": 195, "flight_time": 225,
             "launch_position": (-10, 95), "trajectory_type": "ballistic", "rcs": 0.8,
             "phase_events": {
                 "midcourse_time": 307,
                 "terminal_time": 363,
                 "critical_altitude_km": 25.0,
                 "terminal_velocity_ms": 1200
             }},
            {"id": "T15", "name": "ScudB_7", "type": "SCUD_B", 
             "target_asset_id": "A08", "launch_time": 210, "flight_time": 240,
             "launch_position": (15, 108), "trajectory_type": "ballistic", "rcs": 0.8,
             "phase_events": {
                 "midcourse_time": 330,
                 "terminal_time": 390,
                 "critical_altitude_km": 25.0,
                 "terminal_velocity_ms": 1200
             }}
        ]
        
        # 실제 미사일별 스펙 추가 (노동 + Scud-B)
        missile_specs = {
            "NODONG": {
                "max_range_km": 1300,      # 노동 미사일 실제 사거리
                "max_altitude_km": 80,      # 탄도궤적 최대 고도 (추정)
                "speed_mach": 3.5,          # 마하 3-4 (현실적 속도)
                "payload_kg": 800,          # 실제 페이로드
                "cep_m": 2000,              # 원형공산오차 2km
                "launch_weight_kg": 16500   # 발사중량
            },
            "SCUD_B": {
                "max_range_km": 300,        # Scud-B 실제 사거리
                "max_altitude_km": 40,       # 탄도궤적 최대 고도
                "speed_mach": 2.5,          # 마하 2-3 (현실적 속도)
                "payload_kg": 985,          # 실제 페이로드
                "cep_m": 450,               # 원형공산오차 450m
                "launch_weight_kg": 5900    # 발사중량
            }
        }
        
        # 위협별 세밀한 타임라인 정보 추가
        for threat in threats:
            threat["specs"] = missile_specs[threat["type"]]
            threat["estimated_impact_time"] = threat["launch_time"] + threat["flight_time"]
            
            # 단계별 이벤트 시간 계산
            if "phase_events" in threat:
                events = threat["phase_events"]
                threat["midcourse_absolute_time"] = threat["launch_time"] + events["midcourse_time"]
                threat["terminal_absolute_time"] = threat["launch_time"] + events["terminal_time"]
                
                # 최적 요격 윈도우 계산 (중간코스 ±30초)
                threat["optimal_intercept_window"] = {
                    "start": threat["midcourse_absolute_time"] - 30,
                    "end": threat["midcourse_absolute_time"] + 30
                }
                
                # 마지막 요격 기회 (터미널 단계 시작)
                threat["last_intercept_time"] = threat["terminal_absolute_time"]
        
        return threats

class LaunchBaseConfig(BaseModel):
    """북한 미사일 발사 기지 설정"""
    
    @staticmethod
    def create_north_korean_bases() -> Dict[str, Dict]:
        """North Korean missile launch bases information"""
        return {
            "Pyongyang": {"coords": (39.0392, 125.7625), "weight": 0.3},
            "Hamhung": {"coords": (39.9180, 127.5360), "weight": 0.2},
            "Wonsan": {"coords": (39.1547, 127.4453), "weight": 0.15},
            "Sinpo": {"coords": (40.1031, 128.1847), "weight": 0.1},
            "Musudan_ri": {"coords": (40.8581, 129.6667), "weight": 0.1},
            "Dongchang_ri": {"coords": (39.6603, 124.7056), "weight": 0.1},
            "Cheolsan": {"coords": (39.7833, 124.8333), "weight": 0.05}
        }

class ThreatScenarioConfig(BaseModel):
    """위협 시나리오 설정"""
    
    scenarios: Dict[str, Dict] = Field(
        default_factory=lambda: {
            "north_korea_conventional": {
                "name": "NK_Conventional",
                "missile_types": {"SRBM": 0.6, "MBRM": 0.3, "IRBM": 0.1},
                "threat_count": 50,
                "attack_pattern": "saturation",
                "target_preference": "government_military",
                "salvo_interval": 15.0
            },
            "north_korea_escalated": {
                "name": "NK_Escalated",
                "missile_types": {"IRBM": 0.4, "ICBM": 0.2, "SRBM": 0.4},
                "threat_count": 60,
                "attack_pattern": "precision_then_saturation",
                "target_preference": "critical_infrastructure",
                "salvo_interval": 20.0
            },
            "multi_vector_attack": {
                "name": "Multi_Vector_Attack",
                "missile_types": {"SRBM": 0.3, "MBRM": 0.3, "IRBM": 0.3, "ICBM": 0.1},
                "threat_count": 70,
                "attack_pattern": "coordinated_multi_axis",
                "target_preference": "economic_centers",
                "salvo_interval": 10.0
            },
            "precision_strike": {
                "name": "Precision_Strike",
                "missile_types": {"IRBM": 0.5, "ICBM": 0.3, "MBRM": 0.2},
                "threat_count": 50,
                "attack_pattern": "precision_sequential",
                "target_preference": "command_control",
                "salvo_interval": 30.0
            },
            "sustained_campaign": {
                "name": "Sustained_Campaign",
                "missile_types": {"SRBM": 0.5, "MBRM": 0.4, "IRBM": 0.1},
                "threat_count": 80,
                "attack_pattern": "wave_attack",
                "target_preference": "broad_spectrum",
                "salvo_interval": 5.0
            }
        }
    )

class EngagementZoneConfig(BaseModel):
    """교전 영역 계산 설정 - 궁적 기반 교전 영역 모델링"""
    
    @staticmethod
    def calculate_trajectory_intercept_point(threat: Dict, intercept_time: float, assets: List[Dict] = None) -> Dict:
        """미사일 궤적에서 교전 시점의 위치와 고도 계산"""
        import math
        
        launch_pos = threat["launch_position"]
        
        # 목표 위치 가져오기 (threat에 직접 포함되어 있으면 사용)
        target_pos = threat.get("target_position")
        
        if not target_pos:
            # 목표 자산 위치 찾기
            if assets is None:
                assets = AssetConfig.create_priority_defense_assets()
            for asset in assets:
                if asset["id"] == threat.get("target_asset_id"):
                    target_pos = asset["position"]
                    break
        
        if not target_pos:
            return None
        
        # 미사일 스펙 (안전한 속성 접근)
        missile_specs = getattr(threat, 'specs', threat.get('specs', {}))
        flight_time = getattr(threat, 'flight_time', threat.get('flight_time', 100))
        max_altitude = getattr(missile_specs, 'max_altitude_km', missile_specs.get('max_altitude_km', 50.0))
        
        # critical_altitude_km 가져오기 (phase_events에서)
        phase_events = getattr(threat, 'phase_events', threat.get('phase_events', {}))
        critical_altitude = getattr(phase_events, 'critical_altitude_km', 
                                   phase_events.get('critical_altitude_km', max_altitude * 0.7))
        
        # 탄도 궤적 계산 (포물선 근사)
        total_distance = math.sqrt(
            (target_pos[0] - launch_pos[0])**2 + 
            (target_pos[1] - launch_pos[1])**2
        )
        
        # 교전 시점에서의 위치 (비선형 보간)
        time_ratio = intercept_time / flight_time
        
        if time_ratio < 0 or time_ratio > 1:
            return None
        
        # 수평 위치 (선형 보간)
        intercept_x = launch_pos[0] + (target_pos[0] - launch_pos[0]) * time_ratio
        intercept_y = launch_pos[1] + (target_pos[1] - launch_pos[1]) * time_ratio
        
        # 고도 계산 (critical_altitude 기준 포물선)
        # critical_altitude를 최대 고도로 사용하여 교전 윈도우 확장
        if time_ratio <= 0.5:  # 상승기
            altitude = critical_altitude * (2 * time_ratio)
        else:  # 하강기
            altitude = critical_altitude * (2 * (1 - time_ratio))
        
        return {
            "position": (intercept_x, intercept_y),
            "altitude_km": altitude,
            "time": intercept_time
        }
    
    @staticmethod
    def can_engage_trajectory(battery: Dict, threat: Dict, assets: List[Dict] = None) -> Dict:
        """궤적 기반 교전 가능성 및 교전 시간 윈도우 계산"""
        import math
        
        battery_pos = battery["position"]
        specs = battery["specs"]
        
        # 시스템 별 교전 스펙
        if battery["system_type"] == "LSAM":
            engagement_specs = specs["ballistic_missile_specs"]
        else:  # MSAM
            engagement_specs = specs["ballistic_missile_specs"]
        
        min_range = engagement_specs["engagement_range_km"]["min"]
        max_range = engagement_specs["engagement_range_km"]["max"]
        min_altitude = engagement_specs["engagement_altitude_km"]["min"]
        max_altitude = engagement_specs["engagement_altitude_km"]["max"]
        
        # 교전 가능 시간 윈도우 찾기
        flight_time = threat["flight_time"]
        engagement_windows = []
        
        # 5초 간격으로 궤적 상의 지점들 검사 (더 정밀한 교전 윈도우 탐지)
        for t in range(0, int(flight_time), 3):
            intercept_point = EngagementZoneConfig.calculate_trajectory_intercept_point(threat, t, assets)
            
            if not intercept_point:
                continue
            
            # 거리 계산
            distance = math.sqrt(
                (battery_pos[0] - intercept_point["position"][0])**2 + 
                (battery_pos[1] - intercept_point["position"][1])**2
            )
            
            altitude = intercept_point["altitude_km"]
            
            # 교전 가능 조건 확인
            if (min_range <= distance <= max_range and 
                min_altitude <= altitude <= max_altitude):
                engagement_windows.append({
                    "time": t,
                    "distance": distance,
                    "altitude": altitude,
                    "position": intercept_point["position"]
                })
        
        return {
            "can_engage": len(engagement_windows) > 0,
            "engagement_windows": engagement_windows,
            "optimal_time": engagement_windows[0]["time"] if engagement_windows else None
        }
    
    @staticmethod
    def can_engage(battery: Dict, threat: Dict, assets: List[Dict] = None) -> bool:
        """포대가 위협을 교전할 수 있는지 계산 (궁적 기반)"""
        
        # 궁적 기반 교전 가능성 계산
        engagement_analysis = EngagementZoneConfig.can_engage_trajectory(battery, threat, assets)
        return engagement_analysis["can_engage"]
    
    @staticmethod
    def create_engagement_matrix() -> Dict:
        """교전 가능성 매트릭스 생성 (궁적 기반)"""
        batteries = BatteryDeploymentConfig.create_battery_deployment()
        threats = ThreatMissileConfig.create_ballistic_missile_threats()
        
        engagement_matrix = {}
        detailed_analysis = {}
        
        print("\nCalculating trajectory-based engagement zones...")
        
        for battery in batteries:
            for threat in threats:
                key = (battery["id"], threat["id"])
                
                try:
                    # 궤적 기반 상세 분석 (assets는 기본값 사용)
                    analysis = EngagementZoneConfig.can_engage_trajectory(battery, threat, None)
                    engagement_matrix[key] = analysis["can_engage"]
                    detailed_analysis[key] = analysis
                except Exception as e:
                    print(f"Warning: Failed to analyze {key}: {e}")
                    # 기본값으로 교전 불가능 설정
                    engagement_matrix[key] = False
                    detailed_analysis[key] = {"can_engage": False, "engagement_windows": [], "error": str(e)}
        
        # 교전 가능성 통계
        total_pairs = len(engagement_matrix)
        feasible_pairs = sum(engagement_matrix.values())
        
        print(f"Trajectory-based engagement analysis complete:")
        print(f"  Total battery-threat pairs: {total_pairs}")
        print(f"  Feasible engagements: {feasible_pairs} ({100*feasible_pairs/total_pairs:.1f}%)")
        
        # 시스템별 교전 가능성
        lsam_engagements = sum(1 for (battery_id, threat_id), can_engage in engagement_matrix.items() 
                              if battery_id.startswith('LSAM') and can_engage)
        msam_engagements = sum(1 for (battery_id, threat_id), can_engage in engagement_matrix.items() 
                              if battery_id.startswith('MSAM') and can_engage)
        
        print(f"  LSAM engagements: {lsam_engagements}")
        print(f"  MSAM engagements: {msam_engagements}")
        
        # LSAM 교전 디버깅: 각 LSAM-위협 조합 상세 분석
        print("\nLSAM Engagement Debug:")
        for battery in batteries:
            if battery["system_type"] == "LSAM":
                battery_id = battery["id"]
                print(f"\n{battery_id} analysis:")
                for threat in threats:
                    threat_id = threat["id"]
                    key = (battery_id, threat_id)
                    can_engage = engagement_matrix.get(key, False)
                    
                    if can_engage:
                        print(f"  [OK] {threat_id}: CAN ENGAGE")
                    else:
                        print(f"  [NO] {threat_id}: CANNOT ENGAGE")
                        # 상세 분석 (assets는 기본값 사용)
                        analysis = EngagementZoneConfig.can_engage_trajectory(battery, threat, None)
                        print(f"     - Windows: {len(analysis.get('engagement_windows', []))}")
                        print(f"     - Threat type: {threat.get('type', 'Unknown')}")
                        print(f"     - Max altitude: {threat.get('specs', {}).get('max_altitude_km', 'Unknown')}km")
        
        return engagement_matrix
    
    @staticmethod
    def calculate_engagement_time_window(battery: Dict, threat: Dict) -> Dict:
        """교전 타임 윈도우 계산 - 궁적 기반 실시간 분석"""
        import math
        
        battery_pos = battery["position"]
        battery_range = battery["coverage_radius_km"]
        system_type = battery["system_type"]
        
        # 위협 미사일 궁적 정보
        launch_pos = threat["launch_position"]
        target_asset_id = threat["target_asset_id"]
        flight_time = threat["flight_time"]
        missile_specs = threat["specs"]
        
        # 목표 자산 위치 찾기
        assets = AssetConfig.create_priority_defense_assets()
        target_pos = None
        for asset in assets:
            if asset["id"] == target_asset_id:
                target_pos = asset["position"]
                break
        
        if not target_pos:
            return {"engagement_window_sec": 0, "can_engage": False, "window_quality": 0.0}
        
        # 미사일 총 비행 거리
        total_distance = math.sqrt(
            (target_pos[0] - launch_pos[0])**2 + 
            (target_pos[1] - launch_pos[1])**2
        )
        
        # 미사일 평균 속도 (km/s)
        avg_missile_speed = total_distance / flight_time if flight_time > 0 else 1.0
        
        # 포대에서 미사일 궁적까지의 거리 계산
        engagement_opportunities = []
        
        # 미사일 궁적을 시간별로 샘플링 (0.5초 간격)
        time_step = 0.5  # 초
        for t in range(int(flight_time / time_step)):
            current_time = t * time_step
            
            # 현재 시점에서 미사일 위치 계산
            intercept_point = EngagementZoneConfig.calculate_trajectory_intercept_point(
                threat, current_time
            )
            
            if intercept_point:
                missile_pos = intercept_point["position"]
                missile_altitude = intercept_point["altitude_km"]
                
                # 포대에서 미사일까지의 거리
                distance_to_missile = math.sqrt(
                    (missile_pos[0] - battery_pos[0])**2 + 
                    (missile_pos[1] - battery_pos[1])**2
                )
                
                # 교전 가능 범위 내인지 확인
                if distance_to_missile <= battery_range:
                    engagement_opportunities.append({
                        "time": current_time,
                        "distance": distance_to_missile,
                        "altitude": missile_altitude,
                        "missile_speed": avg_missile_speed
                    })
        
        # 교전 윈도우 계산
        if not engagement_opportunities:
            return {"engagement_window_sec": 0, "can_engage": False, "window_quality": 0.0}
        
        # 연속된 교전 기회 찾기
        engagement_window_sec = len(engagement_opportunities) * time_step
        
        # 교전 품질 평가 (0.0 ~ 1.0)
        prob_config = ProbabilityConfig()
        window_config = prob_config.engagement_window_config[system_type]
        
        optimal_window = window_config["optimal_window_sec"]
        minimum_window = window_config["minimum_window_sec"]
        
        # 윈도우 품질 계산
        if engagement_window_sec >= optimal_window:
            window_quality = 1.0  # 최적 윈도우
        elif engagement_window_sec >= minimum_window:
            # 선형 보간
            window_quality = (engagement_window_sec - minimum_window) / (optimal_window - minimum_window)
        else:
            # 최소 윈도우 미달
            window_quality = 0.2 * (engagement_window_sec / minimum_window)
        
        # 최적 거리/고도 고려
        avg_distance = sum(opp["distance"] for opp in engagement_opportunities) / len(engagement_opportunities)
        avg_altitude = sum(opp["altitude"] for opp in engagement_opportunities) / len(engagement_opportunities)
        
        optimal_range = window_config["maximum_range_km"] * 0.6  # 최적 거리는 최대의 60%
        optimal_altitude = window_config["optimal_altitude_km"]
        
        # 거리 효율성
        if avg_distance <= optimal_range:
            distance_efficiency = 1.0
        else:
            distance_efficiency = max(0.3, optimal_range / avg_distance)
        
        # 고도 효율성
        altitude_diff = abs(avg_altitude - optimal_altitude)
        altitude_efficiency = max(0.4, 1.0 - (altitude_diff / optimal_altitude))
        
        # 종합 윈도우 품질
        final_quality = window_quality * distance_efficiency * altitude_efficiency

        # 🆕 교전 윈도우 시작/종료 시간 추가
        window_start_time = engagement_opportunities[0]["time"] if engagement_opportunities else 0.0
        window_end_time = engagement_opportunities[-1]["time"] if engagement_opportunities else 0.0
        window_duration = window_end_time - window_start_time

        return {
            "engagement_window_sec": engagement_window_sec,
            "can_engage": engagement_window_sec >= minimum_window,
            "window_quality": min(1.0, max(0.0, final_quality)),
            "avg_distance_km": avg_distance,
            "avg_altitude_km": avg_altitude,
            "opportunities_count": len(engagement_opportunities),
            # 🆕 Time-based K-factor를 위한 시간 정보
            "window_start_time": window_start_time,
            "window_end_time": window_end_time,
            "window_duration": window_duration
        }
    
    @staticmethod
    def calculate_window_adjusted_probability(battery: Dict, threat: Dict, base_probability: float) -> float:
        """교전 윈도우 기반 조정된 요격 확률 계산"""
        window_analysis = EngagementZoneConfig.calculate_engagement_time_window(battery, threat)
        
        if not window_analysis["can_engage"]:
            return 0.0
        
        window_quality = window_analysis["window_quality"]
        system_type = battery["system_type"]
        
        # 기본 확률에 윈도우 품질 적용
        prob_config = ProbabilityConfig()
        window_config = prob_config.engagement_window_config[system_type]
        efficiency_factor = window_config["window_efficiency_factor"]
        
        # 윈도우 품질에 따른 확률 조정 (더 관대한 조정)
        # 기본 확률의 90% 이상을 보장하고, 윈도우 품질에 따라 10% 범위에서만 조정
        quality_bonus = (1 - efficiency_factor) * window_quality * 0.5  # 품질 보너스 완화
        adjusted_probability = base_probability * (efficiency_factor + quality_bonus)
        
        # 기본 확률의 85% 이상은 항상 보장
        guaranteed_minimum = base_probability * 0.85
        
        # 범위 제한
        min_prob = max(prob_config.min_probability, guaranteed_minimum)
        max_prob = prob_config.max_probability
        
        return max(min_prob, min(max_prob, adjusted_probability))

class ScenarioManager:
    """다양한 위협 시나리오 버전 관리 클래스"""
    
    @staticmethod
    def get_scenario_list() -> Dict[str, str]:
        """사용 가능한 시나리오 목록 반환 (확장성 테스트 최적화)"""
        return {
            # Small 시나리오 (알고리즘 기본 성능 검증)
            "SMALL_3": "초소규모 (3발 - 알고리즘 검증)",
            "SMALL_5": "소규모 (5발 - 기본 성능)",
            "SMALL_8": "소중규모 (8발 - 전환점 테스트)",
            
            # Medium 시나리오 (실전 시나리오)
            "MEDIUM_10": "중소규모 (10발 - 일반 공격)",
            "BASELINE_15": "중규모 기본 (15발 - 표준 시나리오)",
            "MEDIUM_20": "중대규모 (20발 - 균형 공격)",
            
            # Large 시나리오 (확장성 한계 테스트)
            "LARGE_30": "대규모 (30발 - 포화 공격)",
            "LARGE_40": "초대규모 (40발 - 한계 테스트)",
            
            # Stress 시나리오 (MIP 솔버 성능 한계 검증)
            "STRESS_100": "스트레스 100발 + 15포대 (기준, BAT15)",
            "STRESS_100_BAT30": "스트레스 100발 + 30포대 (LSAM 15 + MSAM 15)",
            "STRESS_100_BAT50": "스트레스 100발 + 50포대 (LSAM 25 + MSAM 25)",
            
            # 패턴 테스트 (발사 패턴 분석)
            "SEQUENTIAL_15": "순차 공격 (15발 - 순차 발사)",
            "SIMULTANEOUS_15": "동시 공격 (15발 - 동시 발사)"
        }
    
    @staticmethod
    def create_small_attack_3(base_threats: List[Dict]) -> List[Dict]:
        """초소규모 공격 시나리오 (3발 - 알고리즘 검증)"""
        selected = [base_threats[i].copy() for i in [0, 1, 2]]  # T01-T03
        
        # 발사 시간: 40초 간격 순차 발사
        for i, threat in enumerate(selected):
            threat['launch_time'] = i * 40
            threat['id'] = f"T{i+1:02d}"
        
        return selected
    
    @staticmethod
    def create_small_attack_5(base_threats: List[Dict]) -> List[Dict]:
        """소규모 공격 시나리오 (5발 - 기본 성능)"""
        selected = [base_threats[i].copy() for i in [0, 1, 2, 3, 4]]  # T01-T05
        
        # 발사 시간: 30초 간격 순차 발사
        for i, threat in enumerate(selected):
            threat['launch_time'] = i * 30
            threat['id'] = f"T{i+1:02d}"
        
        return selected
    
    @staticmethod
    def create_small_attack_8(base_threats: List[Dict]) -> List[Dict]:
        """소중규모 공격 시나리오 (8발 - 전환점 테스트)"""
        selected = [base_threats[i].copy() for i in range(8)]  # T01-T08
        
        # 발사 시간: 25초 간격 순차 발사
        for i, threat in enumerate(selected):
            threat['launch_time'] = i * 25
            threat['id'] = f"T{i+1:02d}"
        
        return selected
    
    @staticmethod
    def create_medium_attack_10(base_threats: List[Dict]) -> List[Dict]:
        """중소규모 공격 시나리오 (10발 - 일반 공격)"""
        selected = [base_threats[i].copy() for i in range(10)]  # T01-T10
        
        # 발사 시간: 20초 간격 순차 발사
        for i, threat in enumerate(selected):
            threat['launch_time'] = i * 20
            threat['id'] = f"T{i+1:02d}"
        
        return selected
    
    @staticmethod
    def create_medium_attack_20(base_threats: List[Dict]) -> List[Dict]:
        """중대규모 공격 시나리오 (20발 - 균형 공격)"""
        threats = []
        
        # 기본 15발 + 5발 추가
        for i in range(20):
            threat = base_threats[i % 15].copy()
            threat['id'] = f"T{i+1:02d}"
            threat['name'] = f"{threat['type']}_{i+1}"
            # 발사 시간: 15초 간격
            threat['launch_time'] = i * 15
            threats.append(threat)
        
        return threats
    
    @staticmethod
    def create_heavy_attack_30(base_threats: List[Dict]) -> List[Dict]:
        """대규모 포화 공격 시나리오 (30발 - 집중 발사)"""
        threats = []
        
        # 기본 15발을 2배로 복제하여 30발 생성
        for i in range(2):
            for j, threat in enumerate(base_threats):
                new_threat = threat.copy()
                new_threat['id'] = f"T{i*15 + j + 1:02d}"
                new_threat['name'] = f"{threat['type']}_{i*15 + j + 1}"
                # 발사 시간: 10초 간격으로 집중 발사
                new_threat['launch_time'] = (i * 15 + j) * 10
                threats.append(new_threat)
        
        return threats
    
    @staticmethod
    def create_large_attack_40(base_threats: List[Dict]) -> List[Dict]:
        """초대규모 공격 시나리오 (40발 - 한계 테스트)"""
        threats = []
        
        # 기본 15발을 반복하여 40발 생성
        for i in range(40):
            threat = base_threats[i % 15].copy()
            threat['id'] = f"T{i+1:02d}"
            threat['name'] = f"{threat['type']}_{i+1}"
            # 발사 시간: 8초 간격으로 집중 발사
            threat['launch_time'] = i * 8
            threats.append(threat)
        
        return threats
    
    @staticmethod
    def create_sequential_attack_15(base_threats: List[Dict]) -> List[Dict]:
        """순차 공격 시나리오 (15발 - 순차 발사)"""
        threats = []
        
        # 기본 15발 사용
        # 발사 시간: 25초 간격으로 순차 발사
        for i, threat in enumerate(base_threats):
            new_threat = threat.copy()
            new_threat['id'] = f"T{i+1:02d}"
            new_threat['name'] = f"{threat['type']}_{i+1}"
            new_threat['launch_time'] = i * 25
            threats.append(new_threat)
        
        return threats
    
    @staticmethod
    def create_simultaneous_attack_15(base_threats: List[Dict]) -> List[Dict]:
        """동시 공격 시나리오 (15발 - 동시 발사)"""
        threats = []
        
        # 기본 15발을 3개 웨이브로 나누어 동시 발사
        wave_times = [0, 60, 120]  # 0초, 60초, 120초에 발사
        
        for i, threat in enumerate(base_threats):
            new_threat = threat.copy()
            new_threat['id'] = f"T{i+1:02d}"
            new_threat['name'] = f"{threat['type']}_{i+1}"
            # 각 웨이브마다 동시 발사 (±2초 편차)
            wave_idx = i // 5
            new_threat['launch_time'] = wave_times[wave_idx] + (i % 5) * 2
            threats.append(new_threat)
        
        return threats
    
    @staticmethod
    def create_stress_test_100(base_threats: List[Dict]) -> List[Dict]:
        """스트레스 테스트 시나리오 (100발 - 성능 한계 검증)
        
        개선: 발사 간격을 2초로 단축하여 위협이 시간에 따라 분산되도록 함
        - 기존 10초 간격: 모든 위협이 발사된 후 요격 시작 (비효율)
        - 개선 2초 간격: 요격과 발사가 동시 진행되어 45개 할당 슬롯 효율적 활용
        """
        return ScenarioManager._create_stress_test(base_threats, 100, interval=2)
    
    @staticmethod
    def create_stress_test_150(base_threats: List[Dict]) -> List[Dict]:
        """스트레스 테스트 시나리오 (150발 - 점진적 확장)"""
        return ScenarioManager._create_stress_test(base_threats, 150, interval=6)
    
    @staticmethod
    def create_stress_test_200(base_threats: List[Dict]) -> List[Dict]:
        """스트레스 테스트 시나리오 (200발 - 한계 탐색)"""
        return ScenarioManager._create_stress_test(base_threats, 200, interval=5)
    
    @staticmethod
    def create_stress_test_300(base_threats: List[Dict]) -> List[Dict]:
        """스트레스 테스트 시나리오 (300발 - 극한 테스트)"""
        return ScenarioManager._create_stress_test(base_threats, 300, interval=3)
    
    @staticmethod
    def _create_stress_test(base_threats: List[Dict], count: int, interval: int) -> List[Dict]:
        """스트레스 테스트 공통 생성 함수
        
        Args:
            base_threats: 기본 위협 템플릿 (15발)
            count: 생성할 위협 수
            interval: 발사 간격 (초)
        
        개선사항: 발사 거리를 순차적으로 증가시켜 시간에 따라 자연스럽게 다가오도록 설정
        - 초기 위협: 가까운 거리 (100-120km)
        - 중기 위협: 중간 거리 (120-160km)
        - 후기 위협: 먼 거리 (160-200km)
        """
        threats = []
        
        for i in range(count):
            threat = base_threats[i % 15].copy()
            threat['id'] = f"T{i+1:03d}"
            threat['name'] = f"{threat['type']}_{i+1}"
            threat['launch_time'] = i * interval
            
            # 발사 거리 순차 증가
            base_distance = 100
            distance_increment = i * 1.0
            target_distance = base_distance + distance_increment
            
            # launch_position 조정
            original_launch_y = threat['launch_position'][1]
            new_launch_y = original_launch_y + distance_increment
            threat['launch_position'] = (threat['launch_position'][0], new_launch_y)
            
            # flight_time 조정
            original_flight_time = threat.get('flight_time', 300)
            distance_ratio = target_distance / base_distance
            threat['flight_time'] = int(original_flight_time * distance_ratio)
            
            threats.append(threat)
        
        return threats

class MIPConfig(BaseModel):
    """MIP 최적화 통합 설정 - 현실적 규모 버전"""
    
    base_config: BaseConfig = Field(default_factory=BaseConfig)
    solver_config: MIPSolverConfig = Field(default_factory=MIPSolverConfig)
    sls_config: SLSConfig = Field(default_factory=SLSConfig)
    probability_config: ProbabilityConfig = Field(default_factory=ProbabilityConfig)
    
    # 현실적 규모 설정
    num_assets: int = Field(10, description="방어 자산 수")
    num_batteries: int = Field(10, description="총 포대 수 (LSAM 5개 + MSAM 5개)")
    num_threats: int = Field(15, description="위협 미사일 수")
    
    weapon_types: List[str] = Field(["LSAM", "MSAM"], description="사용 가능한 무기체계")
    time_step_sec: float = Field(1.0, description="시간 단계 (초)")
    simulation_duration_sec: float = Field(800.0, description="시뮬레이션 지속 시간 (13.3분)")
    
    # 시나리오 선택 (기본값: DWTA_BALANCED)
    scenario_type: str = Field("DWTA_BALANCED", description="시나리오 타입")
    
    def get_defense_assets(self):
        """방어 자산 목록 반환 - scenario_dwta_balanced.py의 ScenarioManager 사용"""
        # 🔧 통합: scenario_dwta_balanced.py의 ScenarioManager 사용
        try:
            from scenario_dwta_balanced import ScenarioManager
            scenario_data = ScenarioManager.create_scenario(self.scenario_type)
            return scenario_data["assets"]
        except (ImportError, ValueError) as e:
            print(f"Warning: Failed to load assets for '{self.scenario_type}': {e}")
            print("Falling back to default assets")
            return AssetConfig.create_priority_defense_assets()
    
    def get_battery_deployment(self):
        """포대 배치 목록 반환 - scenario_dwta_balanced.py의 ScenarioManager 사용"""
        # 🔧 통합: scenario_dwta_balanced.py의 ScenarioManager 사용
        try:
            from scenario_dwta_balanced import ScenarioManager
            scenario_data = ScenarioManager.create_scenario(self.scenario_type)
            return scenario_data["batteries"]
        except (ImportError, ValueError) as e:
            print(f"Warning: Failed to load batteries for '{self.scenario_type}': {e}")
            print("Falling back to default battery deployment")
            return BatteryDeploymentConfig.create_battery_deployment()
    
    def get_threat_missiles(self, scenario_type: Optional[str] = None):
        """위협 미사일 목록 반환 - scenario_dwta_balanced.py의 ScenarioManager 사용"""
        if scenario_type is None:
            scenario_type = self.scenario_type
        
        # 🔧 통합: scenario_dwta_balanced.py의 ScenarioManager 사용
        try:
            from scenario_dwta_balanced import ScenarioManager
            scenario_data = ScenarioManager.create_scenario(scenario_type)
            return scenario_data["threats"]
        except (ImportError, ValueError) as e:
            print(f"Warning: Failed to load scenario '{scenario_type}': {e}")
            print("Falling back to BASELINE_15")
            # Fallback: 기본 15발 시나리오
            return ThreatMissileConfig.create_ballistic_missile_threats()
    
    def get_engagement_matrix(self):
        """교전 가능성 매트릭스 반환"""
        return EngagementZoneConfig.create_engagement_matrix()
    
    def get_interceptor_specs(self, system_type: str):
        """요격 시스템 스펙 반환"""
        if system_type == "LSAM":
            return InterceptorSystemConfig.get_lsam_specs()
        elif system_type == "MSAM":
            return InterceptorSystemConfig.get_msam_specs()
        else:
            raise ValueError(f"Unknown system type: {system_type}")
    
    def get_launch_bases(self) -> Dict[str, Dict]:
        """발사 기지 목록 반환"""
        return LaunchBaseConfig.create_north_korean_bases()
    
    def get_threat_scenarios(self):
        """위협 시나리오 목록 반환"""
        return ThreatScenarioConfig().scenarios
    
    def create_realistic_scenario(self, scenario_type: Optional[str] = None) -> Dict:
        """현실적인 시나리오 생성 - 시나리오 타입에 따라 다른 위협 구성"""
        if scenario_type is None:
            scenario_type = self.scenario_type
        
        # 시나리오 정보 가져오기
        scenario_list = ScenarioManager.get_scenario_list()
        scenario_desc = scenario_list.get(scenario_type, "Unknown scenario")
        
        # 위협 미사일 생성
        threats = self.get_threat_missiles(scenario_type)
        num_threats = len(threats)
        
        return {
            "name": f"Korean_Defense_Scenario_{scenario_type}",
            "description": f"{scenario_desc} - 10 assets, 10 batteries (5 LSAM + 5 MSAM), {num_threats} missiles",
            "scenario_type": scenario_type,
            "assets": self.get_defense_assets(),
            "batteries": self.get_battery_deployment(),
            "threats": threats,
            "engagement_matrix": self.get_engagement_matrix(),
            "total_variables_estimate": self.num_assets * num_threats * self.num_batteries * 2,
            "total_constraints_estimate": self.num_assets * num_threats * 5
        }

# 기본 MIP 설정 인스턴스 생성 (현실적 규모)
mip_config = MIPConfig()

if __name__ == "__main__":
    print("=== MIP Configuration Test (Realistic Scale) ===")
    config = MIPConfig()
    
    print(f"Solver: {config.solver_config.solver_name}")
    print(f"Time limit: {config.solver_config.time_limit_sec}s")
    print(f"Scale: {config.num_assets} assets, {config.num_batteries} batteries, {config.num_threats} threats")
    print(f"Weapon types: {config.weapon_types}")
    
    # 현실적 시나리오 테스트
    scenario = config.create_realistic_scenario()
    print(f"\n=== Realistic Scenario: {scenario['name']} ===")
    print(f"Description: {scenario['description']}")
    print(f"Estimated variables: {scenario['total_variables_estimate']}")
    print(f"Estimated constraints: {scenario['total_constraints_estimate']}")
    
    # 자산 정보
    assets = config.get_defense_assets()
    print(f"\nDefense Assets ({len(assets)}):") 
    for asset in assets:
        print(f"  {asset['id']}: {asset['name']} (Priority {asset['priority']}, Value: {asset['value']})")
    
    # 포대 정보
    batteries = config.get_battery_deployment()
    print(f"\nBattery Deployment ({len(batteries)}):")
    for battery in batteries:
        print(f"  {battery['id']}: {battery['name']} ({battery['system_type']}) - Range: {battery['coverage_radius_km']}km")
    
    # 위협 정보
    threats = config.get_threat_missiles()
    print(f"\nThreat Missiles ({len(threats)}):")
    for threat in threats[:5]:  # 처음 5개만 출력
        print(f"  {threat['id']}: {threat['name']} -> {threat['target_asset_id']} (T+{threat['launch_time']}s)")
    print(f"  ... and {len(threats)-5} more threats")
    
    # 교전 가능성 통계
    engagement_matrix = config.get_engagement_matrix()
    total_engagements = sum(engagement_matrix.values())
    total_possible = len(engagement_matrix)
    print(f"\nEngagement Capability: {total_engagements}/{total_possible} ({100*total_engagements/total_possible:.1f}%) battery-threat pairs can engage")
    
    # 시스템 스펙 샘플
    lsam_specs = config.get_interceptor_specs("LSAM")
    msam_specs = config.get_interceptor_specs("MSAM")
    print(f"\nLSAM Range: {lsam_specs['ballistic_missile_specs']['engagement_range_km']['min']}-{lsam_specs['ballistic_missile_specs']['engagement_range_km']['max']}km")
    print(f"MSAM Range: {msam_specs['ballistic_missile_specs']['engagement_range_km']['min']}-{msam_specs['ballistic_missile_specs']['engagement_range_km']['max']}km")
    for asset in mip_config.get_defense_assets()[:5]:  # Show first 5 assets
        print(f"{asset['id']}: {asset['name']} - Weight: {asset['weighted_value']}")
    
    print("\n=== Launch Bases List ===")
    for base_name, base_info in mip_config.get_launch_bases().items():
        print(f"{base_name}: {base_info['coords']} (Weight: {base_info['weight']})")


# ============================================================================
# 최적화 사전 계산 캐시 클래스들
# ============================================================================

class EnhancedEngagementMatrix:
    """교전 가능성 및 관련 파라미터 사전 계산 (최적화 #1)"""

    def __init__(self):
        self.feasible: Dict[Tuple[str, str], bool] = {}
        self.distances: Dict[Tuple[str, str], float] = {}
        self.base_probabilities: Dict[Tuple[str, str], float] = {}
        self.computed_threats: Set[str] = set()  # 계산된 위협 추적
        # 🆕 Time-based K-factor를 위한 윈도우 정보 저장
        self.window_info: Dict[Tuple[str, str], Dict] = {}  # (battery_id, threat_id) → window_info
        
    def precompute_all(self, batteries: List[Dict], threats: List[Dict], assets: List[Dict]):
        """
        모든 (battery, threat) 조합의 파라미터를 미리 계산
        
        Args:
            batteries: 포대 리스트
            threats: 위협 리스트 (initial_threats_config)
            assets: 자산 리스트
        """
        print("=" * 60)
        print("사전 계산 시작: Engagement Matrix")
        print("=" * 60)
        
        total_combinations = len(batteries) * len(threats)
        feasible_count = 0
        
        for battery in batteries:
            bat_pos = np.array(battery['position'][:2])  # x, y만 사용
            
            # 스펙 추출
            if 'specs' in battery and battery['specs']:
                specs = battery['specs']
                if battery['system_type'] == 'LSAM':
                    spec_key = 'ballistic_missile_specs'
                else:
                    spec_key = 'ballistic_missile_specs'
                
                if spec_key in specs:
                    range_info = specs[spec_key]['engagement_range_km']
                    min_range = range_info.get('min', 0)
                    max_range = range_info['max']
                    # 단발 요격 확률 사용 (새 키 이름 지원)
                    intercept_prob = specs[spec_key].get('intercept_probability_single', 
                                                          specs[spec_key].get('intercept_probability', 0.85))
                    
                    altitude_info = specs[spec_key]['engagement_altitude_km']
                    min_alt = altitude_info.get('min', 0)
                    max_alt = altitude_info['max']
                else:
                    # Fallback
                    min_range = 0
                    max_range = 150 if battery['system_type'] == 'LSAM' else 80
                    intercept_prob = 0.85 if battery['system_type'] == 'LSAM' else 0.78
                    min_alt = 0
                    max_alt = 100
            else:
                # Fallback
                min_range = 0
                max_range = 150 if battery['system_type'] == 'LSAM' else 80
                intercept_prob = 0.85 if battery['system_type'] == 'LSAM' else 0.78
                min_alt = 0
                max_alt = 100
            
            for threat in threats:
                threat_id = threat['id']
                key = (battery['id'], threat_id)
                
                # 1. Distance 계산 (궤적 기반 - 발사 위치와 목표 위치 고려)
                threat_launch_pos = np.array(threat['launch_position'][:2])
                dist_from_launch = np.linalg.norm(bat_pos - threat_launch_pos)
                self.distances[key] = dist_from_launch  # 참고용
                
                # 2. Feasibility 판정: 잠재적 교전 가능 여부
                # 위협이 배터리 사거리 내로 진입할 가능성이 있는지 판단
                
                # 고도 체크 (critical_altitude 사용 - 실제 교전 고도)
                phase_events = threat.get('phase_events', {})
                critical_alt = phase_events.get('critical_altitude_km')
                if critical_alt is None:
                    # fallback: max_altitude의 70%
                    threat_max_alt = threat.get('specs', {}).get('max_altitude_km', 50.0)
                    critical_alt = threat_max_alt * 0.7
                altitude_ok = (min_alt <= critical_alt <= max_alt)
                
                # 거리 체크: 궤적 기반 (발사→목표 경로가 배터리 사거리를 통과하는지)
                threat_target_pos = threat.get('target_position')
                if threat_target_pos is not None:
                    threat_target_pos = np.array(threat_target_pos[:2])
                    dist_to_target = np.linalg.norm(bat_pos - threat_target_pos)
                    # 발사 위치 또는 목표 위치 중 하나라도 사거리 내면 교전 가능
                    min_dist = min(dist_from_launch, dist_to_target)
                    # 🔥 최적화: 교전 가능 범위 (사거리의 2.0배)
                    # - 2.0배: LARGE 시나리오 대응 (요격률 우선)
                    # - 1.5배: 너무 보수적 (LARGE에서 요격 실패)
                    # - Runtime 필터링 + FBBT로 추가 보정
                    potential_range = max_range * 2.0
                    in_potential_range = (min_dist <= potential_range)
                else:
                    # target_position이 없으면 발사 위치만 사용 (fallback)
                    potential_range = max_range * 2.0
                    in_potential_range = (dist_from_launch <= potential_range)
                
                self.feasible[key] = in_potential_range and altitude_ok
                
                # 3. Base intercept probability
                if self.feasible[key]:
                    self.base_probabilities[key] = intercept_prob
                    feasible_count += 1
                else:
                    self.base_probabilities[key] = 0.0
                
                # 계산된 위협 추적
                self.computed_threats.add(threat_id)
        
        print(f"[OK] 총 조합: {total_combinations}")
        print(f"[OK] 교전 가능: {feasible_count} ({feasible_count/total_combinations*100:.1f}%)")
        print(f"[OK] 교전 불가: {total_combinations - feasible_count}")
        
        # DEBUG: SCUD_B (T11-T20)에 대한 MSAM 교전 가능성 확인
        scud_msam_count = 0
        for battery in batteries:
            if battery['system_type'] == 'MSAM':
                for threat in threats:
                    if threat['id'] in ['T11', 'T12', 'T13']:
                        key = (battery['id'], threat['id'])
                        if self.feasible.get(key, False):
                            scud_msam_count += 1
                            print(f"[DEBUG precompute] {battery['id']} CAN engage {threat['id']}")
                        else:
                            print(f"[DEBUG precompute] {battery['id']} CANNOT engage {threat['id']}")
        
        print("=" * 60)
    
    def is_feasible(self, battery_id: str, threat_id: str, threat_current_position: tuple = None, 
                    battery_position: tuple = None, battery_specs: dict = None) -> bool:
        """
        교전 가능 여부 (정적 precompute + 실시간 거리/고도 체크)
        
        Args:
            battery_id: 배터리 ID
            threat_id: 위협 ID
            threat_current_position: 위협의 현재 위치 (x, y) or (x, y, altitude_km) - 실시간 체크용
            battery_position: 배터리 위치 (x, y) - 실시간 체크용
            battery_specs: 배터리 스펙 - 실시간 체크용
        
        Returns:
            교전 가능 여부
        """
        # 1단계: 정적 precompute 결과 확인 (O(1) dict lookup)
        static_feasible = self.feasible.get((battery_id, threat_id), False)
        
        # 2단계: 실시간 거리/고도 체크 (미사일이 비행 중 사거리 내로 진입했는지 확인)
        if not static_feasible and threat_current_position and battery_position and battery_specs:
            # ⚡ 최적화: numpy 배열 생성 없이 직접 계산 (2-3배 빠름)
            dx = battery_position[0] - threat_current_position[0]
            dy = battery_position[1] - threat_current_position[1]
            current_distance_sq = dx * dx + dy * dy  # 제곱 거리로 비교 (sqrt 생략)
            
            # ⚡ 최적화: 딕셔너리 키 체크 최소화
            ballistic_specs = battery_specs.get('ballistic_missile_specs')
            if ballistic_specs:
                range_info = ballistic_specs['engagement_range_km']
                max_range = range_info['max']
                min_range = range_info.get('min', 0)
                max_range_sq = max_range * max_range
                min_range_sq = min_range * min_range
                
                # 거리 체크 (제곱 거리 비교로 sqrt 연산 생략)
                if min_range_sq <= current_distance_sq <= max_range_sq:
                    # 🆕 고도 체크 (3D 위치 정보가 있을 때만)
                    if len(threat_current_position) >= 3:
                        current_altitude = threat_current_position[2]  # km
                        altitude_info = ballistic_specs['engagement_altitude_km']
                        min_altitude = altitude_info.get('min', 0)
                        max_altitude = altitude_info['max']
                        
                        # 거리 + 고도 모두 충족 시에만 True
                        if min_altitude <= current_altitude <= max_altitude:
                            return True
                    else:
                        # 고도 정보 없으면 거리만으로 판단 (기존 동작 유지)
                        return True
        
        return static_feasible
    
    def get_distance(self, battery_id: str, threat_id: str) -> float:
        """거리 (O(1) lookup)"""
        return self.distances.get((battery_id, threat_id), float('inf'))
    
    def get_base_pk(self, battery_id: str, threat_id: str) -> float:
        """기본 요격 확률 (O(1) lookup)"""
        return self.base_probabilities.get((battery_id, threat_id), 0.0)

    def get_engagement_window_info(self, battery_id: str, threat_id: str) -> Dict:
        """
        교전 윈도우 정보 반환 (Time-based K-factor 계산용)

        Returns:
            Dict: {
                'can_engage': bool,
                'window_start_time': float,  # 초
                'window_end_time': float,    # 초
                'window_duration': float,    # 초
                'window_quality': float      # 0.0~1.0
            }
        """
        key = (battery_id, threat_id)

        # 윈도우 정보가 저장되어 있으면 반환
        if key in self.window_info:
            return self.window_info[key]

        # 없으면 기본값 (교전 불가)
        return {
            'can_engage': False,
            'window_start_time': 0.0,
            'window_end_time': 0.0,
            'window_duration': 0.0,
            'window_quality': 0.0
        }
    
    def add_new_threats(self, batteries: List[Dict], new_threats: List[Dict]) -> int:
        """
        새로운 위협에 대해서만 증분 계산
        
        Args:
            batteries: 포대 리스트
            new_threats: 새로 발견된 위협 리스트
        
        Returns:
            계산된 위협 수
        """
        computed_count = 0
        
        for threat in new_threats:
            threat_id = threat['id']
            
            # 이미 계산된 위협은 스킵
            if threat_id in self.computed_threats:
                continue
            
            # 모든 배터리에 대해 계산
            for battery in batteries:
                bat_pos = np.array(battery['position'][:2])
                
                # 스펙 추출
                if 'specs' in battery and battery['specs']:
                    specs = battery['specs']
                    spec_key = 'ballistic_missile_specs'
                    
                    if spec_key in specs:
                        range_info = specs[spec_key]['engagement_range_km']
                        min_range = range_info.get('min', 0)
                        max_range = range_info['max']
                        intercept_prob = specs[spec_key]['intercept_probability']
                        
                        altitude_info = specs[spec_key]['engagement_altitude_km']
                        min_alt = altitude_info.get('min', 0)
                        max_alt = altitude_info['max']
                    else:
                        min_range = 0
                        max_range = 150 if battery['system_type'] == 'LSAM' else 80
                        intercept_prob = 0.85 if battery['system_type'] == 'LSAM' else 0.78
                        min_alt = 0
                        max_alt = 100
                else:
                    min_range = 0
                    max_range = 150 if battery['system_type'] == 'LSAM' else 80
                    intercept_prob = 0.85 if battery['system_type'] == 'LSAM' else 0.78
                    min_alt = 0
                    max_alt = 100
                
                key = (battery['id'], threat_id)
                
                # Distance 계산 (발사 위치 기준 - 참고용)
                threat_launch_pos = np.array(threat['launch_position'][:2])
                dist_2d = np.linalg.norm(bat_pos - threat_launch_pos)
                self.distances[key] = dist_2d
                
                # Feasibility 판정: 잠재적 교전 가능 여부 (궤적 기반)
                # 위협이 배터리 사거리 내로 진입할 가능성이 있는지 판단
                # 발사 위치가 사거리 밖이어도, 목표로 날아가면서 사거리 안으로 들어올 수 있음
                
                # 고도 체크 (critical_altitude 사용 - 실제 교전 고도)
                phase_events = threat.get('phase_events', {})
                critical_alt = phase_events.get('critical_altitude_km')
                if critical_alt is None:
                    # fallback: max_altitude의 70%
                    threat_max_alt = threat.get('specs', {}).get('max_altitude_km', 50.0)
                    critical_alt = threat_max_alt * 0.7
                
                # DEBUG: SCUD_B 교전 가능성 확인
                if threat_id in ['T11', 'T12'] and battery['system_type'] == 'MSAM':
                    print(f"[DEBUG add_new_threats] {battery['id']} vs {threat_id}: "
                          f"critical_alt={critical_alt}km, range=[{min_alt}-{max_alt}km], "
                          f"phase_events={phase_events}")
                
                altitude_ok = (min_alt <= critical_alt <= max_alt)
                
                # 거리 체크: 발사 위치가 최대 사거리의 2배 이내면 잠재적 교전 가능
                # (위협이 날아가면서 배터리에 가까워질 수 있음)
                potential_range = max_range * 2.0  # 잠재적 교전 범위 확대
                in_potential_range = (dist_2d <= potential_range)
                
                self.feasible[key] = in_potential_range and altitude_ok
                
                # Base intercept probability
                if self.feasible[key]:
                    self.base_probabilities[key] = intercept_prob
                else:
                    self.base_probabilities[key] = 0.0

                # 🆕 교전 윈도우 정보 계산 및 저장 (Time-based K-factor용)
                if self.feasible[key]:
                    try:
                        window_analysis = EngagementZoneConfig.calculate_engagement_time_window(
                            battery, threat
                        )
                        # 윈도우 정보 저장
                        self.window_info[key] = {
                            'can_engage': window_analysis.get('can_engage', False),
                            'window_start_time': window_analysis.get('window_start_time', 0.0),
                            'window_end_time': window_analysis.get('window_end_time', 0.0),
                            'window_duration': window_analysis.get('window_duration', 0.0),
                            'window_quality': window_analysis.get('window_quality', 0.0)
                        }
                    except Exception as e:
                        # 윈도우 계산 실패 시 기본값
                        self.window_info[key] = {
                            'can_engage': False,
                            'window_start_time': 0.0,
                            'window_end_time': 0.0,
                            'window_duration': 0.0,
                            'window_quality': 0.0
                        }

            self.computed_threats.add(threat_id)
            computed_count += 1

        return computed_count


class KFactorCache:
    """K-factor 사전 계산 캐시 + 경량 실시간 계산 (최적화 #3)"""
    
    def __init__(self, k_min: float = 0.6, k_max: float = 1.0):
        self.k_min = k_min
        self.k_max = k_max
        self.k_table: Dict[Tuple[str, str], float] = {}
        
        # 🆕 LUT (Lookup Table) - 1000단계, 8KB 메모리
        # 거리 비율 → K값 매핑 (사전 계산)
        self.LUT_SIZE = 1000
        self.k_lut = np.linspace(k_min, k_max, self.LUT_SIZE + 1)
        
        # 🔥 NEW: k_distance LUT (거리 비율 → k_distance)
        # 0~50%: 0.8 → 1.0, 50~70%: 1.0, 70~100%: 1.0 → 0.6
        self.k_distance_lut = np.zeros(self.LUT_SIZE + 1)
        for i in range(self.LUT_SIZE + 1):
            ratio = i / self.LUT_SIZE
            if ratio <= 0.5:
                self.k_distance_lut[i] = 0.8 + 0.2 * (ratio / 0.5)
            elif ratio <= 0.7:
                self.k_distance_lut[i] = 1.0
            else:
                self.k_distance_lut[i] = 1.0 - 0.4 * ((ratio - 0.7) / 0.3)
        
        # 🔥 NEW: k_window LUT (윈도우 길이 → k_window)
        # 60초 이상: 1.0, 30~60초: 0.9~1.0, 10~30초: 0.8~0.9
        self.k_window_lut = np.zeros(121)  # 0~120초 (1초 단위)
        for duration in range(121):
            if duration >= 60:
                self.k_window_lut[duration] = 1.0
            elif duration >= 30:
                self.k_window_lut[duration] = 0.9 + 0.1 * ((duration - 30) / 30)
            else:
                self.k_window_lut[duration] = 0.8 + 0.1 * (duration / 30)
        
        # 시스템 사거리 캐시 (실시간 계산용)
        self.system_ranges: Dict[str, float] = {}
        
        # 🔥 NEW: 윈도우 정보 캐시 (dict.get() 호출 제거)
        self.window_cache: Dict[Tuple[str, str], Tuple[float, float, float]] = {}
        # (system_id, threat_id) → (window_start, window_end, window_duration)
        
        # 🔥 NEW: 거리 캐시 (dict.get() 호출 제거)
        self.distance_cache: Dict[Tuple[str, str], float] = {}
        # (system_id, threat_id) → distance
    
    def precompute(self, threats: List, systems: List, engagement_matrix: EnhancedEngagementMatrix,
                   current_time: float = 0.0):
        """
        모든 (threat, system) 조합의 k-factor 계산

        Args:
            threats: Threat 객체 리스트
            systems: InterceptorSystem 객체 리스트
            engagement_matrix: 교전 가능성 매트릭스
            current_time: 현재 시간 (초, Time-based K-factor용)
        """
        print(f"사전 계산 시작: K-Factor (Time-based, t={current_time:.1f}s)")

        # 시스템 사거리 캐시 (실시간 계산용)
        for system in systems:
            self.system_ranges[system.id] = system.engagement_range

        for threat in threats:
            for system in systems:
                key = (threat.id, system.id)

                # Feasible한 경우만 계산
                if not engagement_matrix.is_feasible(system.id, threat.id):
                    self.k_table[key] = self.k_min
                    continue

                # 🔥 NEW: 윈도우 정보 캐싱 (dict.get() 호출 제거)
                window_info = engagement_matrix.get_engagement_window_info(system.id, threat.id)
                if window_info and window_info.get('can_engage', False):
                    window_start = window_info.get('window_start_time', 0.0)
                    window_end = window_info.get('window_end_time', 0.0)
                    window_duration = window_info.get('window_duration', 0.0)
                    self.window_cache[key] = (window_start, window_end, window_duration)
                
                # 🔥 NEW: 거리 캐싱 (dict.get() 호출 제거)
                distance = engagement_matrix.get_distance(system.id, threat.id)
                self.distance_cache[key] = distance

                # 🆕 Time-based K-factor 계산
                k_value = self._calculate_k_factor(threat, system, engagement_matrix, current_time)
                self.k_table[key] = k_value

        print(f"[OK] K-factor 계산 완료: {len(self.k_table)} 조합 (Time-based)")
    
    def get_k(self, threat_id: str, system_id: str) -> float:
        """K-factor 조회 (캐시에서, O(1))"""
        return self.k_table.get((threat_id, system_id), self.k_min)
    
    def get_k_realtime(self, threat_pos: tuple, system_id: str) -> float:
        """
        실시간 K값 계산 (LUT 기반, 초경량)
        
        Args:
            threat_pos: 위협 현재 위치 (x, y)
            system_id: 시스템 ID
        
        Returns:
            K값 (0.6 ~ 1.0)
        
        성능: 거리 계산 + LUT 인덱싱만 (나눗셈/곱셈 없음)
        """
        # 시스템 사거리 조회 (O(1))
        max_range = self.system_ranges.get(system_id)
        if max_range is None or max_range <= 0:
            return self.k_min
        
        # 거리 계산은 이미 threat['current_position']에서 수행됨
        # 여기서는 거리만 받아서 LUT 조회
        # (실제로는 optimizer에서 거리를 전달받음)
        return self.k_min  # Placeholder - optimizer에서 직접 호출
    
    def get_k_from_distance(self, distance: float, max_range: float) -> float:
        """
        거리 기반 K값 계산 (LUT 사용, O(1))
        
        Args:
            distance: 위협-시스템 거리 (km)
            max_range: 시스템 최대 사거리 (km)
        
        Returns:
            K값 (0.6 ~ 1.0)
        
        성능: 나눗셈 1회 + 배열 인덱싱 (곱셈 없음)
        """
        if distance <= 0 or max_range <= 0:
            return self.k_min
        
        # 거리 비율 계산 (나눗셈 1회)
        ratio = 1.0 - (distance / max_range)
        
        # 범위 체크
        if ratio <= 0:
            return self.k_min
        elif ratio >= 1:
            return self.k_max
        
        # LUT 인덱싱 (O(1), 초고속)
        idx = int(ratio * self.LUT_SIZE)
        return self.k_lut[idx]
    
    def get_k_value(self, threat_id: str, system_id: str) -> float:
        """Warmstart용 K값 조회 (별칭)"""
        return self.get_k(threat_id, system_id)
    
    def _calculate_k_factor(self, threat, system, engagement_matrix, current_time: float = 0.0) -> float:
        """
        K-factor 계산 로직 (LUT 기반 최적화)

        핵심 원칙:
        1. 교전 윈도우: 사거리 70%에서 시작 (권장 교전 거리)
        2. 최적 거리: 사거리 50%에서 최고 확률 (Sweet spot)
        3. 윈도우 길이: 길수록 높은 k (여유 있는 교전)
        4. 중간 진입: 윈도우 시작점보다 늦게 할당받으면 페널티

        최적화:
        - dict.get() 호출 제거 → 캐시 사용
        - 분기문 제거 → LUT 배열 인덱싱
        - 연산 수 감소: 15회 → 6회

        Args:
            threat: 위협 정보
            system: 요격 시스템 정보
            engagement_matrix: 교전 매트릭스 (사용 안함 - 캐시 사용)
            current_time: 현재 시간 (초)

        Returns:
            float: 개선된 k-factor [k_min, k_max]
        """
        key = (threat.id, system.id)

        # 🔥 1단계: 윈도우 정보 캐시에서 조회 (dict.get() 제거)
        window_data = self.window_cache.get(key)
        if not window_data:
            return self.k_min
        
        window_start, window_end, window_duration = window_data
        
        if window_duration <= 0 or current_time > window_end:
            return self.k_min

        # 🔥 2단계: k_distance - LUT 인덱싱 (분기문 제거)
        distance = self.distance_cache.get(key, 0.0)
        max_range = self.system_ranges.get(system.id, 1.0)
        
        if distance <= 0 or max_range <= 0:
            k_distance = self.k_min
        else:
            distance_ratio = distance / max_range
            # LUT 인덱싱 (O(1), 분기문 없음)
            idx = int(distance_ratio * self.LUT_SIZE)
            idx = min(idx, self.LUT_SIZE)  # 범위 체크
            k_distance = self.k_distance_lut[idx]

        # 🔥 3단계: T (시간적 요소) - 논문 수식 T = k_min + (1-k_min)*sqrt(min(Δt/t_opt, 1))
        t_optimal = 60.0  # 최적 교전창 길이 (초)
        T = self.k_min + (1.0 - self.k_min) * np.sqrt(min(window_duration / t_optimal, 1.0))

        # 🔥 4단계: K (운동학적 요소) - 표적 고도·속도 기반
        phase_events = {}
        if hasattr(threat, 'get'):
            phase_events = threat.get('phase_events', {})
        if not phase_events and hasattr(threat, 'phase_events'):
            phase_events = threat.phase_events or {}

        specs = {}
        if hasattr(threat, 'get'):
            specs = threat.get('specs', {})
        if not specs and hasattr(threat, 'specs'):
            specs = threat.specs or {}

        critical_alt_km = (phase_events.get('critical_altitude_km')
                           or specs.get('max_altitude_km', 30.0))

        if phase_events.get('terminal_velocity_ms'):
            terminal_vel_ms = phase_events['terminal_velocity_ms']
        else:
            mach = specs.get('speed_mach', 4.0)
            terminal_vel_ms = mach * 343.0
        missile_speed_kms = terminal_vel_ms / 1000.0

        optimal_alt = 30.0
        if critical_alt_km < 5.0:
            altitude_factor = 0.8
        elif critical_alt_km > 80.0:
            altitude_factor = 0.9
        else:
            dev = abs(critical_alt_km - optimal_alt)
            altitude_factor = max(0.8, 1.0 - 0.2 * (dev / optimal_alt))

        optimal_speed = 2.0
        max_speed     = 5.0
        if missile_speed_kms > max_speed:
            speed_factor = 0.8
        else:
            ratio = missile_speed_kms / optimal_speed
            speed_factor = max(0.8, 1.0 - 0.2 * max(0.0, ratio - 1.0))

        K_factor = min(altitude_factor * speed_factor, 1.0)

        # 🔥 5단계: 최종 K-factor - 논문 수식 K_ij = T^c1 * G^c2 * K^c3 * E^c4
        # G = k_distance (기하학적), E = 1.0 (이상 환경 조건 가정)
        c1, c2, c3, c4 = 0.25, 0.30, 0.25, 0.20
        G = k_distance
        E = 1.0
        k_ij = (T ** c1) * (G ** c2) * (K_factor ** c3) * (E ** c4)

        return np.clip(k_ij, self.k_min, self.k_max)


class McCormickCoefficients:
    """McCormick Relaxation 계수 사전 계산 (최적화 #3)"""
    
    def __init__(self, k_min: float = 0.6, k_max: float = 1.0, missiles_per_engagement: int = 2):
        self.k_min = k_min
        self.k_max = k_max
        self.missiles_per_engagement = missiles_per_engagement
        self.coeffs: Dict[Tuple[str, str], Dict] = {}
    
    def precompute(self, threats: List, systems: List, k_cache: KFactorCache):
        """
        모든 조합의 McCormick linearization 계수 계산
        
        Args:
            threats: Threat 리스트
            systems: InterceptorSystem 리스트
            k_cache: K-factor 캐시
        """
        print("사전 계산 시작: McCormick Coefficients")
        
        for threat in threats:
            for system in systems:
                key = (threat.id, system.id)
                
                # 단발 요격 확률
                P_single = system.intercept_probability
                # 2발 살보 요격 확률
                P_total = 1.0 - (1.0 - P_single) ** self.missiles_per_engagement
                
                k = k_cache.get_k(threat.id, system.id)
                
                # ln(1 - P) 계산 (한 번만)
                if P_total >= 1.0:
                    log_term = -1e10
                elif P_total <= 0.0:
                    log_term = 0.0
                else:
                    log_term = np.log(1.0 - P_total)
                
                # McCormick envelope 계수들
                self.coeffs[key] = {
                    'P_single': P_single,
                    'P_total': P_total,
                    'log_1_minus_P': log_term,
                    'k_value': k,
                    'k_lower': self.k_min,
                    'k_upper': self.k_max,
                    'kP_min': self.k_min * P_total,
                    'kP_max': self.k_max * P_total,
                }
        
        print(f"[OK] McCormick 계수 계산 완료: {len(self.coeffs)} 조합")
    
    def get_coeffs(self, threat_id: str, system_id: str) -> Optional[Dict]:
        """계수 조회 (O(1) lookup)"""
        return self.coeffs.get((threat_id, system_id), None)


class StateFilter:
    """Invalid state 필터링 (최적화 #2)"""
    
    @staticmethod
    def get_valid_states_for_threat(
        threat_id: str, 
        systems: List, 
        engagement_matrix: EnhancedEngagementMatrix,
        max_combination_size: int = 3
    ) -> List[Set[str]]:
        """
        특정 위협에 대해 유효한 state 조합만 생성
        
        Args:
            threat_id: 위협 ID
            systems: InterceptorSystem 리스트
            engagement_matrix: 교전 가능성 매트릭스
            max_combination_size: 최대 조합 크기
            
        Returns:
            유효한 state 리스트
        """
        # 1. Feasible systems 필터링
        feasible_systems = [
            s for s in systems 
            if engagement_matrix.is_feasible(s.id, threat_id)
        ]
        
        if not feasible_systems:
            return [set()]  # Empty state만
        
        valid_states = [set()]  # Empty state
        
        # 2. 조합 생성 (크기 제한)
        actual_max_size = min(max_combination_size, len(feasible_systems))
        
        for size in range(1, actual_max_size + 1):
            for combination in itertools.combinations(feasible_systems, size):
                state = set([s.id for s in combination])
                valid_states.append(state)
        
        return valid_states


class BinaryTreeMcCormickCache:
    """
    🆕 Binary Tree McCormick 계수 캐시 (선택적 최적화)
    
    자산별 생존 확률 곱셈에 사용되는 McCormick 계수를 사전 계산
    실제로는 변수가 동적으로 생성되므로 제한적 효과
    """
    
    def __init__(self):
        self.tree_depth_cache = {}  # {n_vars: depth}
        self.mccormick_count_cache = {}  # {n_vars: count}
    
    def get_tree_depth(self, n_variables: int) -> int:
        """Binary Tree 깊이 계산 (캐싱)"""
        if n_variables in self.tree_depth_cache:
            return self.tree_depth_cache[n_variables]
        
        import math
        depth = math.ceil(math.log2(n_variables)) if n_variables > 0 else 0
        self.tree_depth_cache[n_variables] = depth
        return depth
    
    def get_mccormick_count(self, n_variables: int) -> int:
        """필요한 McCormick 적용 횟수 계산 (캐싱)"""
        if n_variables in self.mccormick_count_cache:
            return self.mccormick_count_cache[n_variables]
        
        # n개 변수 → n-1회 McCormick (Binary Tree)
        count = max(0, n_variables - 1)
        self.mccormick_count_cache[n_variables] = count
        return count
    
    def estimate_constraints(self, n_variables: int) -> int:
        """예상 제약 개수 계산"""
        # 각 McCormick당 4개 제약
        return self.get_mccormick_count(n_variables) * 4
