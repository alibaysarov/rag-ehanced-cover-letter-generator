from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from app.models import CVChunk


class CVChunkRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def replace_chunks(
        self,
        user_id: int,
        source_id: str,
        chunks: list[str],
    ) -> int:
        await self.delete_by_source_id(source_id)
        items = [
            CVChunk(
                user_id=user_id,
                source_id=source_id,
                chunk_index=index,
                text=chunk,
            )
            for index, chunk in enumerate(chunks)
        ]
        self._session.add_all(items)
        await self._session.flush()
        return len(items)

    async def delete_by_source_id(self, source_id: str) -> None:
        await self._session.execute(
            delete(CVChunk).where(CVChunk.source_id == str(source_id))
        )

    async def search_by_source_id(
        self,
        source_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[CVChunk]:
        rank = func.ts_rank_cd(
            func.to_tsvector("simple", CVChunk.text),
            func.plainto_tsquery("simple", query),
        ).label("rank")

        statement = (
            select(CVChunk, rank)
            .where(CVChunk.source_id == str(source_id))
            .order_by(rank.desc(), CVChunk.chunk_index.asc())
            .limit(top_k)
        )
        result = await self._session.execute(statement)
        rows = result.all()
        ranked = [row[0] for row in rows if row[1] and row[1] > 0]
        if ranked:
            return ranked

        fallback = (
            select(CVChunk)
            .where(CVChunk.source_id == str(source_id))
            .order_by(CVChunk.chunk_index.asc())
            .limit(top_k)
        )
        result = await self._session.execute(fallback)
        return list(result.scalars().all())
