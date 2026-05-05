from config_mip import EngagementZoneConfig
from scenario_dwta_balanced import DWTABalancedScenario

scenario = DWTABalancedScenario()
batteries = scenario.create_constrained_batteries()
threats = scenario.create_balanced_threats()

print('Testing T01 (NODONG):')
t01 = [t for t in threats if t['id']=='T01'][0]
print(f'  Launch: {t01["launch_position"]}, Target: A01 at (0,0)')
print(f'  Flight time: {t01["flight_time"]}s')
print(f'  Critical altitude: {t01["phase_events"]["critical_altitude_km"]}km')

lsam01 = [b for b in batteries if b['id']=='LSAM_01'][0]
print(f'  LSAM_01 position: {lsam01["position"]}')

result = EngagementZoneConfig.can_engage_trajectory(lsam01, t01)
print(f'  LSAM_01 can engage: {result["can_engage"]}')
print(f'  Engagement windows: {len(result["engagement_windows"])}')

if result['engagement_windows']:
    print('  First 5 windows:')
    for w in result['engagement_windows'][:5]:
        print(f'    T={w["time"]}s: alt={w["altitude"]:.1f}km, dist={w["distance"]:.1f}km')
else:
    print('  No engagement windows found!')
    print('  Checking trajectory points:')
    for t in range(0, int(t01["flight_time"]), 50):
        point = EngagementZoneConfig.calculate_trajectory_intercept_point(t01, t)
        if point:
            import math
            dist = math.sqrt((lsam01["position"][0] - point["position"][0])**2 + 
                           (lsam01["position"][1] - point["position"][1])**2)
            print(f'    T={t}s: alt={point["altitude_km"]:.1f}km, dist={dist:.1f}km')
