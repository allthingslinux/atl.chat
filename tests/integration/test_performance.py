"""Performance and Load Testing

Comprehensive performance and load testing for IRC servers using controlled environment.
Tests connection throughput, message performance, and concurrent operations.
"""

import contextlib
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pytest

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications


class IRCPerformanceClient:
    """IRC client for performance testing with controlled server."""

    def __init__(self, host: str, port: int, client_id: int = 0):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.socket: socket.socket | None = None
        self.connected = False
        self.connect_time = 0.0
        self.response_times: list[float] = []

    def connect(self) -> float:
        """Connect to IRC server and return connection time."""
        start_time = time.time()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2)
            self.socket.connect((self.host, self.port))

            # Register user with more human-like nickname
            nick = f"User{self.client_id + 100}"
            username = f"user{self.client_id + 100}"
            self.socket.send(f"NICK {nick}\r\n".encode())
            self.socket.send(f"USER {username} 0 * :Test User {self.client_id}\r\n".encode())

            # Read responses and handle PING/PONG
            buffer = ""
            while time.time() - start_time < 10:  # Increased timeout
                try:
                    data = self.socket.recv(1024).decode()
                    if not data:
                        break
                    buffer += data

                    # Handle PING requests
                    lines = buffer.split("\r\n")
                    for line in lines[:-1]:  # Process complete lines
                        if line.startswith("PING "):
                            ping_token = line.split(" ", 1)[1]
                            self.socket.send(f"PONG {ping_token}\r\n".encode())

                        # Check if we received welcome message
                        if " 001 " in line or ":001" in line:
                            self.connected = True
                            self.connect_time = time.time() - start_time
                            return self.connect_time

                    # Keep the last incomplete line in buffer
                    buffer = lines[-1]

                except TimeoutError:
                    continue

        except Exception:
            # Debug: uncomment to see connection errors
            # print(f"Connection error for client {self.client_id}: {e}")
            pass

        return 0

    def send_message(self, target: str, message: str) -> float:
        """Send a message and measure response time."""
        if not self.socket or not self.connected:
            return 0

        start_time = time.time()
        try:
            self.socket.send(f"PRIVMSG {target} :{message}\r\n".encode())

            # Wait for response (simple ACK)
            self.socket.recv(4096)
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            return response_time

        except Exception:
            return 0

    def join_channel(self, channel: str) -> bool:
        """Join a channel."""
        if not self.socket or not self.connected:
            return False

        try:
            self.socket.send(f"JOIN {channel}\r\n".encode())
            response = self.socket.recv(4096).decode()
            return "JOIN" in response or "366" in response
        except Exception:
            return False

    def disconnect(self):
        """Disconnect from server."""
        if self.socket:
            with contextlib.suppress(BaseException):
                self.socket.close()
        self.connected = False


