from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.errors import NotFound
from app.models.mysql.meta_template import MetaTemplateRow
from app.schemas.meta_template import MetaTemplateDTO, MetaTemplateUpdateDTO
from app.tool_runtime.errors import MetaTemplateError

META_ID = 1


class MetaTemplateService:
    """元模板(单例 id=1)读写。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def get(self) -> MetaTemplateDTO:
        async with self._sf() as s:
            row = (
                await s.execute(
                    select(MetaTemplateRow).where(MetaTemplateRow.id == META_ID)
                )
            ).scalar_one_or_none()
            if row is None:
                raise NotFound("meta template not initialized (01.ddl 应已 INSERT)")
            return MetaTemplateDTO.model_validate(row.content)

    async def update(self, dto: MetaTemplateUpdateDTO, user_id: int) -> None:
        keys = [f.key for f in dto.content.fields]
        if len(set(keys)) != len(keys):
            raise MetaTemplateError("duplicate field key")
        if not all(k for k in keys):
            raise MetaTemplateError("empty field key")

        async with self._sf() as s:
            row = (
                await s.execute(
                    select(MetaTemplateRow).where(MetaTemplateRow.id == META_ID)
                )
            ).scalar_one_or_none()
            if row is None:
                s.add(
                    MetaTemplateRow(
                        id=META_ID,
                        content=dto.content.model_dump(),
                        note=dto.note,
                        updated_by=user_id,
                    )
                )
            else:
                await s.execute(
                    update(MetaTemplateRow)
                    .where(MetaTemplateRow.id == META_ID)
                    .values(
                        content=dto.content.model_dump(),
                        note=dto.note,
                        updated_by=user_id,
                    )
                )
            await s.commit()
