import sys
import traceback

try:
    # GUI 실행
    import multi_missile_tracker_gui
    
except Exception as e:
    print("\n" + "="*80)
    print("FATAL ERROR:")
    print("="*80)
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    print("\nFull Traceback:")
    traceback.print_exc()
    print("="*80)
    sys.exit(1)
