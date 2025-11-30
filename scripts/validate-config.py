#!/usr/bin/env python3
"""
Configuration Validation Script
Validates environment configurations and provides detailed feedback
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from panel.config_manager import ConfigManager, Environment


def validate_environment_config(env_name: str) -> Dict[str, Any]:
    """Validate a specific environment configuration"""
    try:
        manager = ConfigManager()
        errors = manager.validate_config(env_name)
        info = manager.get_environment_info(env_name)

        return {
            'environment': env_name,
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': [],
            'info': info
        }
    except Exception as e:
        return {
            'environment': env_name,
            'valid': False,
            'errors': [f'Configuration error: {str(e)}'],
            'warnings': [],
            'info': {}
        }


def validate_all_environments() -> Dict[str, Any]:
    """Validate all environment configurations"""
    manager = ConfigManager()
    results = {}

    for env_name in manager.list_environments():
        results[env_name] = validate_environment_config(env_name)

    # Cross-environment validation
    cross_env_issues = validate_cross_environment(results)
    for env_name, issues in cross_env_issues.items():
        if env_name in results:
            results[env_name]['warnings'].extend(issues)

    return results


def validate_cross_environment(results: Dict[str, Any]) -> Dict[str, List[str]]:
    """Validate consistency across environments"""
    issues = {}

    # Check that production has stricter security settings
    if 'production' in results and 'development' in results:
        prod_info = results['production']['info']
        dev_info = results['development']['info']

        if prod_info.get('password_min_length', 8) <= dev_info.get('password_min_length', 8):
            issues.setdefault('production', []).append(
                'Production password minimum length should be higher than development'
            )

        if prod_info.get('max_login_attempts', 5) >= dev_info.get('max_login_attempts', 5):
            issues.setdefault('production', []).append(
                'Production should have fewer max login attempts than development'
            )

    # Check that sensitive features are disabled in testing
    if 'testing' in results:
        test_info = results['testing']['info']
        sensitive_features = ['oauth', 'realtime', 'pwa']

        for feature in sensitive_features:
            if test_info.get('features', {}).get(feature, False):
                issues.setdefault('testing', []).append(
                    f'Feature "{feature}" should be disabled in testing environment'
                )

    return issues


def check_environment_variables(env_name: str) -> List[str]:
    """Check for required environment variables"""
    missing_vars = []

    # Environment-specific required variables
    required_vars = {
        'production': ['SECRET_KEY', 'DATABASE_URL'],
        'staging': ['SECRET_KEY', 'DATABASE_URL'],
        'development': ['SECRET_KEY'],
        'testing': []
    }

    for var in required_vars.get(env_name, []):
        if not os.getenv(var):
            missing_vars.append(f'Missing environment variable: {var}')

    return missing_vars


def generate_validation_report(results: Dict[str, Any]) -> str:
    """Generate a detailed validation report"""
    report_lines = []
    report_lines.append("# Configuration Validation Report")
    report_lines.append("=" * 50)
    report_lines.append("")

    total_envs = len(results)
    valid_envs = sum(1 for r in results.values() if r['valid'])
    total_errors = sum(len(r['errors']) for r in results.values())
    total_warnings = sum(len(r['warnings']) for r in results.values())

    report_lines.append(f"## Summary")
    report_lines.append(f"- Environments checked: {total_envs}")
    report_lines.append(f"- Valid configurations: {valid_envs}")
    report_lines.append(f"- Total errors: {total_errors}")
    report_lines.append(f"- Total warnings: {total_warnings}")
    report_lines.append("")

    for env_name, result in results.items():
        status = "? PASS" if result['valid'] else "? FAIL"
        report_lines.append(f"## {env_name.upper()} Environment - {status}")
        report_lines.append("")

        if result['errors']:
            report_lines.append("### Errors:")
            for error in result['errors']:
                report_lines.append(f"- {error}")
            report_lines.append("")

        if result['warnings']:
            report_lines.append("### Warnings:")
            for warning in result['warnings']:
                report_lines.append(f"- {warning}")
            report_lines.append("")

        # Environment info
        info = result['info']
        if info:
            report_lines.append("### Configuration Info:")
            report_lines.append(f"- Features enabled: {info.get('features_enabled', 0)}/{info.get('total_features', 0)}")
            report_lines.append(f"- Database configured: {'Yes' if info.get('has_database') else 'No'}")
            report_lines.append(f"- Redis configured: {'Yes' if info.get('has_redis') else 'No'}")
            report_lines.append(f"- CDN enabled: {'Yes' if info.get('has_cdn') else 'No'}")
            report_lines.append(f"- OAuth configured: {'Yes' if info.get('has_oauth') else 'No'}")
            report_lines.append("")

        # Environment variables check
        missing_vars = check_environment_variables(env_name)
        if missing_vars:
            report_lines.append("### Missing Environment Variables:")
            for var in missing_vars:
                report_lines.append(f"- {var}")
            report_lines.append("")

    # Recommendations
    report_lines.append("## Recommendations")
    report_lines.append("")

    if total_errors > 0:
        report_lines.append("### Critical Issues (Must Fix):")
        report_lines.append("- Address all configuration errors before deployment")
        report_lines.append("- Ensure all required environment variables are set")
        report_lines.append("- Validate database and Redis connections")
        report_lines.append("")

    if total_warnings > 0:
        report_lines.append("### Warnings (Should Review):")
        report_lines.append("- Consider security implications of configuration differences")
        report_lines.append("- Review feature flags for each environment")
        report_lines.append("- Verify OAuth and external service configurations")
        report_lines.append("")

    if total_errors == 0 and total_warnings == 0:
        report_lines.append("? All configurations are valid and ready for deployment!")
        report_lines.append("")
        report_lines.append("Next steps:")
        report_lines.append("- Run `make config-setup ENV=<environment>` to setup your environment")
        report_lines.append("- Copy `.env.example` to `.env` and configure your secrets")
        report_lines.append("- Test your configuration with `python app.py`")

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description='Validate environment configurations')
    parser.add_argument('environment', nargs='?', help='Specific environment to validate')
    parser.add_argument('--output', '-o', help='Output file for validation report')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    if args.environment:
        results = {args.environment: validate_environment_config(args.environment)}
    else:
        results = validate_all_environments()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        report = generate_validation_report(results)
        print(report)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\nReport saved to: {args.output}")

    # Exit with error code if there are validation failures
    total_errors = sum(len(r['errors']) for r in results.values())
    if total_errors > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()