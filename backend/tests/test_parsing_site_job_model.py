import unittest

from sqlalchemy import UniqueConstraint

from app.models import AutoParsedJob, ParsingSiteJob


class ParsingSiteJobModelTests(unittest.TestCase):
    def test_site_job_has_required_columns_and_unique_site_per_job(self):
        columns = ParsingSiteJob.__table__.c

        self.assertEqual("pending", columns.status.default.arg)
        self.assertEqual(0, columns.total_found.default.arg)
        self.assertEqual(0, columns.saved_count.default.arg)
        self.assertEqual(0, columns.failed_count.default.arg)
        self.assertTrue(columns.parsing_job_id.index)
        self.assertIn(
            frozenset(("parsing_job_id", "site_key")),
            {
                frozenset(constraint.columns.keys())
                for constraint in ParsingSiteJob.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )

    def test_vacancies_are_unique_within_a_site_job_only(self):
        self.assertIn(
            frozenset(("parsing_site_job_id", "vacancy_id")),
            {
                frozenset(constraint.columns.keys())
                for constraint in AutoParsedJob.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            },
        )
        self.assertTrue(AutoParsedJob.__table__.c.parsing_site_job_id.nullable)


if __name__ == "__main__":
    unittest.main()
