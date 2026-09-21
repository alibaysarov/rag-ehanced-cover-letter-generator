import unittest
import uuid
from datetime import datetime

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.api.v1.endpoints.letter_constructor import router
from app.core.config import settings
from app.database import get_db
from app.helper.user import get_current_user
from app.models import User
from app.schemas.api.user import AuthenticatedUser


@unittest.skipUnless(settings.DATABASE_URL, "DATABASE_URL is required")
class LetterConstructorApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = f"constructor_api_{uuid.uuid4().hex}"
        self.admin_engine = create_async_engine(settings.DATABASE_URL)
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            users = [
                User(email="owner@example.test", password_hash="test"),
                User(email="other@example.test", password_hash="test"),
            ]
            session.add_all(users)
            await session.commit()
            self.user_ids = [user.id for user in users]

        self.current_user_id = self.user_ids[0]
        app = FastAPI()
        app.include_router(router)

        async def override_db():
            async with self.sessions() as session:
                yield session

        async def override_user():
            index = self.user_ids.index(self.current_user_id)
            email = ("owner@example.test", "other@example.test")[index]
            now = datetime.utcnow()
            return AuthenticatedUser(
                id=self.current_user_id,
                email=email,
                password_hash="test",
                is_active=True,
                is_verified=False,
                created_at=now,
                updated_at=now,
            )

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        await self.admin_engine.dispose()

    async def create_phrase(self, text_value="Hello [[job_title]]"):
        response = await self.client.post(
            "/letter-phrases",
            json={"type": "opening", "text": text_value, "is_active": True},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_phrase_crud_filters_pagination_and_owner_isolation(self):
        first = await self.create_phrase("First [[job_title]]")
        await self.create_phrase("Second")
        response = await self.client.get(
            "/letter-phrases",
            params={"q": "first", "type": "opening", "page": 1, "page_size": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["items"][0]["id"], first["id"])

        updated = await self.client.patch(
            f"/letter-phrases/{first['id']}", json={"text": "Changed"}
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["text"], "Changed")

        self.current_user_id = self.user_ids[1]
        hidden = await self.client.get(f"/letter-phrases/{first['id']}")
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json()["detail"]["code"], "phrase_not_found")
        self.current_user_id = self.user_ids[0]

        invalid = await self.client.post(
            "/letter-phrases",
            json={"type": "custom", "text": "[[projects]]", "is_active": True},
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["detail"]["code"], "invalid_phrase")

        deleted = await self.client.delete(f"/letter-phrases/{first['id']}")
        self.assertEqual(deleted.status_code, 204)

    async def test_template_confirmation_activation_conflicts_and_stale_version(self):
        phrase = await self.create_phrase()
        node_id = str(uuid.uuid4())
        payload = {
            "name": "No portfolio",
            "case": "no_portfolio",
            "confirm_without_projects": False,
            "root_node_id": node_id,
            "nodes": [
                {
                    "id": node_id,
                    "node_kind": "phrase",
                    "phrase_id": phrase["id"],
                    "position": {"x": 10, "y": 20},
                }
            ],
            "edges": [],
        }
        created = await self.client.post("/cover-letter-templates", json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        template = created.json()

        activated = await self.client.post(
            f"/cover-letter-templates/{template['id']}/activate",
            json={"version": template["version"], "confirm_without_projects": False},
        )
        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertEqual(activated.json()["status"], "active")

        active_delete = await self.client.delete(
            f"/cover-letter-templates/{template['id']}"
        )
        self.assertEqual(active_delete.status_code, 409)
        self.assertEqual(active_delete.json()["detail"]["code"], "active_template")

        update_payload = {**payload, "version": template["version"]}
        updated = await self.client.put(
            f"/cover-letter-templates/{template['id']}", json=update_payload
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        stale_payload = {**payload, "version": template["version"]}
        stale = await self.client.put(
            f"/cover-letter-templates/{template['id']}", json=stale_payload
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["detail"]["code"], "stale_template_version")

        partial_payload = {
            **payload,
            "name": "Partial",
            "case": "partial_match",
            "root_node_id": str(uuid.uuid4()),
        }
        partial_payload["nodes"] = [
            {**payload["nodes"][0], "id": partial_payload["root_node_id"]}
        ]
        confirmation = await self.client.post(
            "/cover-letter-templates", json=partial_payload
        )
        self.assertEqual(confirmation.status_code, 422)
        self.assertEqual(
            confirmation.json()["detail"],
            {
                "code": "projects_node_confirmation_required",
                "reason": "missing_projects_node",
            },
        )
        partial_payload["confirm_without_projects"] = True
        confirmed = await self.client.post(
            "/cover-letter-templates", json=partial_payload
        )
        self.assertEqual(confirmed.status_code, 201, confirmed.text)

        self.current_user_id = self.user_ids[1]
        hidden = await self.client.get(f"/cover-letter-templates/{template['id']}")
        self.assertEqual(hidden.status_code, 404)


if __name__ == "__main__":
    unittest.main()
