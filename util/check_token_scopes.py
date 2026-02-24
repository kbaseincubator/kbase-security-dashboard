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
    scopes = response.headers.get('X-OAuth-Scopes', 'none')
    print(f"Token scopes: {scopes}")

    if 'read:packages' in scopes:
        print("✓ Has read:packages scope")
    else:
        print("✗ Missing read:packages scope - this is likely your issue!")
else:
    print(f"✗ Token check failed: {response.status_code}")
    print(response.text)
