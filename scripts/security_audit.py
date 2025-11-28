#!/usr/bin/env python3
"""
Security audit script using OWASP ZAP
Run with: python security_audit.py
"""

import subprocess
import os

def run_zap_scan():
    """Run OWASP ZAP security scan"""
    # Assuming ZAP is installed
    zap_path = "C:\\Program Files\\OWASP\\Zed Attack Proxy\\zap.bat"  # Windows path
    target_url = "http://localhost:5000"
    
    cmd = [
        zap_path, "-cmd", "-autorun", f"{os.getcwd()}\\zap_script.zst",
        "-quickurl", target_url, "-quickout", f"{os.getcwd()}\\zap_report.html"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("ZAP scan completed. Report saved to zap_report.html")
    except subprocess.CalledProcessError as e:
        print(f"ZAP scan failed: {e}")

if __name__ == "__main__":
    run_zap_scan()