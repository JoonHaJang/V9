"""
시나리오 시스템 테스트 스크립트
다양한 시나리오 버전이 올바르게 생성되는지 확인
"""

from config_mip import MIPConfig, ScenarioManager

def test_scenarios():
    """모든 시나리오 테스트"""
    
    print("=" * 80)
    print("시나리오 시스템 테스트")
    print("=" * 80)
    
    # 사용 가능한 시나리오 목록
    scenario_list = ScenarioManager.get_scenario_list()
    print(f"\n사용 가능한 시나리오: {len(scenario_list)}개")
    for key, desc in scenario_list.items():
        print(f"  - {key}: {desc}")
    
    print("\n" + "=" * 80)
    
    # 각 시나리오 테스트
    for scenario_type in scenario_list.keys():
        print(f"\n[{scenario_type}] 테스트 중...")
        
        try:
            # MIPConfig 생성
            config = MIPConfig(scenario_type=scenario_type)
            
            # 시나리오 생성
            scenario = config.create_realistic_scenario()
            
            # 결과 출력
            print(f"  [OK] 시나리오 이름: {scenario['name']}")
            print(f"  [OK] 설명: {scenario['description']}")
            print(f"  [OK] 자산 수: {len(scenario['assets'])}개")
            print(f"  [OK] 포대 수: {len(scenario['batteries'])}개")
            print(f"  [OK] 위협 수: {len(scenario['threats'])}발")
            
            # 위협 발사 시간 분석
            threats = scenario['threats']
            if threats:
                launch_times = [t['launch_time'] for t in threats]
                print(f"  [OK] 발사 시간 범위: {min(launch_times)}초 ~ {max(launch_times)}초")
                
                # 동시 발사 분석 (5초 이내)
                simultaneous_count = 0
                for i in range(len(launch_times) - 1):
                    if launch_times[i+1] - launch_times[i] <= 5:
                        simultaneous_count += 1
                
                print(f"  [OK] 동시 발사 특성: {simultaneous_count}/{len(threats)-1} 쌍이 5초 이내")
                
                # 표적 분포
                target_distribution = {}
                for threat in threats:
                    target = threat.get('target_asset_id', 'Unknown')
                    target_distribution[target] = target_distribution.get(target, 0) + 1
                
                print(f"  [OK] 표적 분포: {len(target_distribution)}개 자산 대상")
                
        except Exception as e:
            print(f"  [ERROR] 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)

def test_scenario_comparison():
    """시나리오 비교 분석"""
    
    print("\n" + "=" * 80)
    print("시나리오 비교 분석")
    print("=" * 80)
    
    scenarios_to_compare = ["LIGHT_5", "BASELINE_15", "HEAVY_30", "HEAVY_50"]
    
    print(f"\n{'시나리오':<20} {'위협 수':<10} {'평균 간격':<15} {'최대 동시':<15}")
    print("-" * 70)
    
    for scenario_type in scenarios_to_compare:
        config = MIPConfig(scenario_type=scenario_type)
        scenario = config.create_realistic_scenario()
        threats = scenario['threats']
        
        # 평균 발사 간격 계산
        launch_times = sorted([t['launch_time'] for t in threats])
        if len(launch_times) > 1:
            intervals = [launch_times[i+1] - launch_times[i] for i in range(len(launch_times)-1)]
            avg_interval = sum(intervals) / len(intervals)
        else:
            avg_interval = 0
        
        # 최대 동시 발사 수 (5초 윈도우)
        max_simultaneous = 1
        for i, t1 in enumerate(launch_times):
            count = sum(1 for t2 in launch_times[i:] if t2 - t1 <= 5)
            max_simultaneous = max(max_simultaneous, count)
        
        print(f"{scenario_type:<20} {len(threats):<10} {avg_interval:<15.1f} {max_simultaneous:<15}")
    
    print("=" * 80)

if __name__ == "__main__":
    test_scenarios()
    test_scenario_comparison()
