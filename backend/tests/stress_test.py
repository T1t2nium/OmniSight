#!/usr/bin/env python3
"""Manual 30-minute stress test for OmniSight WebSocket server.

Spawns multiple concurrent WS clients, sends continuous audio/video messages,
and tracks disconnections, errors, and latency.

Usage:
    cd backend
    uv run python tests/stress_test.py [--duration 1800] [--clients 5] [--url ws://localhost:8000/ws]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field

import httpx


@dataclass
class ClientStats:
    session_id: str
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    disconnects: int = 0
    max_latency_ms: float = 0.0
    start_time: float = 0.0

    @property
    def run_time_s(self) -> float:
        return time.time() - self.start_time

    @property
    def throughput_s(self) -> float:
        """Messages per second."""
        return self.messages_sent / max(self.run_time_s, 0.1)


async def client_loop(
    url: str,
    stats: ClientStats,
    stop_event: asyncio.Event,
    reconnect: bool = True,
) -> None:
    """Single client that sends frames and reads echoes until stopped."""
    stats.start_time = time.time()

    while not stop_event.is_set():
        try:
            async with httpx.AsyncClient() as http_client:
                async with http_client.ws_connect(url) as ws:
                    # Register
                    await ws.send_json({
                        "type": "vad_event",
                        "session_id": stats.session_id,
                        "timestamp": time.time(),
                        "payload": {"event": "speech_start"},
                    })
                    # Read server_status
                    await asyncio.wait_for(ws.receive_json(), timeout=5)

                    # Send frames in a loop until stopped
                    while not stop_event.is_set():
                        # Send a video_frame periodically
                        await ws.send_json({
                            "type": "video_frame",
                            "session_id": stats.session_id,
                            "timestamp": time.time(),
                            "payload": {
                                "data": "dummy",
                                "width": 640,
                                "height": 480,
                            },
                        })
                        stats.messages_sent += 1

                        # Read a response (non-blocking with short timeout)
                        try:
                            msg = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
                            stats.messages_received += 1
                            # Track latency
                            if msg.get("timestamp"):
                                rtt = (time.time() - msg["timestamp"]) * 1000
                                if rtt > stats.max_latency_ms:
                                    stats.max_latency_ms = rtt
                        except asyncio.TimeoutError:
                            pass

                        await asyncio.sleep(0.25)  # 4 messages/sec

        except Exception as exc:
            stats.errors += 1
            stats.disconnects += 1
            print(f"  [{stats.session_id[:8]}] Error: {type(exc).__name__}: {exc}")
            if reconnect:
                await asyncio.sleep(2)
            else:
                break


async def run_stress_test(url: str, num_clients: int, duration: float) -> list[ClientStats]:
    """Orchestrate all clients concurrently."""
    stop_event = asyncio.Event()
    all_stats: list[ClientStats] = []

    for i in range(num_clients):
        stats = ClientStats(session_id=f"stress-{i}-{uuid.uuid4().hex[:6]}")
        all_stats.append(stats)

    tasks = [
        asyncio.create_task(client_loop(url, stats, stop_event))
        for stats in all_stats
    ]

    print(f"Running {num_clients} clients for {duration}s...")
    print(f"Target: {url}")
    print()

    start = time.time()
    last_report = start

    # Print periodic stats
    while time.time() - start < duration:
        await asyncio.sleep(10)
        elapsed = time.time() - start
        total_sent = sum(s.messages_sent for s in all_stats)
        total_recv = sum(s.messages_received for s in all_stats)
        total_errs = sum(s.errors for s in all_stats)
        print(
            f"  [{elapsed:6.0f}s] "
            f"sent={total_sent:5d} recv={total_recv:5d} "
            f"errs={total_errs:3d}"
        )

    # Stop all clients
    stop_event.set()
    await asyncio.gather(*tasks, return_exceptions=True)

    return all_stats


def print_summary(all_stats: list[ClientStats], duration: float) -> None:
    """Print final results."""
    total_sent = sum(s.messages_sent for s in all_stats)
    total_recv = sum(s.messages_received for s in all_stats)
    total_errs = sum(s.errors for s in all_stats)
    total_disconnects = sum(s.disconnects for s in all_stats)

    print()
    print("=" * 50)
    print("           STRESS TEST RESULTS")
    print("=" * 50)
    print(f"  Clients:           {len(all_stats)}")
    print(f"  Duration:          {duration:.0f}s")
    print(f"  Total sent:        {total_sent}")
    print(f"  Total received:    {total_recv}")
    print(f"  Total errors:      {total_errs}")
    print(f"  Total disconnects: {total_disconnects}")
    print(f"  Max latency:       {max(s.max_latency_ms for s in all_stats):.0f}ms")
    print(f"  Throughput:        {total_sent / duration:.1f} msg/s")

    if total_errs > 0:
        print()
        print("  ⚠ WARNING: Errors detected!")
    else:
        print()
        print("  ✅ No errors detected.")

    if total_disconnects > len(all_stats):
        print("  ⚠ WARNING: Unexpected disconnects!")
    else:
        print("  ✅ Disconnect count within expected range.")


def main():
    parser = argparse.ArgumentParser(description="OmniSight stress test")
    parser.add_argument("--duration", type=float, default=30.0,
                        help="Test duration in seconds (default: 30)")
    parser.add_argument("--clients", type=int, default=3,
                        help="Number of concurrent clients (default: 3)")
    parser.add_argument("--url", type=str, default="ws://localhost:8000/ws",
                        help="WebSocket URL (default: ws://localhost:8000/ws)")
    parser.add_argument("--full", action="store_true",
                        help="Run full 30-minute test (overrides --duration)")
    args = parser.parse_args()

    duration = 1800.0 if args.full else args.duration

    print("OmniSight WebSocket Stress Test")
    print(f"Duration: {duration}s | Clients: {args.clients}")
    print()

    all_stats = asyncio.run(run_stress_test(args.url, args.clients, duration))
    print_summary(all_stats, duration)


if __name__ == "__main__":
    main()
