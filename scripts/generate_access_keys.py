#!/usr/bin/env python3
"""
Generate random access keys for professional registration.

Usage:
    python scripts/generate_access_keys.py
    python scripts/generate_access_keys.py --count 10
    python scripts/generate_access_keys.py --length 12
"""

import secrets
import string
import argparse
from datetime import datetime, timedelta


def generate_key(length=8):
    """
    Generate a secure random access key.

    Args:
        length: Length of the key (default: 8)

    Returns:
        Random alphanumeric key in uppercase
    """
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_keys_config(count=5, length=8, expires_days=None):
    """
    Generate access keys in config format.

    Args:
        count: Number of keys to generate
        length: Length of each key
        expires_days: Optional expiration in days

    Returns:
        Dictionary ready to paste in config.py
    """
    keys = {}

    for i in range(count):
        key = generate_key(length)

        key_data = {
            "used": False,
            "created_by": "admin",
            "created_at": datetime.now().isoformat()
        }

        if expires_days:
            expiry = datetime.now() + timedelta(days=expires_days)
            key_data["expires"] = expiry.strftime("%Y-%m-%d")
        else:
            key_data["expires"] = None

        keys[key] = key_data

    return keys


def format_keys_for_config(keys):
    """Format keys dictionary for config.py."""
    lines = ["PROFESSIONAL_ACCESS_KEYS = {"]

    for key, data in keys.items():
        expires_str = f'"{data["expires"]}"' if data["expires"] else "None"
        line = f'    "{key}": {{"used": False, "created_by": "{data["created_by"]}", "expires": {expires_str}}},'
        lines.append(line)

    lines.append("}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate access keys for professionals')
    parser.add_argument('--count', type=int, default=5,
                        help='Number of keys to generate (default: 5)')
    parser.add_argument('--length', type=int, default=8,
                        help='Length of each key (default: 8)')
    parser.add_argument('--expires', type=int,
                        help='Expiration in days (optional)')

    args = parser.parse_args()

    print("=" * 60)
    print("  ACCESS KEY GENERATOR")
    print("=" * 60)
    print()
    print(f"Generating {args.count} keys of {args.length} characters...")

    if args.expires:
        print(f"Keys will expire in {args.expires} days")
    else:
        print("Keys will not expire")

    print()

    keys = generate_keys_config(args.count, args.length, args.expires)

    print("─" * 60)
    print("KEYS FOR config.py:")
    print("─" * 60)
    print()
    print(format_keys_for_config(keys))
    print()

    print("─" * 60)
    print("INDIVIDUAL KEYS (for distribution):")
    print("─" * 60)
    print()

    for i, (key, data) in enumerate(keys.items(), 1):
        print(f"{i}. {key}")
        if data["expires"]:
            print(f"   Expires: {data['expires']}")

    print()
    print("=" * 60)
    print("Copy the keys above into src/config/config.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
