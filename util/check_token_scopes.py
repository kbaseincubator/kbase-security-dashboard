#!/usr/bin/env python3
"""Check what scopes a GitHub token has"""
import requests
import sys
import getpass

# Read token from stdin (either piped or interactive)
if not sys.stdin.isatty():
    # Piped input: cat token_file | python check_token_scopes.py
    token = sys.stdin.read().strip()
else:
    # Interactive: prompt without echoing
    token = getpass.getpass("Enter GitHub token: ")

if not token:
    print("Error: No token provided")
    sys.exit(1)

response = requests.get(
    "https://api.github.com/user",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 200:
    print(f"✓ Token is valid for user: {response.json()['login']}")
    scopes = response.headers.get('X-OAuth-Scopes', '')
    scope_list = [s.strip() for s in scopes.split(',') if s.strip()]

    required_scopes = ['repo', 'read:packages']
    missing_scopes = [scope for scope in required_scopes if scope not in scope_list]

    if missing_scopes:
        print(f"✗ Missing required scopes: {', '.join(missing_scopes)}")
        sys.exit(1)
    else:
        print("✓ Token has all required scopes")
else:
    print(f"✗ Token check failed: {response.status_code}")
    print(response.text)
