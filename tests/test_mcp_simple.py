"""
Simple test script for MCP backend - tests text-only expense.

This script tests the MCP client without FastAPI to isolate any issues.
"""

import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.abspath('.'))

from backend.mcp.client import ExpenseMCPClient


async def test_simple_expense():
    """Test processing a simple text-only expense."""
    print("=" * 60)
    print("Testing MCP Backend - Text-Only Expense")
    print("=" * 60)

    # Initialize client
    client = ExpenseMCPClient()

    try:
        # Start MCP client
        print("\n1️⃣  Starting MCP client...")
        await client.startup()

        # Test simple expense
        print("\n2️⃣  Processing: 'Starbucks coffee $5'")
        result = await client.process_expense_message(
            text="Starbucks coffee $5",
            image_base64=None
        )

        # Display results
        print("\n3️⃣  Results:")
        print(f"   Success: {result.get('success')}")
        print(f"   Expense ID: {result.get('expense_id')}")
        print(f"   Expense Name: {result.get('expense_name')}")
        print(f"   Amount: ${result.get('amount')}")
        print(f"   Category: {result.get('category')}")
        print(f"   Budget Warning: {result.get('budget_warning')}")
        print(f"\n   Message:\n   {result.get('message')}")

        # Verify
        print("\n4️⃣  Verification:")
        if result.get('success'):
            print("   ✅ Expense saved successfully!")
        else:
            print("   ❌ Failed to save expense")

        if result.get('expense_id'):
            print(f"   ✅ Got expense ID: {result['expense_id']}")
        else:
            print("   ❌ No expense ID returned")

        if result.get('category') == 'COFFEE':
            print("   ✅ Correct category (COFFEE)")
        else:
            print(f"   ⚠️  Unexpected category: {result.get('category')}")

        print("\n" + "=" * 60)
        print("Test Complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(test_simple_expense())
