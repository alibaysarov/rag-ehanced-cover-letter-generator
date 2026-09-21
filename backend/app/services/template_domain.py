"""Pure domain logic for graph-based cover-letter templates."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping, Sequence
from uuid import UUID

from app.domain.template_enums import TemplateCase, TemplateNodeKind

ALLOWED_TOKENS = frozenset({"job_title", "company_name", "matched_technologies"})
TOKEN_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]")


@dataclass(frozen=True)
class DomainProject:
    id: int
    name: str
    technologies: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoredProject:
    project: DomainProject
    matched_technologies: tuple[str, ...]

    @property
    def match_count(self) -> int:
        return len(self.matched_technologies)


@dataclass(frozen=True)
class GraphNode:
    id: UUID
    node_kind: TemplateNodeKind
    phrase_id: int | None = None
    phrase_text: str | None = None
    phrase_is_active: bool = True
    phrase_is_owned: bool = True


@dataclass(frozen=True)
class GraphEdge:
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    branch_order: int


@dataclass(frozen=True)
class GraphValidationResult:
    errors: tuple[dict[str, object], ...]
    paths_without_projects: bool


@dataclass(frozen=True)
class RenderContext:
    job_title: str
    company_name: str | None
    matched_technologies: tuple[str, ...]
    projects: tuple[DomainProject, ...]


def unique_technologies(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def technology_pattern(technology: str) -> re.Pattern[str]:
    escaped = re.escape(" ".join(technology.split()))
    return re.compile(r"(?<![\w+#.])" + escaped + r"(?![\w+#.])", re.IGNORECASE)


def matching_technologies(
    vacancy_text: str, technologies: Sequence[str], *, limit: int | None = 4
) -> list[str]:
    """Return declared technologies found as complete technical names."""
    result: list[str] = []
    for technology in unique_technologies(technologies):
        if technology_pattern(technology).search(vacancy_text):
            result.append(technology)
            if limit is not None and len(result) == limit:
                break
    return result


def score_projects(
    projects: Sequence[DomainProject], vacancy_text: str
) -> list[ScoredProject]:
    scored = [
        ScoredProject(
            project=DomainProject(
                id=project.id,
                name=project.name.strip(),
                technologies=tuple(unique_technologies(project.technologies)),
            ),
            matched_technologies=tuple(
                matching_technologies(vacancy_text, project.technologies, limit=None)
            ),
        )
        for project in projects
        if project.name.strip()
    ]
    return sorted(scored, key=lambda item: (-item.match_count, item.project.id))


def classify_template_case(scored_projects: Sequence[ScoredProject]) -> TemplateCase:
    if not scored_projects:
        return TemplateCase.NO_PORTFOLIO
    best_count = max(project.match_count for project in scored_projects)
    if best_count == 0:
        return TemplateCase.NO_RELEVANT_PROJECTS
    if best_count == 1:
        return TemplateCase.PARTIAL_MATCH
    return TemplateCase.RELEVANT_DOMAIN


def validate_graph(
    *,
    nodes: Sequence[GraphNode],
    edges: Sequence[GraphEdge],
    root_node_id: UUID | None,
    template_case: TemplateCase,
    require_active_phrases: bool = False,
) -> GraphValidationResult:
    errors: list[dict[str, object]] = []
    node_by_id = {node.id: node for node in nodes}
    if len(node_by_id) != len(nodes):
        errors.append({"code": "duplicate_node_id"})
    edge_by_id = {edge.id: edge for edge in edges}
    if len(edge_by_id) != len(edges):
        errors.append({"code": "duplicate_edge_id"})
    if len(nodes) > 100:
        errors.append({"code": "node_limit_exceeded", "limit": 100})
    if len(edges) > 300:
        errors.append({"code": "edge_limit_exceeded", "limit": 300})

    projects_nodes = [n for n in nodes if n.node_kind == TemplateNodeKind.PROJECTS]
    if len(projects_nodes) > 1:
        errors.append(
            {
                "code": "duplicate_projects_node",
                "node_ids": [str(n.id) for n in projects_nodes],
            }
        )
    if template_case == TemplateCase.NO_PORTFOLIO and projects_nodes:
        errors.append(
            {"code": "projects_node_forbidden", "node_id": str(projects_nodes[0].id)}
        )

    for node in nodes:
        valid_pair = (
            node.node_kind == TemplateNodeKind.PHRASE and node.phrase_id is not None
        ) or (node.node_kind == TemplateNodeKind.PROJECTS and node.phrase_id is None)
        if not valid_pair:
            errors.append({"code": "invalid_node_phrase", "node_id": str(node.id)})
        if node.node_kind == TemplateNodeKind.PHRASE and not node.phrase_is_owned:
            errors.append({"code": "foreign_phrase", "node_id": str(node.id)})
        if (
            require_active_phrases
            and node.node_kind == TemplateNodeKind.PHRASE
            and not node.phrase_is_active
        ):
            errors.append({"code": "inactive_phrase", "node_id": str(node.id)})

    adjacency: dict[UUID, list[GraphEdge]] = {node_id: [] for node_id in node_by_id}
    incoming: dict[UUID, int] = {node_id: 0 for node_id in node_by_id}
    edge_pairs: set[tuple[UUID, UUID]] = set()
    branch_orders: set[tuple[UUID, int]] = set()
    for edge in edges:
        if (
            edge.source_node_id not in node_by_id
            or edge.target_node_id not in node_by_id
        ):
            errors.append({"code": "dangling_edge", "edge_id": str(edge.id)})
            continue
        if edge.source_node_id == edge.target_node_id:
            errors.append({"code": "self_loop", "edge_id": str(edge.id)})
        pair = (edge.source_node_id, edge.target_node_id)
        if pair in edge_pairs:
            errors.append({"code": "duplicate_edge", "edge_id": str(edge.id)})
        edge_pairs.add(pair)
        branch_key = (edge.source_node_id, edge.branch_order)
        if branch_key in branch_orders:
            errors.append({"code": "duplicate_branch_order", "edge_id": str(edge.id)})
        branch_orders.add(branch_key)
        if edge.branch_order < 0:
            errors.append({"code": "invalid_branch_order", "edge_id": str(edge.id)})
        adjacency[edge.source_node_id].append(edge)
        incoming[edge.target_node_id] += 1

    if not nodes:
        errors.append({"code": "empty_graph"})
    if root_node_id is None:
        errors.append({"code": "root_required"})
    elif root_node_id not in node_by_id:
        errors.append({"code": "invalid_root", "node_id": str(root_node_id)})
    elif incoming[root_node_id] != 0:
        errors.append({"code": "root_has_incoming_edge", "node_id": str(root_node_id)})

    color: dict[UUID, int] = {node_id: 0 for node_id in node_by_id}
    cycle_nodes: set[UUID] = set()

    def visit(node_id: UUID, stack: list[UUID]) -> None:
        color[node_id] = 1
        stack.append(node_id)
        for edge in adjacency[node_id]:
            target = edge.target_node_id
            if color[target] == 0:
                visit(target, stack)
            elif color[target] == 1:
                cycle_nodes.update(stack[stack.index(target) :])
        stack.pop()
        color[node_id] = 2

    for node_id in node_by_id:
        if color[node_id] == 0:
            visit(node_id, [])
    if cycle_nodes:
        errors.append(
            {"code": "cycle_detected", "node_ids": sorted(map(str, cycle_nodes))}
        )

    reachable: set[UUID] = set()
    if root_node_id in node_by_id:
        valid_root = root_node_id
        assert valid_root is not None
        pending = [valid_root]
        while pending:
            current = pending.pop()
            if current in reachable:
                continue
            reachable.add(current)
            pending.extend(edge.target_node_id for edge in adjacency[current])
        for node_id in node_by_id.keys() - reachable:
            errors.append({"code": "unreachable_node", "node_id": str(node_id)})

    # In a finite DAG every reachable node reaches a terminal. Cycles are already
    # reported above; this explicit check keeps the invariant machine-readable.
    terminal_memo: dict[UUID, bool] = {}

    def reaches_terminal(node_id: UUID, visiting: set[UUID]) -> bool:
        if node_id in terminal_memo:
            return terminal_memo[node_id]
        if node_id in visiting:
            return False
        outgoing = adjacency[node_id]
        result = not outgoing or any(
            reaches_terminal(edge.target_node_id, visiting | {node_id})
            for edge in outgoing
        )
        terminal_memo[node_id] = result
        return result

    for node_id in reachable:
        if not reaches_terminal(node_id, set()):
            errors.append({"code": "no_terminal_path", "node_id": str(node_id)})

    paths_without_projects = False
    if root_node_id in node_by_id and not cycle_nodes:
        valid_root = root_node_id
        assert valid_root is not None
        project_ids = {node.id for node in projects_nodes}

        def misses_projects(node_id: UUID, seen_project: bool) -> bool:
            seen_project = seen_project or node_id in project_ids
            outgoing = adjacency[node_id]
            if not outgoing:
                return not seen_project
            return any(
                misses_projects(edge.target_node_id, seen_project) for edge in outgoing
            )

        paths_without_projects = misses_projects(valid_root, False)

    return GraphValidationResult(tuple(errors), paths_without_projects)


def select_path(
    *,
    vacancy_id: int | str,
    template_id: int,
    template_version: int,
    root_node_id: UUID,
    edges: Sequence[GraphEdge],
) -> list[UUID]:
    adjacency: dict[UUID, list[GraphEdge]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source_node_id, []).append(edge)
    for outgoing in adjacency.values():
        outgoing.sort(key=lambda edge: (edge.branch_order, str(edge.id)))

    path = [root_node_id]
    current = root_node_id
    visited = {current}
    while outgoing := adjacency.get(current):
        seed = f"{vacancy_id}:{template_id}:{template_version}:{current}".encode()
        value = int.from_bytes(hashlib.sha256(seed).digest()[:8], "big", signed=False)
        current = outgoing[value % len(outgoing)].target_node_id
        if current in visited:
            raise ValueError("cycle_detected")
        visited.add(current)
        path.append(current)
    return path


def unknown_tokens(text: str) -> set[str]:
    tokens = set(TOKEN_PATTERN.findall(text))
    if "projects" in tokens:
        return (tokens - ALLOWED_TOKENS) | {"projects"}
    return tokens - ALLOWED_TOKENS


def _render_phrase(text: str, values: Mapping[str, str]) -> str:
    rendered = TOKEN_PATTERN.sub(
        lambda match: values.get(match.group(1), match.group(0)), text
    )
    rendered = re.sub(r"[ \t]+", " ", rendered)
    rendered = re.sub(r"\s+([,.;:!?])", r"\1", rendered)
    rendered = re.sub(r"(?m)^\s*[,;:]\s*$", "", rendered)
    return rendered.strip()


def render_path(
    *, path: Sequence[UUID], nodes: Mapping[UUID, GraphNode], context: RenderContext
) -> str:
    values = {
        "job_title": context.job_title.strip(),
        "company_name": (context.company_name or "").strip(),
        "matched_technologies": ", ".join(context.matched_technologies),
    }
    blocks: list[str] = []
    for node_id in path:
        node = nodes[node_id]
        if node.node_kind == TemplateNodeKind.PROJECTS:
            lines = []
            for project in context.projects[:3]:
                technologies = unique_technologies(project.technologies)
                suffix = f" — {', '.join(technologies)}" if technologies else ""
                lines.append(f"«{project.name.strip()}»{suffix}.")
            block = "\n".join(lines)
        else:
            block = _render_phrase(node.phrase_text or "", values)
        if block.strip():
            blocks.append(block.strip())
    rendered = "\n\n".join(blocks)
    return re.sub(r"\n{3,}", "\n\n", rendered).strip()
