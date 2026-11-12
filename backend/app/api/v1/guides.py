"""API de guías con autorización por proyecto y protección CSRF."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, SettingsDep, require_csrf
from app.schemas.guide import GuideCreate, GuideList, GuideProgress, GuideRead
from app.services.guides import GuideService

router = APIRouter(prefix="/projects/{project_id}/guides", tags=["guides"])


@router.get("", response_model=GuideList)
async def list_guides(
    project_id: UUID, user: CurrentUser, db: DbSession, settings: SettingsDep
) -> GuideList:
    return await GuideService(db, settings.guide_embedding_revision).list(user.id, project_id)


@router.post("", response_model=GuideRead, status_code=202, dependencies=[Depends(require_csrf)])
async def create_guide(
    project_id: UUID, payload: GuideCreate, user: CurrentUser, db: DbSession, settings: SettingsDep
) -> GuideRead:
    return await GuideService(db, settings.guide_embedding_revision).create(
        user.id, project_id, payload.image_id
    )


@router.get("/{guide_id}", response_model=GuideRead)
async def read_guide(
    project_id: UUID, guide_id: UUID, user: CurrentUser, db: DbSession, settings: SettingsDep
) -> GuideRead:
    return await GuideService(db, settings.guide_embedding_revision).read(
        user.id, project_id, guide_id
    )


@router.post("/{guide_id}/cancel", response_model=GuideRead, dependencies=[Depends(require_csrf)])
async def cancel_guide(
    project_id: UUID, guide_id: UUID, user: CurrentUser, db: DbSession, settings: SettingsDep
) -> GuideRead:
    return await GuideService(db, settings.guide_embedding_revision).cancel(
        user.id, project_id, guide_id
    )


@router.put(
    "/{guide_id}/steps/{step_id}/progress",
    response_model=GuideRead,
    dependencies=[Depends(require_csrf)],
)
async def update_progress(
    project_id: UUID,
    guide_id: UUID,
    step_id: UUID,
    payload: GuideProgress,
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
) -> GuideRead:
    return await GuideService(db, settings.guide_embedding_revision).progress(
        user.id, project_id, guide_id, step_id, payload
    )
