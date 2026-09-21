"""One-shot command: ``python -m app.commands.provision_default_templates``."""

import asyncio

from sqlmodel import select

from app.database import async_session_maker
from app.models import User
from app.services.default_template_provisioner import DefaultTemplateProvisioner


async def provision_all_users() -> tuple[int, int]:
    created = 0
    skipped = 0
    async with async_session_maker() as session:
        user_ids = list(
            (await session.scalars(select(User.id).order_by(User.id))).all()
        )
        provisioner = DefaultTemplateProvisioner(session)
        for user_id in user_ids:
            if await provisioner.ensure_for_user(user_id):
                created += 1
            else:
                skipped += 1
    return created, skipped


if __name__ == "__main__":
    result = asyncio.run(provision_all_users())
    print(f"Provisioned: {result[0]}; skipped: {result[1]}")
