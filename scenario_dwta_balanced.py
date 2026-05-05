"""
DWTA 벤치마크 최적화 시나리오
================================
학술 논문용 균형잡힌 DWTA 시나리오 설계

목표:
- 알고리즘 차별성 명확화 (MIP vs GA vs Greedy)
- 자원 제약 현실화 (과도한 자원 제거)
- 공정한 위협 분배 (모든 자산에 균등)
- 적절한 난이도 (GA 85~95%, MIP 90~98%)
"""

from typing import Dict, List
from config_mip import AssetConfig, InterceptorSystemConfig

# 🎯 포대 동시 교전 능력 설정 (전역 상수)
SIMULTANEOUS_ENGAGEMENTS_LSAM = 6 # LSAM 포대 동시 교전 가능 수
SIMULTANEOUS_ENGAGEMENTS_MSAM = 6  # MSAM 포대 동시 교전 가능 수

class DWTABalancedScenario:
    """DWTA 벤치마크용 균형 시나리오"""
    
    @staticmethod
    def create_balanced_assets() -> List[Dict]:
        """
        균형잡힌 자산 가치 분포 (10개)
        - 균등 분포로 편차 최소화
        - 총 가치: 9,500
        """
        assets = [
            # 3계층 구조: 고가(4개), 중가(3개), 저가(3개)
            # 고가 자산 (1200~1500)
            {"id": "A01", "name": "Blue_House", "position": (0, 0), "value": 1500, "priority": 1},
            {"id": "A02", "name": "Defense_Ministry", "position": (2, -1), "value": 1400, "priority": 1},
            {"id": "A03", "name": "Intelligence_Service", "position": (-3, 1), "value": 1300, "priority": 1},
            {"id": "A04", "name": "Gyeryong_Command", "position": (15, -25), "value": 1200, "priority": 1},
            
            # 중가 자산 (800~1000)
            {"id": "A05", "name": "Pyeongtaek_US_Base", "position": (5, -15), "value": 1000, "priority": 2},
            {"id": "A06", "name": "Osan_Air_Base", "position": (8, -20), "value": 900, "priority": 2},
            {"id": "A07", "name": "Incheon_Airport", "position": (-25, 15), "value": 800, "priority": 2},
            
            # 저가 자산 (500~700)
            {"id": "A08", "name": "Busan_Port", "position": (50, -80), "value": 700, "priority": 3},
            {"id": "A09", "name": "Incheon_Port", "position": (-20, 10), "value": 600, "priority": 3},
            {"id": "A10", "name": "Gimpo_Airport", "position": (-10, 5), "value": 500, "priority": 3}
        ]
        
        # 통계 출력
        values = [a['value'] for a in assets]
        print(f"자산 가치 분포: 평균={sum(values)/len(values):.0f}, 총합={sum(values)}, 범위={min(values)}~{max(values)}")
        
        return assets
    
    @staticmethod
    def create_balanced_threats() -> List[Dict]:
        """
        균형잡힌 위협 분배 (20발)
        - 모든 자산에 정확히 2발씩 할당
        - 동시 발사 + 순차 발사 혼합
        """
        threats = []
        
        # 자산 목록 (위치 정보 포함)
        assets = DWTABalancedScenario.create_balanced_assets()
        asset_map = {asset["id"]: asset["position"] for asset in assets}
        asset_ids = [f"A{i:02d}" for i in range(1, 11)]
        
        # 각 자산당 2발씩 할당
        threat_id = 1
        
        # 1차 공격파: 각 자산에 1발씩 (0~90초, 10초 간격)
        for i, asset_id in enumerate(asset_ids):
            threats.append({
                "id": f"T{threat_id:02d}",
                "name": f"Nodong_{threat_id}",
                "type": "NODONG",
                "target_asset_id": asset_id,
                "target_position": asset_map[asset_id],  # 교전 매트릭스 계산용
                "launch_time": i * 10,  # 0, 10, 20, ..., 90초
                "flight_time": 480,
                "launch_position": (i * 20 - 90, 500),  # Y축 500km (상승+하강 모두 교전 가능)
                "trajectory_type": "ballistic",
                "rcs": 1.5,
                "phase_events": {
                    "midcourse_time": i * 10 + 240,
                    "terminal_time": i * 10 + 320,
                    "critical_altitude_km": 55.0,  # LSAM 최적 범위 (40~70km 중간)
                    "terminal_velocity_ms": 1800
                },
                "specs": {
                    "max_range_km": 1300,
                    "max_altitude_km": 80,
                    "speed_mach": 3.5,
                    "payload_kg": 800,
                    "cep_m": 2000,
                    "launch_weight_kg": 16500
                }
            })
            threat_id += 1
        
        # 2차 공격파: MSAM 담당 자산을 목표로 (120~210초, 10초 간격)
        # MSAM 담당 자산: A01,A02,A03 (MSAM_01), A07,A09,A10 (MSAM_02), A04,A05 (MSAM_03)
        scud_targets = ["A05", "A02", "A03", "A07", "A09", "A10", "A04", "A05", "A01", "A02"]  # T11: A01→A05 (MSAM 사거리 내)
        
        for i, target_asset_id in enumerate(scud_targets):
            # 🆕 T11 특별 처리: 비행시간 연장 + 발사 위치 원거리화 (할당 윈도우 확보)
            if i == 0:  # T11 (첫 번째 SCUD_B)
                flight_time_scud = 350  # 270→350초 (80초 연장)
                launch_y_scud = 120  # Y=120km (더 먼 거리)
            else:
                flight_time_scud = 270  # 기본 비행시간
                launch_y_scud = 80  # 기본 발사 위치
            
            threats.append({
                "id": f"T{threat_id:02d}",
                "name": f"ScudB_{threat_id}",
                "type": "SCUD_B",
                "target_asset_id": target_asset_id,
                "target_position": asset_map[target_asset_id],  # 교전 매트릭스 계산용
                "launch_time": 140 + i * 10,  # 140, 150, 160, ..., 230초 (10초 앞당김)
                "flight_time": flight_time_scud,
                "launch_position": (i * 15 - 70, launch_y_scud),
                "trajectory_type": "ballistic",
                "rcs": 0.8,
                "phase_events": {
                    "midcourse_time": 140 + i * 10 + int(flight_time_scud * 0.5),  # 중간 단계 (비행 50%)
                    "terminal_time": 140 + i * 10 + int(flight_time_scud * 0.81),  # 종말 단계 (비행 81%)
                    "critical_altitude_km": 25.0,
                    "terminal_velocity_ms": 1200
                },
                "specs": {
                    "max_range_km": 300,
                    "max_altitude_km": 40,
                    "speed_mach": 2.5,
                    "payload_kg": 985,
                    "cep_m": 450,
                    "launch_weight_kg": 5900
                }
            })
            threat_id += 1
        
        # 통계 출력
        print(f"위협 분배: 총 {len(threats)}발, 자산당 {len(threats)//10}발")
        
        # 표적 분포 확인
        target_dist = {}
        for t in threats:
            target = t['target_asset_id']
            target_dist[target] = target_dist.get(target, 0) + 1
        print(f"표적 분포: {target_dist}")
        
        return threats
    
    @staticmethod
    def create_constrained_batteries() -> List[Dict]:
        """
        제약된 방어 자원 (6개 포대)
        - LSAM 3개 (20발/포대) = 60발
        - MSAM 3개 (30발/포대) = 90발
        - 총 150발 (위협 20발 대비 7.5배)
        """
        batteries = [
            # 상층 방어 (LSAM) - 3개 포대
            {
                "id": "LSAM_01",
                "name": "Seoul_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (0, 0),
                "coverage_radius_km": 150,
                "defense_zone": "ZONE_1_SEOUL",
                "dedicated_assets": ["A01", "A02", "A03", "A04"],
                "specs": {
                    **InterceptorSystemConfig.get_lsam_specs(),
                    "battery_config": {
                        "launchers": 4,
                        "missiles_per_launcher": 5,  # 6→5
                        "total_missiles": 20,  # 24→20
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_LSAM
                    }
                }
            },
            {
                "id": "LSAM_02",
                "name": "Central_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (10, -20),
                "coverage_radius_km": 150,
                "defense_zone": "ZONE_2_CENTRAL",
                "dedicated_assets": ["A05", "A06", "A07"],
                "specs": {
                    **InterceptorSystemConfig.get_lsam_specs(),
                    "battery_config": {
                        "launchers": 4,
                        "missiles_per_launcher": 5,
                        "total_missiles": 20,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_LSAM
                    }
                }
            },
            {
                "id": "LSAM_03",
                "name": "South_LSAM",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (50, -75),
                "coverage_radius_km": 150,
                "defense_zone": "ZONE_3_SOUTH",
                "dedicated_assets": ["A08", "A09", "A10"],
                "specs": {
                    **InterceptorSystemConfig.get_lsam_specs(),
                    "battery_config": {
                        "launchers": 4,
                        "missiles_per_launcher": 5,
                        "total_missiles": 20,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_LSAM
                    }
                }
            },
            
            # 하층 방어 (MSAM) - 3개 포대
            {
                "id": "MSAM_01",
                "name": "Seoul_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (5, -5),
                "coverage_radius_km": 40,
                "defense_zone": "ZONE_1_SEOUL",
                "dedicated_assets": ["A01", "A02", "A03", "A04"],
                "specs": {
                    **InterceptorSystemConfig.get_msam_specs(),
                    "battery_config": {
                        "launchers": 6,
                        "missiles_per_launcher": 5,  # 8→5
                        "total_missiles": 30,  # 48→30
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_MSAM
                    }
                }
            },
            {
                "id": "MSAM_02",
                "name": "Central_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (15, -25),
                "coverage_radius_km": 40,
                "defense_zone": "ZONE_2_CENTRAL",
                "dedicated_assets": ["A05", "A06", "A07"],
                "specs": {
                    **InterceptorSystemConfig.get_msam_specs(),
                    "battery_config": {
                        "launchers": 6,
                        "missiles_per_launcher": 5,
                        "total_missiles": 30,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_MSAM
                    }
                }
            },
            {
                "id": "MSAM_03",
                "name": "South_MSAM",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (55, -80),
                "coverage_radius_km": 40,
                "defense_zone": "ZONE_3_SOUTH",
                "dedicated_assets": ["A08", "A09", "A10"],
                "specs": {
                    **InterceptorSystemConfig.get_msam_specs(),
                    "battery_config": {
                        "launchers": 6,
                        "missiles_per_launcher": 5,
                        "total_missiles": 30,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_MSAM
                    }
                }
            }
        ]
        
        # 통계 출력
        total_missiles = sum(b['specs']['battery_config']['total_missiles'] for b in batteries)
        print(f"방어 자원: 총 {len(batteries)}개 포대, {total_missiles}발 미사일")
        
        return batteries


