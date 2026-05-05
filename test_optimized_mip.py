"""
Optimized MIP 성능 테스트 스크립트
=================================
기존 MIP vs 최적화 MIP 비교 테스트
"""

import sys
import time
from optimized_mip_wrapper import (
    OptimizedMIPWrapper,
    compare_optimizers,
    Asset,
    InterceptorSystem,
    Threat
)

def create_test_scenario(num_threats=20):
    """테스트 시나리오 생성"""

    print(f"\n📦 Creating test scenario with {num_threats} threats...")

    # Assets
    assets = [
        Asset(
            id=f"A{i}",
            position=(100.0 + i*10, 100.0),
            value=50.0 - i*5,
            priority=1 if i < 3 else 2,
            estimated_threat_missiles=[]
        )
        for i in range(5)
    ]

    # Batteries
    batteries = [
        {
            'id': f'LSAM_{i}',
            'system_type': 'LSAM',
            'position': (50.0 + i*50, 80.0),
            'available_missiles': 10,
            'specs': {
                'ballistic_missile_specs': {
                    'intercept_probability': 0.85,
                    'engagement_range_km': {'max': 150}
                },
                'battery_config': {
                    'simultaneous_engagements': 3
                }
            }
        }
        for i in range(3)
    ] + [
        {
            'id': f'MSAM_{i}',
            'system_type': 'MSAM',
            'position': (60.0 + i*50, 120.0),
            'available_missiles': 8,
            'specs': {
                'ballistic_missile_specs': {
                    'intercept_probability': 0.78,
                    'engagement_range_km': {'max': 80}
                },
                'battery_config': {
                    'simultaneous_engagements': 2
                }
            }
        }
        for i in range(3)
    ]

    # Interceptor Systems
    systems = []
    for battery in batteries:
        systems.append(
            InterceptorSystem(
                id=battery['id'],
                system_type=battery['system_type'],
                position=battery['position'],
                available_missiles=battery['available_missiles'],
                max_missiles_per_target=2,
                intercept_probability=battery['specs']['ballistic_missile_specs']['intercept_probability'],
                engagement_range=battery['specs']['ballistic_missile_specs']['engagement_range_km']['max']
            )
        )

    # Threats
    threats = []
    for i in range(num_threats):
        asset_idx = i % len(assets)
        threat = Threat(
            id=f"T{i+1}",
            target_asset_id=assets[asset_idx].id,
            current_position=(50.0 + i*5, 150.0 - i*2, 30.0),
            estimated_impact_time=60.0 + i*5,
            flight_time=300.0,
            specs={
                'max_altitude_km': 40.0,
                'avg_speed_kmh': 2000.0
            }
        )
        threats.append(threat)

    print(f"   ✅ Created {len(assets)} assets, {len(batteries)} batteries, {len(threats)} threats")

    return assets, systems, threats, batteries


def test_basic_functionality():
    """기본 기능 테스트"""

    print("\n" + "="*80)
    print("🧪 TEST 1: Basic Functionality")
    print("="*80)

    from config_mip import MIPConfig, EnhancedEngagementMatrix

    # Config
    config = MIPConfig()

    # Scenario
    assets, systems, threats, batteries = create_test_scenario(num_threats=10)

    # Enhanced Engagement Matrix
    print("\n📐 Creating Enhanced Engagement Matrix...")
    engagement_matrix = EnhancedEngagementMatrix()
    threats_dict = [
        {
            'id': t.id,
            'launch_position': t.launch_position,
            'target_position': next((a.position for a in assets if a.id == t.target_asset_id), (0, 0)),
            'specs': t.specs,
            'phase_events': {},
            'flight_time': t.flight_time,
            'target_asset_id': t.target_asset_id
        }
        for t in threats
    ]
    computed = engagement_matrix.add_new_threats(batteries, threats_dict)
    print(f"   ✅ Computed {computed} threat engagement windows")

    # Create optimizer
    print("\n🚀 Creating Optimized MIP Optimizer...")
    optimizer = OptimizedMIPWrapper(config)

    # Create model
    print("\n📊 Creating model...")
    model = optimizer.create_model(
        assets=assets,
        interceptor_systems=systems,
        threats=threats,
        batteries=batteries,
        engagement_matrix=engagement_matrix
    )

    if model is None:
        print("❌ Model creation failed!")
        return False

    # Solve
    print("\n🎯 Solving...")
    result = optimizer.solve(time_limit=30.0, mip_gap=0.02)

    # Results
    print("\n" + "="*80)
    print("📊 RESULTS")
    print("="*80)
    print(f"Status: {result['status']}")
    print(f"Feasible: {result['feasible']}")
    print(f"Objective: {result['objective_value']:.2f}")
    print(f"Upper assignments: {len(result['upper_assignments'])}")
    print(f"Lower assignments: {len(result['lower_assignments'])}")

    # Performance report
    print(optimizer.get_performance_report())

    return result['feasible']