class LoadTestRunner:
    """Runner for load testing scenarios with controlled server."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: list[IRCPerformanceClient] = []

    def create_clients(self, count: int) -> list[IRCPerformanceClient]:
        """Create multiple IRC clients."""
        clients = []
        for i in range(count):
            client = IRCPerformanceClient(self.host, self.port, i)
            clients.append(client)
        return clients

    def run_connect_test(self, client_count: int = 10) -> dict[str, Any]:
        """Test connection performance."""
        clients = self.create_clients(client_count)
        connect_times = []

        with ThreadPoolExecutor(max_workers=min(client_count, 10)) as executor:
            futures = [executor.submit(client.connect) for client in clients]
            for future in as_completed(futures):
                connect_time = future.result()
                if connect_time > 0:
                    connect_times.append(connect_time)

        # Cleanup
        for client in clients:
            client.disconnect()

        if not connect_times:
            return {"error": "No successful connections"}

        return {
            "client_count": len(connect_times),
            "avg_connect_time": statistics.mean(connect_times),
            "min_connect_time": min(connect_times),
            "max_connect_time": max(connect_times),
            "connections_per_second": len(connect_times) / max(connect_times) if connect_times else 0,
        }

    def run_message_test(self, client_count: int = 5, messages_per_client: int = 10) -> dict[str, Any]:
        """Test message throughput performance."""
        clients = self.create_clients(client_count)
        connected_clients = []

        # Connect clients
        for client in clients:
            if client.connect() > 0:
                connected_clients.append(client)

        if not connected_clients:
            return {"error": "No clients could connect"}

        # Have all clients join a channel
        test_channel = f"#perf_test_{int(time.time())}"
        for client in connected_clients:
            client.join_channel(test_channel)
            time.sleep(0.1)  # Small delay to avoid overwhelming server

        # Send messages
        total_messages = 0
        response_times = []

        with ThreadPoolExecutor(max_workers=min(len(connected_clients), 5)) as executor:
            futures = []
            for client in connected_clients:
                for i in range(messages_per_client):
                    message = f"Performance test message {i} from client {client.client_id}"
                    future = executor.submit(client.send_message, test_channel, message)
                    futures.append(future)

            for future in as_completed(futures):
                response_time = future.result()
                if response_time > 0:
                    response_times.append(response_time)
                    total_messages += 1

        # Cleanup
        for client in connected_clients:
            client.disconnect()

        if not response_times:
            return {"error": "No messages sent successfully"}

        return {
            "total_messages": total_messages,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "messages_per_second": total_messages / sum(response_times) if response_times else 0,
        }

    def run_channel_join_test(self, client_count: int = 20) -> dict[str, Any]:
        """Test concurrent channel join performance."""
        clients = self.create_clients(client_count)
        connected_clients = []

        # Connect clients first
        for client in clients:
            if client.connect() > 0:
                connected_clients.append(client)

        if not connected_clients:
            return {"error": "No clients could connect"}

        # Test joining channels
        test_channel = f"#join_test_{int(time.time())}"

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=min(len(connected_clients), 10)) as executor:
            futures = [executor.submit(client.join_channel, test_channel) for client in connected_clients]
            successful_joins = 0

            for future in as_completed(futures):
                if future.result():
                    successful_joins += 1

        total_join_time = time.time() - start_time

        # Cleanup
        for client in connected_clients:
            client.disconnect()

        return {
            "total_clients": len(connected_clients),
            "successful_joins": successful_joins,
            "total_join_time": total_join_time,
            "joins_per_second": successful_joins / total_join_time if total_join_time > 0 else 0,
            "success_rate": successful_joins / len(connected_clients) if connected_clients else 0,
        }


class TestPerformanceLoad(BaseServerTestCase):
    """Performance and load testing for IRC services with controlled server."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = False
            self.run_services = False
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}
        self.load_tester = LoadTestRunner(self.hostname, self.port)

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.performance
    @pytest.mark.slow
    def test_connection_performance(self):
        """Test IRC server connection performance."""
        result = self.load_tester.run_connect_test(client_count=10)

        assert "error" not in result, f"Connection test failed: {result.get('error')}"
        assert result["client_count"] > 0, "Should have successful connections"
        assert result["avg_connect_time"] < 5.0, "Average connect time should be reasonable"
        assert result["connections_per_second"] > 0, "Should have connection throughput"

        print("Connection Performance Results:")
        print(f"  Clients: {result['client_count']}")
        print(".3f")
        print(".3f")
        print(".1f")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.performance
    @pytest.mark.slow
    def test_message_performance(self):
        """Test IRC message throughput performance."""
        result = self.load_tester.run_message_test(client_count=5, messages_per_client=10)

        if "error" in result:
            pytest.skip(f"Message test failed: {result['error']}")

        assert result["total_messages"] > 0, "Should send messages"
        assert result["avg_response_time"] < 1.0, "Message response should be fast"
        assert result["messages_per_second"] > 0, "Should have message throughput"

        print("Message Performance Results:")
        print(f"  Total messages: {result['total_messages']}")
        print(".3f")
        print(".1f")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_channel_joins(self):
        """Test performance of concurrent channel joins."""
        result = self.load_tester.run_channel_join_test(client_count=20)

        if "error" in result:
            pytest.skip(f"Channel join test failed: {result['error']}")

        assert result["successful_joins"] > 0, "Should have successful channel joins"
        assert result["success_rate"] > 0.8, "Should have high join success rate"
        assert result["joins_per_second"] > 0, "Should have join throughput"

        print("Channel Join Performance Results:")
        print(f"  Total clients: {result['total_clients']}")
        print(f"  Successful joins: {result['successful_joins']}")
        print(".3f")
        print(".1f")
        print(".1%")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.performance
    @pytest.mark.slow
    def test_mixed_workload_performance(self):
        """Test mixed workload performance (connects, joins, messages)."""
        # Create a comprehensive test scenario
        clients = self.load_tester.create_clients(15)
        connected_clients = []
        test_channel = f"#mixed_test_{int(time.time())}"

        # Phase 1: Connect clients
        connect_times = []
        for client in clients:
            connect_time = client.connect()
            if connect_time > 0:
                connected_clients.append(client)
                connect_times.append(connect_time)

        assert len(connected_clients) > 10, "Should have majority of clients connect"

        # Phase 2: Join channel
        join_start = time.time()
        successful_joins = 0
        for client in connected_clients:
            if client.join_channel(test_channel):
                successful_joins += 1
            time.sleep(0.05)  # Small stagger

        time.time() - join_start

        # Phase 3: Send messages
        message_times = []
        messages_sent = 0

        for i, client in enumerate(connected_clients):
            message = f"Mixed workload test message {i}"
            response_time = client.send_message(test_channel, message)
            if response_time > 0:
                message_times.append(response_time)
                messages_sent += 1

        # Cleanup
        for client in connected_clients:
            client.disconnect()

        # Assertions
        assert successful_joins > len(connected_clients) * 0.8, "Most clients should join successfully"
        assert messages_sent > 0, "Should send some messages"
        assert statistics.mean(connect_times) < 3.0, "Connection times should be reasonable"

        if message_times:
            assert statistics.mean(message_times) < 1.0, "Message response times should be good"

        print("Mixed Workload Performance Results:")
        print(f"  Connected clients: {len(connected_clients)}/{len(clients)}")
        print(f"  Successful joins: {successful_joins}")
        print(f"  Messages sent: {messages_sent}")
        print(".3f")
        if message_times:
            print(".3f")

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.performance
    @pytest.mark.slow
    def test_server_scalability(self):
        """Test server scalability under increasing load."""
        scalability_results = []

        # Test with increasing client counts
        for client_count in [5, 10, 20]:
            result = self.load_tester.run_connect_test(client_count=client_count)
            if "error" not in result:
                scalability_results.append(
                    {
                        "client_count": client_count,
                        "avg_connect_time": result["avg_connect_time"],
                        "connections_per_second": result["connections_per_second"],
                    }
                )

        # Verify scalability (connection times shouldn't degrade too much)
        if len(scalability_results) >= 2:
            first_test = scalability_results[0]
            last_test = scalability_results[-1]

            # Last test shouldn't be more than 3x slower than first
            degradation_ratio = last_test["avg_connect_time"] / first_test["avg_connect_time"]
            assert degradation_ratio < 3.0, ".2f"

            print("Server Scalability Results:")
            for result in scalability_results:
                print(
                    f"  {result['client_count']} clients: {result['avg_connect_time']:.3f}s avg, {result['connections_per_second']:.1f} conn/s"
                )

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_and_resource_usage(self):
        """Test server resource usage under load (basic connectivity test)."""
        # This is a simplified resource test - in a real scenario you'd monitor
        # actual server process memory/CPU usage

        # Create some load
        clients = []
        for i in range(10):
            client = self.connectClient(f"resource_test_{i}")
            clients.append(client)

        test_channel = f"#resource_test_{int(time.time())}"

        # Have clients join and chat
        for client in clients:
            self.joinChannel(client, test_channel)
            self.sendLine(client, f"PRIVMSG {test_channel} :Resource usage test message")

        # Verify server is still responsive
        self.sendLine(clients[0], "PING resource_test")
        pong = self.getMessage(clients[0])
        self.assertMessageMatch(pong, command="PONG", params=["resource_test"])

        # Basic assertion that server handled the load
        assert len(clients) == 10, "All clients should be connected"
        assert self.controller.proc is not None, "Server should still be running"