class ScenarioManager:
    """통합 시나리오 관리자 - config_mip.py의 모든 시나리오를 DWTA 설계 원칙으로 재구현"""
    
    @staticmethod
    def get_scenario_list() -> Dict[str, str]:
        """사용 가능한 모든 시나리오 목록"""
        return {
            # 확장성 테스트 (Scalability)
            "SMALL_3": "초소규모 (3발 - 알고리즘 검증)",
            "SMALL_5": "소규모 (5발 - 기본 성능)",
            "SMALL_8": "소중규모 (8발 - 전환점)",
            "MEDIUM_10": "중소규모 (10발 - 일반 공격)",
            "BASELINE_15": "중규모 기본 (15발 - 표준)",
            "MEDIUM_20": "중대규모 (20발 - 균형 공격)",
            "HEAVY_30": "대규모 (30발 - 포화 공격)",
            "LARGE_40": "초대규모 (40발 - 한계 테스트)",
            "STRESS_100": "스트레스 100발 + 15포대 (기준, BAT15)",

            # Stress-100 포대 규모 변형 (논문 실험 3)
            "STRESS_100_BAT30": "스트레스 100발 + 30포대 (LSAM 15 + MSAM 15)",
            "STRESS_100_BAT50": "스트레스 100발 + 50포대 (LSAM 25 + MSAM 25)",

            # 공격 패턴
            "SEQUENTIAL_20": "순차 공격 (20발 - 순차 발사)",
            "SIMULTANEOUS_20": "동시 공격 (20발 - 동시 발사)",

            # 표준 벤치마크
            "DWTA_BALANCED": "표준 벤치마크 (20발, 6개 배터리)"
        }
    
    @staticmethod
    def create_scenario(scenario_type: str) -> Dict:
        """시나리오 타입에 따라 자산, 배터리, 위협 생성"""
        if scenario_type == "DWTA_BALANCED":
            return {
                "assets": DWTABalancedScenario.create_balanced_assets(),
                "batteries": DWTABalancedScenario.create_constrained_batteries(),
                "threats": DWTABalancedScenario.create_balanced_threats()
            }
        elif scenario_type in ["SMALL_3", "SMALL_5", "SMALL_8", "MEDIUM_10", "BASELINE_15", 
                               "MEDIUM_20", "HEAVY_30", "LARGE_40", "STRESS_100"]:
            # 숫자 추출
            if "_" in scenario_type:
                num_threats = int(scenario_type.split("_")[1])
            else:
                num_threats = 15  # BASELINE
            
            return {
                "assets": ScenarioManager._create_assets(num_threats),
                "batteries": ScenarioManager._create_batteries(num_threats),
                "threats": ScenarioManager._create_threats(num_threats, pattern="balanced")
            }
        elif scenario_type in ["STRESS_100_BAT30", "STRESS_100_BAT50"]:
            # 포대 수 파싱: STRESS_100_BAT30 → 30
            num_batteries = int(scenario_type.split("_BAT")[1])
            return {
                "assets": ScenarioManager._create_assets(100),
                "batteries": ScenarioManager._create_batteries_n(num_batteries),
                "threats": ScenarioManager._create_threats(100, pattern="balanced")
            }
        elif scenario_type == "SEQUENTIAL_20":
            return {
                "assets": ScenarioManager._create_assets(20),
                "batteries": ScenarioManager._create_batteries(20),
                "threats": ScenarioManager._create_threats(20, pattern="sequential")
            }
        elif scenario_type == "SIMULTANEOUS_20":
            return {
                "assets": ScenarioManager._create_assets(20),
                "batteries": ScenarioManager._create_batteries(20),
                "threats": ScenarioManager._create_threats(20, pattern="simultaneous")
            }
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
    
    @staticmethod
    def _create_assets(num_threats: int) -> List[Dict]:
        """위협 수에 비례한 자산 생성"""
        base_assets = DWTABalancedScenario.create_balanced_assets()
        
        if num_threats <= 10:
            return base_assets
        
        # 위협이 많으면 자산 추가 (최대 20개)
        # HEAVY_30: 30발 → 15개 자산 (각 자산당 2발)
        if num_threats == 30:
            num_assets = 15
        else:
            num_assets = min(20, max(10, num_threats // 2))
        assets = base_assets[:num_assets]
        
        for i in range(len(base_assets), num_assets):
            assets.append({
                "id": f"A{i+1:02d}",
                "name": f"Asset_{i+1}",
                "position": ((i-10) * 10, (i-10) * -8),
                "value": 1000 - (i-10) * 50,
                "priority": 2
            })
        
        return assets
    
    @staticmethod
    def _create_batteries(_num_threats: int) -> List[Dict]:
        """모든 시나리오에서 6개 배터리 고정 (확장성 실험 일관성)"""
        return DWTABalancedScenario.create_constrained_batteries()
    
    @staticmethod
    def _create_batteries_for_30() -> List[Dict]:
        """HEAVY_30 전용: 10개 배터리 (LSAM 5 + MSAM 5)
        
        배치 전략:
        - LSAM 5개: 광역 방어 (150km), 각 20발
        - MSAM 5개: 근접 방어 (40km), 각 30발
        - 총 250발 (30발 위협 대비 8.3배)
        """
        batteries = []
        
        # LSAM 5개 배치 (원형 배치)
        lsam_positions = [
            (0, 20),      # 북쪽
            (30, 0),      # 동쪽
            (0, -20),     # 남쪽
            (-30, 0),     # 서쪽
            (0, 0)        # 중앙
        ]
        
        for i in range(5):
            batteries.append({
                "id": f"LSAM_{i+1:02d}",
                "name": f"LSAM_BAT{i+1}",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": lsam_positions[i],
                "coverage_radius_km": 150,
                "defense_zone": f"ZONE_L{i+1}",
                "dedicated_assets": [f"A{(i*3+j)%15+1:02d}" for j in range(3)],
                "specs": {
                    **InterceptorSystemConfig.get_lsam_specs(),
                    "battery_config": {
                        "launchers": 4,
                        "missiles_per_launcher": 5,
                        "total_missiles": 20,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_LSAM
                    }
                }
            })
        
        # MSAM 5개 배치 (내부 원형 배치)
        msam_positions = [
            (15, 10),     # 북동
            (15, -10),    # 남동
            (-15, -10),   # 남서
            (-15, 10),    # 북서
            (0, -5)       # 중앙 남쪽
        ]
        
        for i in range(5):
            batteries.append({
                "id": f"MSAM_{i+1:02d}",
                "name": f"MSAM_BAT{i+1}",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": msam_positions[i],
                "coverage_radius_km": 40,
                "defense_zone": f"ZONE_M{i+1}",
                "dedicated_assets": [f"A{(i*3+j)%15+1:02d}" for j in range(3)],
                "specs": {
                    **InterceptorSystemConfig.get_msam_specs(),
                    "battery_config": {
                        "launchers": 6,
                        "missiles_per_launcher": 5,
                        "total_missiles": 30,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_MSAM
                    }
                }
            })
        
        return batteries
    
    @staticmethod
    def _create_batteries_n(n: int) -> List[Dict]:
        """논문 실험용: 임의의 포대 수 N개 생성 (LSAM:MSAM = 1:1, 반올림)

        Args:
            n: 총 포대 수 (15, 30, 50 등)
        배치 전략: 균등 격자 배치, LSAM은 광역 방어 (coverage 150km), MSAM은 정밀 방어 (coverage 40km)
        """
        import math
        num_lsam = math.ceil(n / 2)
        num_msam = n - num_lsam

        batteries = []
        assets_per_bat = max(1, 10 // num_lsam)

        for i in range(num_lsam):
            # 격자 배치: 대각선 방향으로 분산
            angle = (i / num_lsam) * 2 * math.pi
            rx = int(30 * math.cos(angle))
            ry = int(30 * math.sin(angle) - 20)
            # 전담 자산 (순환 배분)
            start_idx = (i * assets_per_bat) % 10
            dedicated = [f"A{(start_idx + j) % 10 + 1:02d}" for j in range(assets_per_bat)]
            batteries.append({
                "id": f"LSAM_{i+1:02d}",
                "name": f"LSAM_BAT{i+1}",
                "system_type": "LSAM",
                "layer": "UPPER",
                "position": (rx, ry),
                "coverage_radius_km": 150,
                "defense_zone": f"ZONE_L{i+1}",
                "dedicated_assets": dedicated,
                "specs": {
                    **InterceptorSystemConfig.get_lsam_specs(),
                    "battery_config": {
                        "launchers": 4,
                        "missiles_per_launcher": 6,
                        "total_missiles": 24,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_LSAM
                    }
                }
            })

        assets_per_bat_m = max(1, 10 // num_msam)
        for i in range(num_msam):
            angle = (i / num_msam) * 2 * math.pi
            rx = int(20 * math.cos(angle))
            ry = int(20 * math.sin(angle) - 15)
            start_idx = (i * assets_per_bat_m) % 10
            dedicated = [f"A{(start_idx + j) % 10 + 1:02d}" for j in range(assets_per_bat_m)]
            batteries.append({
                "id": f"MSAM_{i+1:02d}",
                "name": f"MSAM_BAT{i+1}",
                "system_type": "MSAM",
                "layer": "LOWER",
                "position": (rx + 5, ry - 5),
                "coverage_radius_km": 40,
                "defense_zone": f"ZONE_M{i+1}",
                "dedicated_assets": dedicated,
                "specs": {
                    **InterceptorSystemConfig.get_msam_specs(),
                    "battery_config": {
                        "launchers": 6,
                        "missiles_per_launcher": 8,
                        "total_missiles": 48,
                        "simultaneous_engagements": SIMULTANEOUS_ENGAGEMENTS_MSAM
                    }
                }
            })

        total_missiles = sum(b['specs']['battery_config']['total_missiles'] for b in batteries)
        print(f"[배터리 구성] {n}개 포대 (LSAM {num_lsam} + MSAM {num_msam}), 총 {total_missiles}발")
        return batteries

    @staticmethod
    def _create_threats(num_threats: int, pattern: str = "balanced") -> List[Dict]:
        """
        DWTA 설계 원칙을 적용한 위협 생성
        - NODONG: Y=500km (상층 방어)
        - SCUD_B: Y=80km (하층 방어, 실시간 거리 체크)
        - 발사 간격: McCormick 솔버 최적화
        """
        threats = []
        assets = ScenarioManager._create_assets(num_threats)
        asset_map = {a["id"]: a["position"] for a in assets}
        asset_ids = [a["id"] for a in assets]
        
        # 발사 간격 계산 (McCormick 솔버 최적화)
        if num_threats <= 5:
            interval = 15
        elif num_threats <= 10:
            interval = 10
        elif num_threats <= 20:
            interval = 8
        elif num_threats <= 30:
            interval = 6
        elif num_threats <= 50:
            interval = 5
        else:
            # STRESS_100: 2초 간격으로 요격과 발사가 동시 진행되어 45개 할당 슬롯 효율적 활용
            interval = 2
        
        # 공격 패턴별 발사 시간 계산
        if pattern == "simultaneous":
            # 동시 발사: 모두 T=0
            launch_times = [0] * num_threats
        elif pattern == "sequential":
            # 순차 발사: 긴 간격
            launch_times = [i * interval * 2 for i in range(num_threats)]
        else:
            # 균형 발사: 표준 간격
            launch_times = [i * interval for i in range(num_threats)]
        
        # NODONG vs SCUD_B 비율 (40:60 - MSAM 활용 최적화)
        # STRESS_100: 40 NODONG (LSAM), 60 SCUD_B (MSAM) → 하층 방어 강화
        num_nodong = int(num_threats * 0.4)  # 40%
        num_scud = num_threats - num_nodong  # 60%
        
        # 발사 위치 범위: 포대 커버리지 내로 제한
        # LSAM 150km, MSAM 40km 커버리지 기준으로
        # NODONG 터미널 단계(Y≈50~150) 시 LSAM 반경 내 진입 보장: X ±120km
        # SCUD_B 터미널 단계(Y≈20~40) 시 MSAM 반경 내 진입 보장: X ±100km
        if num_threats > 50:
            nodong_x_half = 120  # LSAM 커버리지 내 집중
            scud_x_half   = 100  # MSAM 커버리지 내 집중
        else:
            nodong_x_half = num_nodong * 10
            scud_x_half   = num_scud * 6

        # NODONG 미사일 생성 (상층 방어)
        for i in range(num_nodong):
            target_asset = asset_ids[i % len(asset_ids)]
            if num_nodong > 1:
                nodong_x = round(i * 2 * nodong_x_half / (num_nodong - 1) - nodong_x_half)
            else:
                nodong_x = 0
            threats.append({
                "id": f"T{i+1:02d}",
                "name": f"Nodong_{i+1}",
                "type": "NODONG",
                "target_asset_id": target_asset,
                "target_position": asset_map[target_asset],
                "launch_time": launch_times[i],
                "flight_time": 480,
                "launch_position": (nodong_x, 500),
                "trajectory_type": "ballistic",
                "rcs": 1.5,
                "phase_events": {
                    "midcourse_time": launch_times[i] + 240,
                    "terminal_time": launch_times[i] + 320,
                    "critical_altitude_km": 55.0,
                    "terminal_velocity_ms": 1800
                },
                "specs": {
                    "max_range_km": 1300,
                    "max_altitude_km": 80,
                    "speed_mach": 3.5,
                    "payload_kg": 800,
                    "cep_m": 2000,
                    "launch_weight_kg": 16500
                }
            })

        # SCUD_B 발사 타이밍: NODONG과 병행 (T=40부터 1.5초 간격)
        scud_start_time = 40
        scud_interval = 1.5

        # SCUD_B 미사일 생성 (하층 방어)
        for i in range(num_scud):
            target_asset = asset_ids[i % len(asset_ids)]
            threat_id = num_nodong + i + 1
            launch_time = scud_start_time + (i * scud_interval)
            if num_scud > 1:
                scud_x = round(i * 2 * scud_x_half / (num_scud - 1) - scud_x_half)
            else:
                scud_x = 0
            threats.append({
                "id": f"T{threat_id:02d}",
                "name": f"ScudB_{threat_id}",
                "type": "SCUD_B",
                "target_asset_id": target_asset,
                "target_position": asset_map[target_asset],
                "launch_time": launch_time,
                "flight_time": 300,
                "launch_position": (scud_x, 80),
                "trajectory_type": "ballistic",
                "rcs": 0.8,
                "phase_events": {
                    "midcourse_time": launch_time + 135,
                    "terminal_time": launch_time + 220,
                    "critical_altitude_km": 25.0,
                    "terminal_velocity_ms": 1200
                },
                "specs": {
                    "max_range_km": 300,
                    "max_altitude_km": 40,
                    "speed_mach": 2.5,
                    "payload_kg": 985,
                    "cep_m": 450,
                    "launch_weight_kg": 5900
                }
            })
        
        print(f"시나리오 생성: {num_threats}발 (NODONG: {num_nodong}, SCUD_B: {num_scud}), 간격: {interval}초, 패턴: {pattern}")
        print(f"  - NODONG 발사: T=0~{launch_times[num_nodong-1] if num_nodong > 0 else 0}s (간격 {interval}s, LSAM 타겟)")
        print(f"  - SCUD_B 발사: T={scud_start_time}~{scud_start_time + (num_scud-1)*scud_interval if num_scud > 0 else scud_start_time:.1f}s (간격 {scud_interval}s, MSAM 타겟)")
        print(f"  → 하층 방어 최적화: SCUD {num_scud}발 (60%) vs NODONG {num_nodong}발 (40%)")
        return threats


# 사용 예시
if __name__ == "__main__":
    print("=" * 80)
    print("DWTA 균형 시나리오 설계")
    print("=" * 80)
    
    scenario = DWTABalancedScenario()
    
    print("\n[1] 자산 구성")
    assets = scenario.create_balanced_assets()
    
    print("\n[2] 위협 구성")
    threats = scenario.create_balanced_threats()
    
    print("\n[3] 방어 자원")
    batteries = scenario.create_constrained_batteries()
    
    print("\n" + "=" * 80)
    print("시나리오 요약")
    print("=" * 80)
    print(f"자산: {len(assets)}개, 총 가치: {sum(a['value'] for a in assets):,}")
    print(f"위협: {len(threats)}발 (자산당 {len(threats)//len(assets)}발)")
    print(f"방어: {len(batteries)}개 포대, 총 {sum(b['specs']['battery_config']['total_missiles'] for b in batteries)}발")
    print(f"자원 비율: {sum(b['specs']['battery_config']['total_missiles'] for b in batteries) / len(threats):.1f}배")
    print("\n예상 성능:")
    print("  MIP:    90~98% (최적 할당)")
    print("  GA:     85~95% (준최적)")
    print("  Greedy: 60~75% (휴리스틱)")
    print("=" * 80)
