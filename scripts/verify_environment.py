#!/usr/bin/env python3
"""
Environment Verification Script
Validates all required tools and configurations are properly installed.
"""

import os
import sys
import subprocess
import shutil
from typing import Tuple, List

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_result(check_name: str, passed: bool, details: str = "") -> None:
    """Print check result with color coding."""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status}  {check_name}")
    if details:
        print(f"       {details}")


def check_command(command: str, min_version: str = None) -> Tuple[bool, str]:
    """
    Check if a command exists and optionally verify version.
    Returns (success, version_info).
    """
    if not shutil.which(command):
        return False, f"{command} not found in PATH"
    
    try:
        # Try to get version
        result = subprocess.run(
            [command, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_output = result.stdout + result.stderr
        first_line = version_output.split('\n')[0] if version_output else "Unknown version"
        return True, first_line
    except Exception as e:
        return True, f"Found but couldn't get version: {str(e)}"


def check_python_version() -> Tuple[bool, str]:
    """Check Python version is 3.12 or higher."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major == 3 and version.minor >= 12:
        return True, f"Python {version_str}"
    else:
        return False, f"Python {version_str} (requires 3.12+)"


def check_java_version() -> Tuple[bool, str]:
    """Check Java version is 11 or higher (required for Synthea)."""
    try:
        result = subprocess.run(
            ['java', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_output = result.stderr + result.stdout
        
        # Parse version from output
        if 'version' in version_output.lower():
            # Extract version number
            import re
            match = re.search(r'version "?(\d+)\.?(\d+)?\.?(\d+)?', version_output)
            if match:
                major = int(match.group(1))
                version_str = version_output.split('\n')[0]
                
                if major >= 11:
                    return True, version_str
                else:
                    return False, f"{version_str} (requires Java 11+)"
        
        return True, version_output.split('\n')[0] if version_output else "Unknown"
    except FileNotFoundError:
        return False, "Java not found (required for Synthea)"
    except Exception as e:
        return False, f"Error checking Java: {str(e)}"


def check_docker() -> Tuple[bool, str]:
    """Check Docker is installed and daemon is running."""
    if not shutil.which('docker'):
        return False, "Docker not found in PATH"
    
    try:
        # Check Docker daemon is running
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Get Docker version
            version_result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return True, version_result.stdout.strip()
        else:
            return False, "Docker daemon not running"
    except subprocess.TimeoutExpired:
        return False, "Docker daemon timeout - may not be running"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_docker_compose() -> Tuple[bool, str]:
    """Check Docker Compose is available."""
    # Try docker compose (v2)
    try:
        result = subprocess.run(
            ['docker', 'compose', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except:
        pass
    
    # Try docker-compose (v1)
    try:
        result = subprocess.run(
            ['docker-compose', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except:
        pass
    
    return False, "Docker Compose not found (try 'docker compose' or 'docker-compose')"


def check_aws_cli() -> Tuple[bool, str]:
    """Check AWS CLI is installed and configured."""
    if not shutil.which('aws'):
        return False, "AWS CLI not found"
    
    try:
        # Check version
        result = subprocess.run(
            ['aws', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_info = result.stdout.strip()
        
        # Check if configured
        config_result = subprocess.run(
            ['aws', 'sts', 'get-caller-identity'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if config_result.returncode == 0:
            return True, f"{version_info} (configured)"
        else:
            return True, f"{version_info} (NOT configured - run 'aws configure')"
    except Exception as e:
        return True, f"Found but error checking config: {str(e)}"


def check_git() -> Tuple[bool, str]:
    """Check Git is installed."""
    return check_command('git')


def check_jq() -> Tuple[bool, str]:
    """Check jq (JSON processor) is installed."""
    return check_command('jq')


def check_env_file() -> Tuple[bool, str]:
    """Check if .env file exists."""
    if os.path.exists('.env'):
        # Check if it's not just the example file
        with open('.env', 'r') as f:
            content = f.read()
            if 'your_openai_api_key_here' in content or 'change_this_password' in content:
                return False, ".env exists but contains placeholder values - update with real credentials"
            return True, ".env file configured"
    else:
        if os.path.exists('.env.example'):
            return False, ".env missing - copy from .env.example and configure"
        else:
            return False, ".env and .env.example both missing"


def check_directories() -> Tuple[bool, str]:
    """Check if required directories exist."""
    required_dirs = [
        'data/schemas',
        'data/seeds',
        'data/synthea',
        'data/guidelines',
        'vector_store',
        'config',
        'scripts',
        'tests/integration',
        'tests/unit'
    ]
    
    missing = [d for d in required_dirs if not os.path.exists(d)]
    
    if missing:
        return False, f"Missing directories: {', '.join(missing)}"
    return True, "All required directories present"


def main():
    """Run all environment checks."""
    print_header("PCC Platform Environment Verification")
    
    checks = [
        ("Python 3.12+", check_python_version),
        ("Java 11+ (Synthea)", check_java_version),
        ("Docker", check_docker),
        ("Docker Compose", check_docker_compose),
        ("Git", check_git),
        ("AWS CLI", check_aws_cli),
        ("jq (JSON processor)", check_jq),
        (".env Configuration", check_env_file),
        ("Project Directories", check_directories),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            passed, details = check_func()
            print_result(check_name, passed, details)
            results.append((check_name, passed))
        except Exception as e:
            print_result(check_name, False, f"Error: {str(e)}")
            results.append((check_name, False))
    
    # Summary
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print_header("Summary")
    print(f"Passed: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print(f"\n{GREEN}✓ All checks passed! Environment is ready.{RESET}\n")
        return 0
    else:
        print(f"\n{RED}✗ Some checks failed. Please fix the issues above.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
