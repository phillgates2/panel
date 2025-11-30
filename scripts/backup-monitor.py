#!/usr/bin/env python3
"""
Backup Monitoring Script
Monitor backup system health and send alerts
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from panel.backup_monitoring import (check_backup_health, check_storage_health,
                                     generate_health_report,
                                     run_monitoring_checks)


def main():
    if len(sys.argv) < 2:
        print("Usage: python backup-monitor.py <command>")
        print("Commands:")
        print("  check-health    - Check backup system health")
        print("  check-storage   - Check backup storage health")
        print("  report          - Generate health report")
        print("  monitor         - Run monitoring checks and alerts")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "check-health":
            health = check_backup_health()
            print(f"Status: {health['status']}")
            print(f"Total backups: {health['total_backups']}")
            print(f"Success rate: {health['backup_success_rate']*100:.1f}%")
            if health["issues"]:
                print("Issues:")
                for issue in health["issues"]:
                    print(f"  - {issue}")
            if health["recommendations"]:
                print("Recommendations:")
                for rec in health["recommendations"]:
                    print(f"  - {rec}")

        elif command == "check-storage":
            storage = check_storage_health()
            print(f"Status: {storage['status']}")
            print(f"Files: {storage['file_count']}")
            size_gb = storage["total_size_bytes"] / (1024**3)
            print(f"Total size: {size_gb:.2f} GB")
            print(f"Disk usage: {storage['disk_usage_percent']:.1f}%")
            if storage["issues"]:
                print("Issues:")
                for issue in storage["issues"]:
                    print(f"  - {issue}")

        elif command == "report":
            report = generate_health_report()
            print(report)

        elif command == "monitor":
            run_monitoring_checks()
            print("Monitoring checks completed")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
