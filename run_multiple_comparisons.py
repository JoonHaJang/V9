"""
Compare 모드를 여러 번 반복 실행하는 스크립트

각 실행은 독립적이며, 결과는 자동으로 CSV 파일로 저장됩니다.
크래시 발생 시 이전 실행 결과는 보존됩니다.

사용법:
    python run_multiple_comparisons.py

설정 변경:
    - scenario: 시나리오 이름 (기본값: DWTA_BALANCED)
    - algorithms: 알고리즘 목록 (기본값: MIP,GA,Greedy)
    - total_iterations: 반복 횟수 (기본값: 5)
"""

import subprocess
import sys
import time
from datetime import datetime
import os
import json

def run_single_comparison(scenario, algorithms, iteration_num, total_iterations):
    """단일 comparison 실행 (--iterations 1)"""
    print(f"\n{'='*80}")
    print(f"Iteration {iteration_num}/{total_iterations}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    cmd = [
        sys.executable,
        "multi_missile_tracker_gui.py",
        "--compare",
        scenario,
        "--iterations", "1",  # 각 실행은 1회만 (안정성)
        algorithms
    ]
    
    start_time = time.time()
    
    # 출력 로그 파일 경로
    log_file = f"performance_results/run_log_{iteration_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        # 파일로 리다이렉션 (capture_output 대신)
        with open(log_file, 'w', encoding='utf-8', errors='replace') as f:
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=f,
                stderr=subprocess.STDOUT,  # stderr도 stdout으로 합침
                timeout=600  # 10분 타임아웃
            )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n[OK] Iteration {iteration_num} completed ({elapsed:.1f}s)")
            print(f"Log saved: {log_file}")
            
            # CSV 파일 찾기
            csv_files = [f for f in os.listdir('performance_results') 
                        if f.startswith('comparison_all_') and f.endswith('.csv')]
            latest_csv = max(csv_files, key=lambda x: os.path.getmtime(os.path.join('performance_results', x))) if csv_files else None
            
            return {
                'iteration': iteration_num,
                'status': 'success',
                'elapsed_time': elapsed,
                'csv_file': latest_csv,
                'log_file': log_file,
                'timestamp': datetime.now().isoformat()
            }
        else:
            print(f"\n[FAILED] Iteration {iteration_num} (exit code: {result.returncode})")
            
            # 로그 파일에서 마지막 에러 읽기
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    log_content = f.read()
                    error_msg = log_content[-1000:] if len(log_content) > 1000 else log_content
                    print(f"Error output (last 500 chars):\n{error_msg[-500:]}")
            except:
                error_msg = "Could not read log file"
            
            return {
                'iteration': iteration_num,
                'status': 'failed',
                'exit_code': result.returncode,
                'elapsed_time': elapsed,
                'error': error_msg,
                'log_file': log_file,
                'timestamp': datetime.now().isoformat()
            }
    
    except subprocess.TimeoutExpired:
        print(f"\n[TIMEOUT] Iteration {iteration_num} exceeded 10 minutes")
        return {
            'iteration': iteration_num,
            'status': 'timeout',
            'elapsed_time': 600,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"\n[CRASHED] Iteration {iteration_num}: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'iteration': iteration_num,
            'status': 'crashed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def main():
    # ========== 설정 (여기를 수정하세요) ==========
    
    # 시나리오 선택 (하나만 선택)
    # ─────────────────────────────────────────────────────────────
    # 확장성 테스트 (Scalability):
    #   "SMALL_3"        - 초소규모 (3발 - 알고리즘 검증)
    #   "SMALL_5"        - 소규모 (5발 - 기본 성능)
    #   "SMALL_8"        - 소중규모 (8발 - 전환점)
    #   "MEDIUM_10"      - 중소규모 (10발 - 일반 공격)
    #   "BASELINE_15"    - 중규모 기본 (15발 - 표준)
    #   "MEDIUM_20"      - 중대규모 (20발 - 균형 공격)
    #   "HEAVY_30"       - 대규모 (30발 - 포화 공격)
    #   "LARGE_40"       - 초대규모 (40발 - 한계 테스트)
    #   "STRESS_100"     - 스트레스 (100발 - 성능 검증)
    #
    # 공격 패턴 테스트:
    #   "SEQUENTIAL_20"  - 순차 공격 (20발 - 순차 발사)
    #   "SIMULTANEOUS_20"- 동시 공격 (20발 - 동시 발사)
    #
    # 표준 벤치마크:
    #   "DWTA_BALANCED"  - 표준 벤치마크 (20발, 6개 배터리) ⭐ 권장
    # ─────────────────────────────────────────────────────────────
    scenario = "STRESS_100"
    
    # 알고리즘 선택 (쉼표로 구분, 여러 개 선택 가능)
    # ─────────────────────────────────────────────────────────────
    # "MIP"     - McCormick MIP (최적성 보장, 실시간 가능)
    # "GA"      - Genetic Algorithm (안정적, 느림)
    # "Greedy"  - Greedy (초고속, 자원 비효율)
    #
    # 예시:
    #   "MIP"              - MIP만 실행
    #   "MIP,GA"           - MIP와 GA 비교
    #   "MIP,GA,Greedy"    - 3개 알고리즘 전체 비교 ⭐ 권장
    # ─────────────────────────────────────────────────────────────
    algorithms = "MIP,GA,Greedy"
    
    # 반복 횟수 (통계적 신뢰성을 위해 최소 5회 이상 권장)
    total_iterations = 10
    
    # ============================================
    
    print("="*80)
    print("MULTIPLE COMPARISON RUNNER")
    print("="*80)
    print(f"Scenario: {scenario}")
    print(f"Algorithms: {algorithms}")
    print(f"Total Iterations: {total_iterations}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # performance_results 디렉토리 확인
    if not os.path.exists('performance_results'):
        os.makedirs('performance_results')
        print("Created 'performance_results' directory")
    
    results = []
    successful = 0
    failed = 0
    csv_files = []
    
    overall_start = time.time()
    
    for i in range(1, total_iterations + 1):
        result = run_single_comparison(scenario, algorithms, i, total_iterations)
        results.append(result)
        
        if result['status'] == 'success':
            successful += 1
            if result.get('csv_file'):
                csv_files.append(result['csv_file'])
        else:
            failed += 1
        
        # 진행 상황 저장 (크래시 대비)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        progress_file = f"performance_results/progress_{timestamp}.json"
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scenario': scenario,
                'algorithms': algorithms,
                'total_iterations': total_iterations,
                'completed': i,
                'successful': successful,
                'failed': failed,
                'csv_files': csv_files,
                'results': results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\nProgress: {i}/{total_iterations} ({successful} success, {failed} failed)")
        print(f"Progress saved: {progress_file}")
        
        # 다음 실행 전 잠시 대기 (시스템 안정화)
        if i < total_iterations:
            print("Waiting 3 seconds before next iteration...")
            time.sleep(3)
    
    overall_elapsed = time.time() - overall_start
    
    # 최종 요약
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"Total Iterations: {total_iterations}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {successful/total_iterations*100:.1f}%")
    print(f"Total Time: {overall_elapsed/60:.1f} minutes")
    print(f"Average Time per Iteration: {overall_elapsed/total_iterations:.1f} seconds")
    print("="*80)
    
    if csv_files:
        print(f"\nGenerated CSV files ({len(csv_files)}):")
        for csv in csv_files:
            print(f"  - {csv}")
    
    print(f"\nAll results saved in: performance_results/")
    print(f"Progress file: {progress_file}")
    
    # 실패한 iteration 상세 정보
    if failed > 0:
        print(f"\n{'='*80}")
        print("FAILED ITERATIONS:")
        print("="*80)
        for r in results:
            if r['status'] != 'success':
                print(f"  Iteration {r['iteration']}: {r['status']}")
                if 'error' in r:
                    print(f"    Error: {r['error'][:200]}")


if __name__ == "__main__":
    main()
