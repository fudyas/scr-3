from abc import ABC
from typing import Dict, List, Optional, Set

from sdlc.models.item import ItemStatus


class DependencyGraphHelper(ABC):
    """Checks the inter-item dependency graph for cycles and readiness."""

    @staticmethod
    def find_cycle(graph: Dict[str, List[str]]) -> Optional[List[str]]:
        """Returns one dependency cycle in the graph, or None when the graph is acyclic.

        Steps:
            1. Walk the graph depth-first from every node.
            2. Keep the current path; a dependency already on the path closes a cycle.
            3. Return the cycle path from its first node back to itself.

        Args:
            graph: each node id mapped to the ids it depends on.

        Returns:
            The cycle as a node list that starts and ends with the same id, or None.
        """
        finished: Set[str] = set()
        path: List[str] = []
        on_path: Set[str] = set()

        def visit(node: str) -> Optional[List[str]]:
            """Returns a cycle reachable from the node, or None."""
            if node in on_path:
                return path[path.index(node):] + [node]
            if node in finished:
                return None
            path.append(node)
            on_path.add(node)
            for dependency in graph.get(node, []):
                cycle = visit(dependency)
                if cycle is not None:
                    return cycle
            path.pop()
            on_path.discard(node)
            finished.add(node)
            return None

        # Visits every node so disconnected parts of the graph are checked too
        for start in sorted(graph):
            cycle = visit(start)
            if cycle is not None:
                return cycle
        return None

    @staticmethod
    def unmet_dependencies(depends_on: List[str], statuses: Dict[str, ItemStatus]) -> List[str]:
        """Returns the dependencies that are not DONE.

        Args:
            depends_on: the short ids the item depends on.
            statuses: every known item's status, keyed by short id.

        Returns:
            The dependency ids that are unknown or not DONE, in input order.
        """
        return [dependency for dependency in depends_on if statuses.get(dependency) != ItemStatus.DONE]