def test_performance_comparison():
    """성능 비교 테스트"""

    print("\n" + "="*80)
    print("🧪 TEST 2: Performance Comparison (Original vs Optimized)")
    print("="*80)

    from config_mip import MIPConfig, EnhancedEngagementMatrix

    # Config
    config = MIPConfig()

    # Scenario - 더 큰 규모
    assets, systems, threats, batteries = create_test_scenario(num_threats=50)

    # Enhanced Engagement Matrix
    print("\n📐 Creating Enhanced Engagement Matrix...")
    engagement_matrix = EnhancedEngagementMatrix()
    threats_dict = [
        {
            'id': t.id,
            'launch_position': t.launch_position,
            'target_position': next((a.position for a in assets if a.id == t.target_asset_id), (0, 0)),
            'specs': t.specs,
            'phase_events': {},
            'flight_time': t.flight_time,
            'target_asset_id': t.target_asset_id
        }
        for t in threats
    ]
    computed = engagement_matrix.add_new_threats(batteries, threats_dict)
    print(f"   ✅ Computed {computed} threat engagement windows")

    # Compare
    results = compare_optimizers(
        config=config,
        assets=assets,
        systems=systems,
        threats=threats,
        batteries=batteries,
        engagement_matrix=engagement_matrix
    )

    return results


def test_scalability():
    """확장성 테스트 - 위협 수를 늘려가며 성능 측정"""

    print("\n" + "="*80)
    print("🧪 TEST 3: Scalability Test")
    print("="*80)

    from config_mip import MIPConfig, EnhancedEngagementMatrix

    threat_counts = [10, 20, 50, 100]
    results = {}

    for num_threats in threat_counts:
        print(f"\n{'─'*80}")
        print(f"Testing with {num_threats} threats...")
        print(f"{'─'*80}")

        config = MIPConfig()
        assets, systems, threats, batteries = create_test_scenario(num_threats=num_threats)

        # Engagement Matrix
        engagement_matrix = EnhancedEngagementMatrix()
        threats_dict = [
            {
                'id': t.id,
                'launch_position': t.launch_position,
                'target_position': next((a.position for a in assets if a.id == t.target_asset_id), (0, 0)),
                'specs': t.specs,
                'phase_events': {},
                'flight_time': t.flight_time,
                'target_asset_id': t.target_asset_id
            }
            for t in threats
        ]
        engagement_matrix.add_new_threats(batteries, threats_dict)

        # Test optimized only (faster)
        optimizer = OptimizedMIPWrapper(config)

        start = time.time()
        optimizer.create_model(assets, systems, threats, batteries, engagement_matrix)
        result = optimizer.solve(time_limit=60.0)
        elapsed = time.time() - start

        results[num_threats] = {
            'time': elapsed,
            'feasible': result['feasible'],
            'objective': result.get('objective_value', float('inf')),
            'variables': optimizer.performance_metrics['num_variables'],
            'constraints': optimizer.performance_metrics['num_constraints']
        }

        print(f"   Time: {elapsed:.3f}s")
        print(f"   Feasible: {result['feasible']}")
        print(f"   Variables: {results[num_threats]['variables']}")

    # Summary
    print("\n" + "="*80)
    print("📊 SCALABILITY SUMMARY")
    print("="*80)
    print(f"{'Threats':<15} {'Time (s)':<15} {'Variables':<15} {'Feasible':<15}")
    print("-"*80)
    for num_threats, data in results.items():
        print(f"{num_threats:<15} {data['time']:<15.3f} {data['variables']:<15} {data['feasible']!s:<15}")
    print("="*80 + "\n")

    return results


def main():
    """메인 테스트 실행"""

    print("\n" + "🔥"*40)
    print("OPTIMIZED MIP TEST SUITE")
    print("🔥"*80 + "\n")

    # Test 1: Basic functionality
    success1 = test_basic_functionality()

    if not success1:
        print("❌ Basic functionality test failed!")
        return

    # Test 2: Performance comparison
    print("\n" + "🔁"*40 + "\n")
    results2 = test_performance_comparison()

    # Test 3: Scalability
    print("\n" + "📈"*40 + "\n")
    results3 = test_scalability()

    print("\n" + "✅"*40)
    print("ALL TESTS COMPLETE!")
    print("✅"*80 + "\n")


if __name__ == "__main__":
    main()
