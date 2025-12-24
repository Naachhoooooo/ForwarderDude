import logging
import os
import shutil
import time
import sys

# Ensure we can import app modules
sys.path.append(os.getcwd())

from app.logger import configure_logging, get_logger

def verify_logging():
    print("🧪 Starting Logging Verification...")
    
    # 1. Setup
    # Clear logs dir for clean test (optional, but good for verification)
    if os.path.exists("logs"):
        for f in os.listdir("logs"):
            if f.endswith(".log"):
                try:
                    open(os.path.join("logs", f), 'w').close() # Clear file
                except: pass

    configure_logging()
    
    # 2. Emit logs
    print("📢 Emitting logs to all channels...")
    
    # Bot Logger
    bot_log = get_logger('bot')
    bot_log.info("Test Info Message for Bot")
    
    # System Logger
    sys_log = get_logger('system')
    sys_log.info("Test System Stat: CPU 50%")
    
    # Forwards Logger
    fw_log = get_logger('forwards')
    fw_log.info("Test Forward Message ID: 12345")
    
    # Error Logger (via root or specific)
    err_log = get_logger('errors')
    err_log.error("Test Error Message")
    
    # Root logger warning should go to errors?
    logging.warning("This is a root warning, should go to errors?")
    
    # Allow simple flush
    time.sleep(1)
    
    # 3. Verify files
    results = {}
    
    def check_file(filename, content):
        path = os.path.join("logs", filename)
        if not os.path.exists(path):
            return False, "File not found"
        
        with open(path, 'r') as f:
            data = f.read()
            if content in data:
                return True, "Found"
            else:
                return False, f"Content '{content}' not found in {data[:100]}..."

    results['bot.log'] = check_file('bot.log', "Test Info Message for Bot")
    results['system.log'] = check_file('system.log', "Test System Stat: CPU 50%")
    results['forwards.log'] = check_file('forwards.log', "Test Forward Message ID: 12345")
    results['errors.log'] = check_file('errors.log', "Test Error Message")
    
    # 4. Report
    print("\n📊 Verification Results:")
    all_passed = True
    for log, (passed, msg) in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed: all_passed = False
        print(f"{status} {log}: {msg}")
        
    if all_passed:
        print("\n✅ All logging tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    verify_logging()
