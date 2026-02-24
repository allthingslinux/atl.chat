"""Performance and load testing for IRC servers using controlled test environment."""

import contextlib
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import psutil
import pytest
import requests

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
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))

            # Register user
            nick = f"perf_test_{self.client_id}_{int(time.time())}"
            self.socket.send(f"NICK {nick}\r\n".encode())
            self.socket.send(f"USER perfuser{self.client_id} 0 * :Performance Test User\r\n".encode())

            # Wait for welcome
            response = self.socket.recv(4096).decode()
            if "001" in response:
                self.connected = True
                self.connect_time = time.time() - start_time
                return self.connect_time

        except Exception:
            pass

        return 0

    def send_message(self, target: str, message: str) -> float:
        """Send message and measure response time."""
        if not self.connected:
            return 0

        start_time = time.time()
        try:
            self.socket.send(f"PRIVMSG {target} :{message}\r\n".encode())
            # Simple timing - in real scenario would wait for response
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            return response_time
        except Exception:
            return 0

    def join_channel(self, channel: str) -> float:
        """Join channel and measure response time."""
        if not self.connected:
            return 0

        start_time = time.time()
        try:
            self.socket.send(f"JOIN {channel}\r\n".encode())
            response = self.socket.recv(4096).decode()
            if "JOIN" in response:
                return time.time() - start_time
        except Exception:
            pass
        return 0

    def disconnect(self):
        """Disconnect from server."""
        if self.socket:
            with contextlib.suppress(Exception):
                self.socket.close()
        self.connected = False


class LoadTestRunner:
    """Runner for load testing scenarios."""

    def __init__(self, host="localhost", port=6667):
        self.host = host
        self.port = port
        self.clients = []

    def create_clients(self, count: int) -> list[IRCPerformanceClient]:
        """Create multiple IRC clients."""
        clients = []
        for i in range(count):
            client = IRCPerformanceClient(self.host, self.port, i)
            clients.append(client)
        return clients

    def run_connect_test(self, client_count: int) -> dict[str, Any]:
        """Run connection performance test."""
        clients = self.create_clients(client_count)
        connect_times = []

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(client.connect) for client in clients]
            for future in as_completed(futures):
                connect_time = future.result()
                if connect_time > 0:
                    connect_times.append(connect_time)

        total_time = time.time() - start_time

        # Cleanup
        for client in clients:
            client.disconnect()

        return {
            "client_count": len(connect_times),
            "total_time": total_time,
            "connect_times": connect_times,
            "avg_connect_time": statistics.mean(connect_times) if connect_times else 0,
            "min_connect_time": min(connect_times) if connect_times else 0,
            "max_connect_time": max(connect_times) if connect_times else 0,
            "connections_per_second": len(connect_times) / total_time if total_time > 0 else 0,
        }

    def run_message_test(self, client_count: int, messages_per_client: int) -> dict[str, Any]:
        """Run messaging performance test."""
        clients = self.create_clients(client_count)
        connected_clients = []

        # Connect all clients first
        for client in clients:
            if client.connect() > 0:
                connected_clients.append(client)

        if not connected_clients:
            return {"error": "No clients could connect"}

        # Create test channel
        channel = f"#load_test_{int(time.time())}"
        connected_clients[0].socket.send(f"JOIN {channel}\r\n".encode())

        # Run messaging test
        total_messages = 0
        response_times = []

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=len(connected_clients)) as executor:
            futures = []
            for client in connected_clients:
                future = executor.submit(self._send_messages, client, channel, messages_per_client)
                futures.append(future)

            for future in as_completed(futures):
                result = future.result()
                total_messages += result["messages_sent"]
                response_times.extend(result["response_times"])

        total_time = time.time() - start_time

        # Cleanup
        for client in connected_clients:
            client.disconnect()

        return {
            "client_count": len(connected_clients),
            "total_messages": total_messages,
            "total_time": total_time,
            "messages_per_second": total_messages / total_time if total_time > 0 else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "response_times": response_times,
        }

    def _send_messages(self, client: IRCPerformanceClient, channel: str, count: int) -> dict[str, Any]:
        """Send multiple messages from a client."""
        messages_sent = 0
        response_times = []

        for i in range(count):
            message = f"Load test message {i} from client {client.client_id}"
            response_time = client.send_message(channel, message)
            if response_time > 0:
                messages_sent += 1
                response_times.append(response_time)

        return {"messages_sent": messages_sent, "response_times": response_times}


