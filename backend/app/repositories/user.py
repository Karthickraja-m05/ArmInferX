"""User repository implementation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import UserRecord
from backend.app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserRecord, session)

    async def get_by_email(self, email: str) -> UserRecord | None:
        """Fetch user by unique email address."""
        query = select(UserRecord).where(UserRecord.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
