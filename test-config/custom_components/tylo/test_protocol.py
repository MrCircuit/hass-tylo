#!/usr/bin/env python3
"""Test script for Tylö protocol without hardware."""
import asyncio
import logging
from protocol import TyloProtocol

logging.basicConfig(level=logging.DEBUG)

class MockSerial:
    """Mock serial interface for testing."""
    
    def __init__(self):
        self.is_open = True
        
    def read(self, size=1):
        # Return empty bytes to simulate no data
        return b''
        
    def write(self, data):
        print(f"Mock serial write: {data.hex()}")
        return len(data)
        
    def close(self):
        self.is_open = False

async def test_protocol():
    """Test the protocol with mock serial."""
    print("Testing Tylö protocol with mock serial interface...")
    
    # Create protocol with mock serial
    protocol = TyloProtocol()
    protocol.serial = MockSerial()
    
    # Test basic functionality
    print("Protocol initialized successfully")
    print(f"Current state: {protocol.state}")
    
    # Test command sending
    await protocol.send_command(0x3400, b'\x01')  # Test heater on
    
    protocol.close()
    print("Test completed successfully")

if __name__ == "__main__":
    asyncio.run(test_protocol())