#!/usr/bin/env python3
"""
Simple injection script - run this while GoLive Studio is open
"""

import sys
import subprocess
import time

def inject_fix():
    """Inject the runtime fix into the running application"""
    
    print("💉 INJECTING EFFECT REMOVAL FIX")
    print("=" * 40)
    
    try:
        # Import the runtime fixer
        from runtime_effect_fix import RuntimeEffectFixer
        
        # Create and install the fixer
        fixer = RuntimeEffectFixer()
        
        if fixer.install_fix():
            print("\\n🎉 SUCCESS! Effect removal fix is now active!")
            print("\\n📋 TEST IT:")
            print("1. Single-click an effect → Should apply normally")
            print("2. Double-click the same effect → Should remove it completely!")
            print("3. If stuck, press Ctrl+Delete to clear manually")
            
            return True
        else:
            print("\\n❌ Fix injection failed")
            return False
            
    except Exception as e:
        print(f"❌ Injection error: {e}")
        return False

if __name__ == "__main__":
    print("🎯 GoLive Studio Effect Fix Injector")
    print("\\nMAKE SURE GOLIVE STUDIO IS RUNNING FIRST!")
    print("\\nPress Enter to inject the fix...")
    input()
    
    if inject_fix():
        print("\\n✅ Fix injected successfully!")
        print("The fix is now active in your running GoLive Studio.")
        print("\\nYou can close this window - the fix will remain active.")
    else:
        print("\\n❌ Injection failed!")
        print("Make sure GoLive Studio is running and try again.")
    
    print("\\nPress Enter to exit...")
    input()