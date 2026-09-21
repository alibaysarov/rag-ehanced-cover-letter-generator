import unittest
from uuid import UUID

from app.domain import TemplateCase, TemplateNodeKind
from app.services.template_domain import (
    DomainProject,
    GraphEdge,
    GraphNode,
    RenderContext,
    classify_template_case,
    matching_technologies,
    render_path,
    score_projects,
    select_path,
    unknown_tokens,
    validate_graph,
)


def uid(value: int) -> UUID:
    return UUID(int=value)


class TemplateMatchingTests(unittest.TestCase):
    def test_matches_technical_names_without_substring_collisions(self):
        technologies = ["Java", "JavaScript", "C++", "C#", ".NET", "Node.js", "java"]
        text = "JAVASCRIPT, C++, C#, .NET and Node.js"

        self.assertEqual(
            matching_technologies(text, technologies, limit=None),
            ["JavaScript", "C++", "C#", ".NET", "Node.js"],
        )

    def test_classifies_all_cases_and_ignores_empty_projects(self):
        self.assertEqual(classify_template_case([]), TemplateCase.NO_PORTFOLIO)
        empty = score_projects([DomainProject(1, " ", ("Python",))], "Python")
        self.assertEqual(classify_template_case(empty), TemplateCase.NO_PORTFOLIO)
        no_match = score_projects([DomainProject(1, "A", ("Python",))], "Java")
        self.assertEqual(
            classify_template_case(no_match), TemplateCase.NO_RELEVANT_PROJECTS
        )
        partial = score_projects([DomainProject(1, "A", ("Python",))], "python")
        self.assertEqual(classify_template_case(partial), TemplateCase.PARTIAL_MATCH)
        relevant = score_projects(
            [DomainProject(1, "A", ("Python", "FastAPI"))], "python fastapi"
        )
        self.assertEqual(classify_template_case(relevant), TemplateCase.RELEVANT_DOMAIN)

    def test_score_order_is_match_count_then_id(self):
        result = score_projects(
            [
                DomainProject(3, "Third", ("Python",)),
                DomainProject(1, "First", ("Python",)),
                DomainProject(2, "Best", ("Python", "React")),
            ],
            "Python React",
        )
        self.assertEqual([item.project.id for item in result], [2, 1, 3])


class TemplateGraphTests(unittest.TestCase):
    def setUp(self):
        self.root = GraphNode(uid(1), TemplateNodeKind.PHRASE, 10, "Hello")
        self.projects = GraphNode(uid(2), TemplateNodeKind.PROJECTS)
        self.end = GraphNode(uid(3), TemplateNodeKind.PHRASE, 11, "Bye")
        self.edges = [
            GraphEdge(uid(11), uid(1), uid(2), 0),
            GraphEdge(uid(12), uid(2), uid(3), 0),
        ]

    def test_valid_graph_has_projects_on_all_paths(self):
        result = validate_graph(
            nodes=[self.root, self.projects, self.end],
            edges=self.edges,
            root_node_id=uid(1),
            template_case=TemplateCase.PARTIAL_MATCH,
            require_active_phrases=True,
        )
        self.assertEqual(result.errors, ())
        self.assertFalse(result.paths_without_projects)

    def test_reports_cycle_unreachable_wrong_root_and_invalid_phrase(self):
        invalid = GraphNode(
            uid(4), TemplateNodeKind.PHRASE, None, phrase_is_owned=False
        )
        cycle = [
            GraphEdge(uid(21), uid(1), uid(2), 0),
            GraphEdge(uid(22), uid(2), uid(1), 0),
        ]
        result = validate_graph(
            nodes=[self.root, self.projects, invalid],
            edges=cycle,
            root_node_id=uid(1),
            template_case=TemplateCase.NO_PORTFOLIO,
        )
        codes = {str(error["code"]) for error in result.errors}
        self.assertTrue(
            {
                "projects_node_forbidden",
                "invalid_node_phrase",
                "foreign_phrase",
                "root_has_incoming_edge",
                "cycle_detected",
                "unreachable_node",
            }.issubset(codes)
        )

    def test_detects_path_without_projects(self):
        edges = self.edges + [GraphEdge(uid(13), uid(1), uid(3), 1)]
        result = validate_graph(
            nodes=[self.root, self.projects, self.end],
            edges=edges,
            root_node_id=uid(1),
            template_case=TemplateCase.PARTIAL_MATCH,
        )
        self.assertEqual(result.errors, ())
        self.assertTrue(result.paths_without_projects)

    def test_select_path_is_stable(self):
        edges = [
            GraphEdge(uid(31), uid(1), uid(2), 0),
            GraphEdge(uid(32), uid(1), uid(3), 1),
        ]
        first = select_path(
            vacancy_id=9,
            template_id=7,
            template_version=2,
            root_node_id=uid(1),
            edges=edges,
        )
        second = select_path(
            vacancy_id=9,
            template_id=7,
            template_version=2,
            root_node_id=uid(1),
            edges=list(reversed(edges)),
        )
        self.assertEqual(first, second)


class TemplateRenderTests(unittest.TestCase):
    def test_validates_tokens_and_renders_empty_company_cleanly(self):
        self.assertEqual(
            unknown_tokens("[[job_title]] [[unknown]] [[projects]]"),
            {"unknown", "projects"},
        )
        nodes = {
            uid(1): GraphNode(
                uid(1),
                TemplateNodeKind.PHRASE,
                1,
                "Вакансия [[job_title]] в [[company_name]].",
            ),
            uid(2): GraphNode(uid(2), TemplateNodeKind.PROJECTS),
        }
        text = render_path(
            path=[uid(1), uid(2)],
            nodes=nodes,
            context=RenderContext(
                "Backend Developer",
                None,
                ("Python",),
                (
                    DomainProject(1, "API", ("Python", "FastAPI")),
                    DomainProject(2, "Site"),
                ),
            ),
        )
        self.assertEqual(
            text,
            "Вакансия Backend Developer в.\n\n«API» — Python, FastAPI.\n«Site».",
        )

    def test_empty_blocks_are_removed(self):
        node = GraphNode(uid(1), TemplateNodeKind.PHRASE, 1, "[[company_name]]")
        self.assertEqual(
            render_path(
                path=[uid(1)],
                nodes={uid(1): node},
                context=RenderContext("", None, (), ()),
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
