"""Adversarial tests for concurrent access and race conditions.

Tests concurrent message delivery through the pipeline, concurrent
TTL map operations, and concurrent config reloads.

Validates: Requirement 15.4
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from bridge.config.schema import Config
from bridge.formatting.converter import convert
from bridge.gateway.pipeline import Pipeline, TransformContext
from bridge.gateway.steps import format_convert, unwrap_spoiler, wrap_spoiler
from bridge.tracking.base import BidirectionalTTLMap

# ---------------------------------------------------------------------------
# Concurrent message delivery through the pipeline
# ---------------------------------------------------------------------------


class TestConcurrentPipeline:
    """Multiple messages processed through the pipeline concurrently."""

    def test_concurrent_pipeline_transforms(self) -> None:
        """Multiple threads transforming messages simultaneously should
        not corrupt each other's results."""
        pipeline = Pipeline([unwrap_spoiler, format_convert, wrap_spoiler])
        results: list[str | None] = [None] * 100
        errors: list[Exception] = []

        def transform_message(idx: int) -> None:
            try:
                ctx = TransformContext(origin="discord", target="irc")
                content = f"message number {idx}"
                result = pipeline.transform(content, ctx)
                results[idx] = result
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(transform_message, i) for i in range(100)]
            for f in futures:
                f.result()

        assert not errors, f"Errors during concurrent pipeline: {errors}"
        for i, result in enumerate(results):
            assert result is not None, f"Result {i} was None"
            assert f"message number {i}" in result

    def test_concurrent_conversions(self) -> None:
        """Concurrent format conversions should produce correct results."""
        results: dict[int, str] = {}
        errors: list[Exception] = []

        def do_convert(idx: int) -> None:
            try:
                text = f"**bold {idx}**"
                result = convert(text, "discord", "irc")
                results[idx] = result
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(do_convert, i) for i in range(50)]
            for f in futures:
                f.result()

        assert not errors
        for i in range(50):
            assert str(i) in results[i]

    @pytest.mark.asyncio
    async def test_async_concurrent_pipeline(self) -> None:
        """Async concurrent pipeline transforms should not interfere."""
        pipeline = Pipeline([format_convert])

        async def transform(idx: int) -> str | None:
            ctx = TransformContext(origin="irc", target="discord")
            return pipeline.transform(f"\x02bold {idx}\x02", ctx)

        tasks = [transform(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            assert result is not None
            assert str(i) in result


# ---------------------------------------------------------------------------
# Concurrent TTL map operations
# ---------------------------------------------------------------------------


class TestConcurrentTTLMap:
    """Concurrent reads and writes to BidirectionalTTLMap."""

    def test_concurrent_store_and_lookup(self) -> None:
        """Concurrent stores and lookups should not crash or corrupt data."""
        ttl_map: BidirectionalTTLMap[str, None] = BidirectionalTTLMap(ttl_seconds=60, maxsize=10000)
        errors: list[Exception] = []

        def store_entries(start: int, count: int) -> None:
            try:
                for i in range(start, start + count):
                    ttl_map.store(f"key1_{i}", f"key2_{i}")
            except Exception as exc:
                errors.append(exc)

        def lookup_entries(start: int, count: int) -> None:
            try:
                for i in range(start, start + count):
                    ttl_map.get_forward(f"key1_{i}")
                    ttl_map.get_reverse(f"key2_{i}")
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            # 4 writer threads
            for t in range(4):
                futures.append(executor.submit(store_entries, t * 250, 250))
            # 4 reader threads
            for t in range(4):
                futures.append(executor.submit(lookup_entries, t * 250, 250))
            for f in futures:
                f.result()

        assert not errors, f"Errors during concurrent TTL map ops: {errors}"

    def test_concurrent_store_and_alias(self) -> None:
        """Concurrent stores and alias additions should not crash."""
        ttl_map: BidirectionalTTLMap[str, None] = BidirectionalTTLMap(ttl_seconds=60, maxsize=10000)
        errors: list[Exception] = []

        def store_and_alias(idx: int) -> None:
            try:
                ttl_map.store(f"primary_{idx}", f"secondary_{idx}")
                ttl_map.add_alias(f"alias_{idx}", f"primary_{idx}")
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(store_and_alias, i) for i in range(200)]
            for f in futures:
                f.result()

        assert not errors

    def test_concurrent_eviction(self) -> None:
        """Concurrent writes that trigger eviction should not crash."""
        ttl_map: BidirectionalTTLMap[str, None] = BidirectionalTTLMap(ttl_seconds=3600, maxsize=100)
        errors: list[Exception] = []

        def fill_map(thread_id: int) -> None:
            try:
                for i in range(200):
                    ttl_map.store(f"t{thread_id}_k1_{i}", f"t{thread_id}_k2_{i}")
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fill_map, t) for t in range(4)]
            for f in futures:
                f.result()

        assert not errors


# ---------------------------------------------------------------------------
# Concurrent config reloads
# ---------------------------------------------------------------------------


class TestConcurrentConfigReload:
    """Concurrent config reload operations should not corrupt state."""

    def test_concurrent_reload(self) -> None:
        """Multiple threads reloading config simultaneously should not crash."""
        config = Config({"mappings": []})
        errors: list[Exception] = []

        def reload_config(idx: int) -> None:
            try:
                data = {
                    "mappings": [{"discord_channel_id": f"{idx}", "irc_channel": f"#chan{idx}"}],
                    "edit_suffix": f" (edit-{idx})",
                }
                config.reload(data)
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(reload_config, i) for i in range(50)]
            for f in futures:
                f.result()

        assert not errors

    def test_concurrent_read_during_reload(self) -> None:
        """Reading config properties while another thread reloads
        should not crash."""
        config = Config({"mappings": [], "edit_suffix": " (edited)"})
        errors: list[Exception] = []
        stop = threading.Event()

        def reader() -> None:
            try:
                while not stop.is_set():
                    _ = config.edit_suffix
                    _ = config.mappings
                    _ = config.announce_joins_and_quits
            except Exception as exc:
                errors.append(exc)

        def writer() -> None:
            try:
                for i in range(50):
                    config.reload(
                        {
                            "mappings": [{"discord_channel_id": f"{i}"}],
                            "edit_suffix": f" (v{i})",
                        }
                    )
            except Exception as exc:
                errors.append(exc)

        reader_thread = threading.Thread(target=reader)
        reader_thread.start()

        writer()
        stop.set()
        reader_thread.join(timeout=5)

        assert not errors
