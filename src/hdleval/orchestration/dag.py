"""A minimal directed-acyclic-graph executor.

Replaces linear execution with a DAG so stages can be cached, conditionally
skipped, incrementally recomputed and scheduled in parallel. Each node declares
dependencies and a pure ``fn(inputs) -> result``; results are content-hash
cached so unchanged upstream inputs short-circuit recomputation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeResult:
    node: str
    value: Any
    cached: bool = False


@dataclass
class Node:
    name: str
    fn: Callable[[dict[str, Any]], Any]
    deps: list[str] = field(default_factory=list)
    condition: Callable[[dict[str, Any]], bool] | None = None


class DAG:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._cache: dict[str, Any] = {}

    def add(self, node: Node) -> DAG:
        if node.name in self._nodes:
            raise ValueError(f"duplicate node {node.name!r}")
        self._nodes[node.name] = node
        return self

    def _toposort(self) -> list[str]:
        visited: dict[str, int] = {}
        order: list[str] = []

        def visit(n: str) -> None:
            state = visited.get(n, 0)
            if state == 1:
                raise ValueError(f"cycle detected at {n!r}")
            if state == 2:
                return
            visited[n] = 1
            for d in self._nodes[n].deps:
                if d not in self._nodes:
                    raise ValueError(f"unknown dependency {d!r} for {n!r}")
                visit(d)
            visited[n] = 2
            order.append(n)

        for name in self._nodes:
            visit(name)
        return order

    @staticmethod
    def _key(name: str, inputs: dict[str, Any]) -> str:
        try:
            payload = json.dumps({k: str(v) for k, v in inputs.items()}, sort_keys=True)
        except TypeError:
            payload = str(inputs)
        return hashlib.sha256((name + payload).encode()).hexdigest()

    def run(
        self, initial: dict[str, Any] | None = None, use_cache: bool = True
    ) -> dict[str, NodeResult]:
        env: dict[str, Any] = dict(initial or {})
        results: dict[str, NodeResult] = {}
        for name in self._toposort():
            node = self._nodes[name]
            inputs = {d: env[d] for d in node.deps if d in env}
            if node.condition is not None and not node.condition(env):
                results[name] = NodeResult(name, None, cached=False)
                env[name] = None
                continue
            key = self._key(name, inputs)
            if use_cache and key in self._cache:
                val = self._cache[key]
                results[name] = NodeResult(name, val, cached=True)
            else:
                val = node.fn(inputs)
                self._cache[key] = val
                results[name] = NodeResult(name, val, cached=False)
            env[name] = val
        return results