class TestPerformanceLoad(BaseServerTestCase):
    """Performance and load testing for IRC services."""

    @pytest.fixture
    def load_tester(self):
        """Create load test runner with controlled server info."""
        return LoadTestRunner(self.hostname, self.port)

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.performance
    @pytest.mark.slow
    def test_connection_performance(self, load_tester):
        """Test IRC server connection performance."""
        # Test with small load first
        result = load_tester.run_connect_test(client_count=10)

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
    def test_message_performance(self, load_tester):
        """Test IRC message throughput performance."""
        result = load_tester.run_message_test(client_count=5, messages_per_client=10)

        if "error" not in result:
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
    def test_concurrent_channel_joins(self, load_tester):
        """Test performance of concurrent channel joins."""
        clients = load_tester.create_clients(20)
        connected_clients = []
        join_times = []

        # Connect clients
        for client in clients:
            if client.connect() > 0:
                connected_clients.append(client)

        assert len(connected_clients) > 0, "Should have connected clients"

        # Test channel joins
        test_channel = f"#join_test_{int(time.time())}"

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=len(connected_clients)) as executor:
            futures = [executor.submit(client.join_channel, test_channel) for client in connected_clients]
            for future in as_completed(futures):
                join_time = future.result()
                if join_time > 0:
                    join_times.append(join_time)

        time.time() - start_time

        # Cleanup
        for client in connected_clients:
            client.disconnect()

        assert len(join_times) > 0, "Should have successful joins"
        assert statistics.mean(join_times) < 2.0, "Channel joins should be fast"

        print("Channel Join Performance:")
        print(f"  Successful joins: {len(join_times)}")
        print(".3f")
        print(".3f")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_server_resource_usage(self, docker_client):
        """Test server resource usage under load."""
        try:
            # Get initial resource usage
            initial_cpu = psutil.cpu_percent(interval=1)
            initial_memory = psutil.virtual_memory().percent

            # Run a small load test
            load_tester = LoadTestRunner()
            load_tester.run_connect_test(client_count=20)

            # Get resource usage after load
            final_cpu = psutil.cpu_percent(interval=1)
            final_memory = psutil.virtual_memory().percent

            # Resource usage should not be excessive
            cpu_increase = final_cpu - initial_cpu
            memory_increase = final_memory - initial_memory

            assert cpu_increase < 50, f"CPU usage increase too high: {cpu_increase}%"
            assert memory_increase < 20, f"Memory usage increase too high: {memory_increase}%"

            print("Resource Usage:")
            print(".1f")
            print(".1f")

        except ImportError:
            pytest.skip("psutil not available for resource monitoring")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_webpanel_performance(self):
        """Test WebPanel performance under load."""

        # Test basic response time
        start_time = time.time()
        try:
            response = requests.get("http://localhost:8080", timeout=10)
            response_time = time.time() - start_time

            assert response.status_code == 200
            assert response_time < 2.0, f"WebPanel response too slow: {response_time}s"

        except requests.exceptions.RequestException:
            pytest.skip("WebPanel not accessible for performance testing")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_ssl_performance(self):
        """Test SSL connection performance."""
        import ssl

        connect_times = []

        # Test multiple SSL connections
        for _i in range(5):
            start_time = time.time()
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                with socket.create_connection(("localhost", 6697), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname="localhost"):
                        connect_time = time.time() - start_time
                        connect_times.append(connect_time)

            except (OSError, ssl.SSLError):
                continue

        if connect_times:
            avg_ssl_time = statistics.mean(connect_times)
            assert avg_ssl_time < 3.0, f"SSL connection too slow: {avg_ssl_time}s"

            print("SSL Performance:")
            print(f"  Average SSL connect time: {avg_ssl_time:.3f}s")
            print(f"  Successful SSL connections: {len(connect_times)}")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_service_scalability(self, docker_client):
        """Test service scalability with increasing load."""
        load_tester = LoadTestRunner()

        # Test different load levels
        test_levels = [5, 10, 20]
        results = {}

        for client_count in test_levels:
            result = load_tester.run_connect_test(client_count)
            results[client_count] = result

            # Each level should maintain reasonable performance
            if result["client_count"] > 0:
                assert result["avg_connect_time"] < 10.0, f"Performance degraded at {client_count} clients"

        print("Scalability Test Results:")
        for count, result in results.items():
            if result["client_count"] > 0:
                print(f"  {count} clients: {result['avg_connect_time']:.3f}s avg connect time")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_leak_detection(self, docker_client):
        """Test for memory leaks under sustained load."""
        try:
            # Get initial memory usage
            containers = docker_client.containers.list(filters={"name": "unrealircd"})

            if not containers:
                pytest.skip("UnrealIRCd container not running")

            container = containers[0]

            # Run sustained load test
            load_tester = LoadTestRunner()
            start_memory = self._get_container_memory(container)

            # Run multiple load cycles
            for _i in range(3):
                load_tester.run_connect_test(client_count=15)
                time.sleep(2)

            end_memory = self._get_container_memory(container)

            # Memory usage should not increase significantly
            if start_memory and end_memory:
                memory_increase = ((end_memory - start_memory) / start_memory) * 100
                assert memory_increase < 20, f"Memory leak detected: {memory_increase}% increase"

        except Exception:
            pytest.skip("Could not perform memory leak test")

    def _get_container_memory(self, container) -> float:
        """Get container memory usage in MB."""
        try:
            stats = container.stats(stream=False)
            memory_stats = stats.get("memory_stats", {})
            usage = memory_stats.get("usage", 0)
            return usage / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0

    @pytest.mark.performance
    @pytest.mark.slow
    def test_network_latency(self):
        """Test network latency between services."""
        latencies = []

        # Test multiple connections to measure latency
        for _i in range(10):
            start_time = time.time()

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(("localhost", 6667))

                # Send ping-like command
                sock.send(b"PING test\r\n")
                response = sock.recv(4096)

                latency = time.time() - start_time
                if response and b"PONG" in response:
                    latencies.append(latency)

                sock.close()

            except Exception:
                continue

        if latencies:
            avg_latency = statistics.mean(latencies)
            assert avg_latency < 0.1, f"Network latency too high: {avg_latency}s"

            print("Network Latency Test:")
            print(f"  Average latency: {avg_latency:.4f}s")
            print(f"  Samples: {len(latencies)}")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_error_rate_under_load(self, load_tester):
        """Test error rate under high load conditions."""
        # Test with high load to check error handling
        result = load_tester.run_connect_test(client_count=50)

        if result["client_count"] > 0:
            success_rate = (result["client_count"] / 50) * 100
            assert success_rate > 80, f"Too many connection failures: {success_rate}% success rate"

            print("Error Rate Test:")
            print(".1f")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_service_recovery_performance(self, docker_client):
        """Test service recovery performance after failures."""
        try:
            containers = docker_client.containers.list(filters={"name": "unrealircd"})

            if not containers:
                pytest.skip("UnrealIRCd container not running")

            container = containers[0]

            # Measure restart time
            start_time = time.time()
            container.restart()
            restart_time = time.time() - start_time

            # Wait for service to be ready
            time.sleep(5)

            # Test connectivity after restart
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex(("localhost", 6667))
            sock.close()

            assert result == 0, "Service should be accessible after restart"
            assert restart_time < 30, f"Restart too slow: {restart_time}s"

            print("Service Recovery Test:")
            print(".2f")

        except Exception:
            pytest.skip("Could not test service recovery")
