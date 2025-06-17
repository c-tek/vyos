from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Role, Permission, UserRoleAssignment

async def create_role(db: AsyncSession, name: str, description: str, permissions: list[str]):
    role = Role(name=name, description=description, permissions=','.join(permissions))
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role

async def get_role_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()

async def list_roles(db: AsyncSession):
    result = await db.execute(select(Role))
    return result.scalars().all()

async def assign_role_to_user(db: AsyncSession, user_id: int, role_id: int):
    assignment = UserRoleAssignment(user_id=user_id, role_id=role_id)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment

# ...more CRUD for permissions and assignments as needed...
