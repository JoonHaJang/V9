"""
전역 예외 처리를 추가하여 프로그램 크래시 원인을 추적
"""
import sys
import traceback

def exception_hook(exctype, value, tb):
    """전역 예외 핸들러 - 모든 에러를 캡처"""
    print("\n" + "="*80)
    print("FATAL ERROR DETECTED")
    print("="*80)
    print(f"Exception Type: {exctype.__name__}")
    print(f"Exception Value: {value}")
    print("\nFull Traceback:")
    print("-"*80)
    traceback.print_exception(exctype, value, tb)
    print("="*80 + "\n")
    
    # 에러 로그 파일로도 저장
    with open('crash_log.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("CRASH LOG\n")
        f.write("="*80 + "\n")
        f.write(f"Exception Type: {exctype.__name__}\n")
        f.write(f"Exception Value: {value}\n\n")
        f.write("Full Traceback:\n")
        f.write("-"*80 + "\n")
        traceback.print_exception(exctype, value, tb, file=f)
        f.write("="*80 + "\n")
    
    print("Crash log saved to: crash_log.txt")
    
    # 원래 예외 핸들러 호출
    sys.__excepthook__(exctype, value, tb)

# 전역 예외 핸들러 설정
sys.excepthook = exception_hook

print("="*80)
print("Starting DWTA Simulator with Exception Tracking")
print("="*80)
print("If the program crashes, check crash_log.txt for details")
print("="*80 + "\n")

# 메인 프로그램 실행
try:
    import multi_missile_tracker_gui
except Exception as e:
    print("\n" + "="*80)
    print("ERROR during import:")
    print("="*80)
    traceback.print_exc()
    print("="*80)
    sys.exit(1)
