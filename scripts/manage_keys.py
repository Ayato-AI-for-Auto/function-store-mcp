"""
CLI tool for managing API keys
"""
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from solo_mcp.auth import generate_api_key, revoke_api_key, verify_api_key
import duckdb

def list_keys():
    """List all API keys."""
    from solo_mcp.auth import API_KEYS_DB
    conn = duckdb.connect(str(API_KEYS_DB))
    try:
        results = conn.execute("""
            SELECT key_hash, user_id, created_at, last_used, is_active
            FROM api_keys
            ORDER BY created_at DESC
        """).fetchall()
        
        print("\n=== API Keys ===")
        for r in results:
            status = "ACTIVE" if r[4] else "REVOKED"
            print(f"\nKey: fsk_{r[0][:32]}...")
            print(f"  User: {r[1]}")
            print(f"  Created: {r[2]}")
            print(f"  Last Used: {r[3] or 'Never'}")
            print(f"  Status: {status}")
    finally:
        conn.close()

def create_key(user_id: str):
    """Create a new API key."""
    key = generate_api_key(user_id)
    print(f"\n=== New API Key Created ===")
    print(f"User ID: {user_id}")
    print(f"API Key: {key}")
    print(f"\nIMPORTANT: Save this key securely. It cannot be retrieved later.")
    print(f"\nUsage:")
    print(f'  curl -H "X-API-Key: {key}" http://localhost:8000/functions/search')

def revoke_key(api_key: str):
    """Revoke an API key."""
    success = revoke_api_key(api_key)
    if success:
        print(f"\nAPI key revoked successfully: {api_key[:16]}...")
    else:
        print(f"\nFailed to revoke key: {api_key[:16]}...")

def verify_key(api_key: str):
    """Verify an API key."""
    is_valid, user_id = verify_api_key(api_key)
    if is_valid:
        print(f"\nKey is VALID")
        print(f"User ID: {user_id}")
    else:
        print(f"\nKey is INVALID or REVOKED")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Manage Function Store API keys")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List command
    subparsers.add_parser("list", help="List all API keys")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("user_id", help="User ID for the new key")
    
    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key")
    revoke_parser.add_argument("api_key", help="API key to revoke")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify an API key")
    verify_parser.add_argument("api_key", help="API key to verify")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_keys()
    elif args.command == "create":
        create_key(args.user_id)
    elif args.command == "revoke":
        revoke_key(args.api_key)
    elif args.command == "verify":
        verify_key(args.api_key)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
