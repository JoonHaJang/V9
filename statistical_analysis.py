"""
통계적 분석 모듈
=================
알고리즘 간 성능 비교를 위한 통계적 유의성 검증
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

class StatisticalAnalyzer:
    """DWTA 알고리즘 성능 통계 분석"""
    
    def __init__(self):
        self.results = {}
        
    def load_results(self, csv_file: str) -> pd.DataFrame:
        """CSV 파일에서 결과 로드"""
        return pd.read_csv(csv_file)
    
    def compare_algorithms(self, results_df: pd.DataFrame, metric: str = 'intercept_rate') -> Dict:
        """알고리즘 간 통계적 비교"""
        algorithms = results_df['algorithm'].unique()
        
        if len(algorithms) < 2:
            print("비교할 알고리즘이 2개 미만입니다.")
            return None
        
        # 각 알고리즘별 데이터 추출
        data_by_algo = {}
        for algo in algorithms:
            data_by_algo[algo] = results_df[results_df['algorithm'] == algo][metric].values
        
        # 쌍별 t-검정
        pairwise_tests = {}
        for i, algo1 in enumerate(algorithms):
            for algo2 in algorithms[i+1:]:
                t_stat, p_value = stats.ttest_ind(data_by_algo[algo1], data_by_algo[algo2])
                pairwise_tests[f"{algo1}_vs_{algo2}"] = {
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'significant': p_value < 0.05,
                    'effect_size': self._cohen_d(data_by_algo[algo1], data_by_algo[algo2])
                }
        
        # ANOVA (3개 이상 알고리즘)
        if len(algorithms) >= 3:
            f_stat, p_value_anova = stats.f_oneway(*[data_by_algo[algo] for algo in algorithms])
            anova_result = {
                'f_statistic': f_stat,
                'p_value': p_value_anova,
                'significant': p_value_anova < 0.05
            }
        else:
            anova_result = None
        
        # 기술 통계
        descriptive_stats = {}
        for algo in algorithms:
            data = data_by_algo[algo]
            descriptive_stats[algo] = {
                'mean': np.mean(data),
                'std': np.std(data),
                'min': np.min(data),
                'max': np.max(data),
                'median': np.median(data),
                'n': len(data)
            }
        
        return {
            'metric': metric,
            'pairwise_tests': pairwise_tests,
            'anova': anova_result,
            'descriptive_stats': descriptive_stats
        }
    
    def _cohen_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """Cohen's d 효과 크기 계산"""
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
        return (np.mean(group1) - np.mean(group2)) / pooled_std
    
    def analyze_scalability(self, results_df: pd.DataFrame) -> Dict:
        """확장성 분석 (시나리오 크기별 성능)"""
        # 시나리오별 위협 수 매핑
        scenario_sizes = {
            'SMALL_3': 3, 'SMALL_5': 5, 'SMALL_8': 8,
            'MEDIUM_10': 10, 'BASELINE_15': 15, 'MEDIUM_20': 20,
            'LARGE_30': 30, 'LARGE_40': 40
        }
        
        results_df['threat_count'] = results_df['scenario'].map(scenario_sizes)
        
        scalability_results = {}
        for algo in results_df['algorithm'].unique():
            algo_data = results_df[results_df['algorithm'] == algo]
            
            # 위협 수와 계산 시간 간 상관관계
            if len(algo_data) > 2:
                corr_time, p_time = stats.pearsonr(
                    algo_data['threat_count'].dropna(), 
                    algo_data['avg_solve_time'].dropna()
                )
                
                # 위협 수와 요격률 간 상관관계
                corr_rate, p_rate = stats.pearsonr(
                    algo_data['threat_count'].dropna(),
                    algo_data['intercept_rate'].dropna()
                )
                
                scalability_results[algo] = {
                    'time_correlation': corr_time,
                    'time_p_value': p_time,
                    'rate_correlation': corr_rate,
                    'rate_p_value': p_rate,
                    'time_complexity': 'O(n)' if corr_time > 0.9 else 'O(n log n)' if corr_time > 0.7 else 'O(n²)'
                }
        
        return scalability_results
    
    def generate_report(self, results_df: pd.DataFrame, output_file: str = None) -> str:
        """종합 통계 분석 보고서 생성"""
        report = []
        report.append("=" * 80)
        report.append("DWTA 알고리즘 통계 분석 보고서")
        report.append("=" * 80)
        report.append("")
        
        # 1. 요격률 비교
        report.append("1. 요격률 (Intercept Rate) 비교")
        report.append("-" * 80)
        intercept_analysis = self.compare_algorithms(results_df, 'intercept_rate')
        
        if intercept_analysis:
            # 기술 통계
            for algo, stats_dict in intercept_analysis['descriptive_stats'].items():
                report.append(f"\n{algo}:")
                report.append(f"  평균: {stats_dict['mean']:.2f}% ± {stats_dict['std']:.2f}%")
                report.append(f"  범위: [{stats_dict['min']:.2f}%, {stats_dict['max']:.2f}%]")
                report.append(f"  중앙값: {stats_dict['median']:.2f}%")
                report.append(f"  샘플 수: {stats_dict['n']}")
            
            # 쌍별 검정
            report.append("\n쌍별 t-검정 결과:")
            for pair, test_result in intercept_analysis['pairwise_tests'].items():
                sig_mark = "***" if test_result['significant'] else "n.s."
                report.append(f"  {pair}: t={test_result['t_statistic']:.3f}, "
                            f"p={test_result['p_value']:.4f} {sig_mark}, "
                            f"Cohen's d={test_result['effect_size']:.3f}")
            
            # ANOVA
            if intercept_analysis['anova']:
                anova = intercept_analysis['anova']
                sig_mark = "***" if anova['significant'] else "n.s."
                report.append(f"\nANOVA: F={anova['f_statistic']:.3f}, "
                            f"p={anova['p_value']:.4f} {sig_mark}")
        
        # 2. 계산 시간 비교
        report.append("\n\n2. 계산 시간 (Solve Time) 비교")
        report.append("-" * 80)
        time_analysis = self.compare_algorithms(results_df, 'avg_solve_time')
        
        if time_analysis:
            for algo, stats_dict in time_analysis['descriptive_stats'].items():
                report.append(f"\n{algo}:")
                report.append(f"  평균: {stats_dict['mean']:.4f}s ± {stats_dict['std']:.4f}s")
                report.append(f"  범위: [{stats_dict['min']:.4f}s, {stats_dict['max']:.4f}s]")
        
        # 3. 확장성 분석
        report.append("\n\n3. 확장성 (Scalability) 분석")
        report.append("-" * 80)
        scalability = self.analyze_scalability(results_df)
        
        for algo, scale_result in scalability.items():
            report.append(f"\n{algo}:")
            report.append(f"  시간 복잡도: {scale_result['time_complexity']}")
            report.append(f"  시간-크기 상관계수: {scale_result['time_correlation']:.3f} "
                        f"(p={scale_result['time_p_value']:.4f})")
            report.append(f"  요격률-크기 상관계수: {scale_result['rate_correlation']:.3f} "
                        f"(p={scale_result['rate_p_value']:.4f})")
        
        # 4. 종합 평가
        report.append("\n\n4. 종합 평가")
        report.append("-" * 80)
        
        # 최고 성능 알고리즘 식별
        avg_intercept = results_df.groupby('algorithm')['intercept_rate'].mean()
        avg_time = results_df.groupby('algorithm')['avg_solve_time'].mean()
        
        best_accuracy = avg_intercept.idxmax()
        best_speed = avg_time.idxmin()
        
        report.append(f"\n최고 요격률: {best_accuracy} ({avg_intercept[best_accuracy]:.2f}%)")
        report.append(f"최고 속도: {best_speed} ({avg_time[best_speed]:.4f}s)")
        
        # Pareto 효율성
        report.append("\nPareto 효율성 분석:")
        for algo in results_df['algorithm'].unique():
            intercept = avg_intercept[algo]
            time = avg_time[algo]
            
            # 다른 알고리즘과 비교
            dominated = False
            for other_algo in results_df['algorithm'].unique():
                if other_algo != algo:
                    if (avg_intercept[other_algo] >= intercept and 
                        avg_time[other_algo] <= time and
                        (avg_intercept[other_algo] > intercept or avg_time[other_algo] < time)):
                        dominated = True
                        break
            
            status = "지배됨" if dominated else "Pareto 최적"
            report.append(f"  {algo}: {status}")
        
        report.append("\n" + "=" * 80)
        
        # 보고서 저장
        report_text = "\n".join(report)
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"보고서 저장: {output_file}")
        
        return report_text
    
    def plot_comparison(self, results_df: pd.DataFrame, save_path: str = None):
        """비교 시각화"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 요격률 박스플롯
        sns.boxplot(data=results_df, x='algorithm', y='intercept_rate', ax=axes[0, 0])
        axes[0, 0].set_title('Intercept Rate by Algorithm', fontweight='bold')
        axes[0, 0].set_ylabel('Intercept Rate (%)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 계산 시간 박스플롯
        sns.boxplot(data=results_df, x='algorithm', y='avg_solve_time', ax=axes[0, 1])
        axes[0, 1].set_title('Solve Time by Algorithm', fontweight='bold')
        axes[0, 1].set_ylabel('Average Solve Time (s)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 확장성 (시나리오 크기별)
        scenario_sizes = {
            'SMALL_3': 3, 'SMALL_5': 5, 'SMALL_8': 8,
            'MEDIUM_10': 10, 'BASELINE_15': 15, 'MEDIUM_20': 20,
            'LARGE_30': 30, 'LARGE_40': 40
        }
        results_df['threat_count'] = results_df['scenario'].map(scenario_sizes)
        
        for algo in results_df['algorithm'].unique():
            algo_data = results_df[results_df['algorithm'] == algo]
            axes[1, 0].plot(algo_data['threat_count'], algo_data['avg_solve_time'], 
                          'o-', label=algo, markersize=6)
        
        axes[1, 0].set_title('Scalability: Solve Time vs Problem Size', fontweight='bold')
        axes[1, 0].set_xlabel('Number of Threats')
        axes[1, 0].set_ylabel('Average Solve Time (s)')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Pareto Front (요격률 vs 시간)
        for algo in results_df['algorithm'].unique():
            algo_data = results_df[results_df['algorithm'] == algo]
            axes[1, 1].scatter(algo_data['avg_solve_time'], algo_data['intercept_rate'],
                             label=algo, s=100, alpha=0.7)
        
        axes[1, 1].set_title('Pareto Front: Accuracy vs Speed', fontweight='bold')
        axes[1, 1].set_xlabel('Average Solve Time (s)')
        axes[1, 1].set_ylabel('Intercept Rate (%)')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"그래프 저장: {save_path}")
        
        plt.show()


def analyze_comparison_results(csv_file: str, output_dir: str = 'performance_results'):
    """비교 실험 결과 분석 메인 함수"""
    import os
    
    analyzer = StatisticalAnalyzer()
    
    # 결과 로드
    print(f"결과 로드 중: {csv_file}")
    results_df = analyzer.load_results(csv_file)
    
    print(f"총 {len(results_df)}개 실험 결과 로드")
    print(f"알고리즘: {results_df['algorithm'].unique()}")
    print(f"시나리오: {results_df['scenario'].unique()}")
    
    # 통계 분석
    report = analyzer.generate_report(
        results_df, 
        output_file=os.path.join(output_dir, 'statistical_analysis_report.txt')
    )
    
    print("\n" + report)
    
    # 시각화
    analyzer.plot_comparison(
        results_df,
        save_path=os.path.join(output_dir, 'comparison_plots.png')
    )
    
    return analyzer


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # 가장 최근 비교 결과 파일 찾기
        import glob
        files = glob.glob('performance_results/comparison_*.csv')
        if files:
            csv_file = max(files, key=lambda x: x.split('_')[-1])
            print(f"최근 결과 파일 사용: {csv_file}")
        else:
            print("분석할 CSV 파일을 찾을 수 없습니다.")
            print("사용법: python statistical_analysis.py <csv_file>")
            sys.exit(1)
    
    analyze_comparison_results(csv_file)
