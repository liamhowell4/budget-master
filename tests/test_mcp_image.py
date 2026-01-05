"""
Test script for MCP backend - tests receipt image processing with Claude Vision.
"""

import asyncio
import sys
import os
import base64

# Add paths
sys.path.insert(0, os.path.abspath('.'))

from backend.mcp.client import ExpenseMCPClient


async def test_image_parsing():
    """Test processing a receipt image with Claude Vision."""
    print("=" * 60)
    print("Testing MCP Backend - Receipt Image Parsing")
    print("=" * 60)

    # Image path (relative to tests/ directory)
    image_path = "fixtures/images/B6223AEE-8E18-4D6D-9165-077C559FC1E9_1_105_c.jpeg"

    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return

    print(f"\n📸 Loading image: {image_path}")

    # Read and encode image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    # Convert to base64 with data URL prefix
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    image_base64 = f"data:image/jpeg;base64,{image_base64}"

    print(f"   Image size: {len(image_bytes)} bytes")
    print(f"   Base64 size: {len(image_base64)} chars")

    # Initialize client
    client = ExpenseMCPClient()

    try:
        # Start MCP client
        print("\n1️⃣  Starting MCP client...")
        await client.startup()

        # Test image with optional text
        print("\n2️⃣  Processing receipt image...")
        result = await client.process_expense_message(
            text="Receipt from today",  # Optional context
            image_base64=image_base64
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

        if result.get('amount') and result.get('amount') > 0:
            print(f"   ✅ Extracted amount: ${result['amount']}")
        else:
            print("   ⚠️  Could not extract amount from receipt")

        if result.get('expense_name'):
            print(f"   ✅ Generated expense name: {result['expense_name']}")
        else:
            print("   ⚠️  No expense name generated")

        print("\n" + "=" * 60)
        print("Image Test Complete!")
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
    asyncio.run(test_image_parsing())
