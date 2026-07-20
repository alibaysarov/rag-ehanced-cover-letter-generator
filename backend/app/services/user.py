from app.repository.user_repository import UserRepository


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_user_by_email(self, email: str):
        user = await self.repo.get_user_by_email(email)
        if user is None:
            raise Exception("User not found")
        return user
