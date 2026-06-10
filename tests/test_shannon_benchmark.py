"""
Tests for Shannon Benchmark Genesis Protocol.
"""

import asyncio
import hashlib
import struct
import pytest
from cortex.shannon.benchmark.genesis import GenesisBenchmark

@pytest.mark.asyncio
async def test_genesis_benchmark_solvable():
    # 1. Start Benchmark
    benchmark = GenesisBenchmark()
    await benchmark.setup()
    
    writer = None
    try:
        # 2. Connect client
        reader, writer = await asyncio.open_connection(benchmark.server.host, benchmark.server.port)
        
        # 3. Read Challenge
        challenge = await reader.readexactly(33)
        nonce = challenge[:32]
        endian_char = challenge[32:33].decode()
        endianness = '>' if endian_char == 'B' else '<'
        
        # 4. Compute response
        nonce_hash = hashlib.sha256(nonce).digest()
        max_payload = 1024
        length_packed = struct.pack(f"{endianness}I", max_payload)
        
        writer.write(nonce_hash + length_packed)
        await writer.drain()
        
        # 5. Read header
        header = await reader.readexactly(4)
        (payload_length,) = struct.unpack(f"{endianness}I", header)
        
        # 6. Read obfuscated payload
        payload = await reader.readexactly(payload_length)
        
        # 7. Brute force XOR mask
        flag = None
        for mask in range(256):
            decoded = bytes([b ^ mask for b in payload])
            if decoded.startswith(b"CORTEX_GENESIS_FLAG_"):
                flag = decoded.decode()
                break
                
        assert flag is not None
        assert flag == benchmark.server.flag.decode()
        
    finally:
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass
        await benchmark.teardown()
