"""Endpoints de registro, inicio y cierre de sesión."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.core.cookies import (
    CSRF_COOKIE,
    REFRESH_COOKIE,
    clear_auth_cookies,
    set_access_cookie,
    set_csrf_cookie,
    set_refresh_cookie,
)
from app.core.security import generate_csrf_token, is_valid_csrf_token
from app.schemas.auth import CsrfResponse, LoginRequest, RegisterRequest, UserRead
from app.services.auth import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _apply_session_cookies(response: Response, tokens: TokenPair) -> None:
    set_access_cookie(response, tokens.access_token)
    set_refresh_cookie(response, tokens.refresh_token)
    # El token CSRF se renueva en cada inicio de sesión para evitar fijación.
    set_csrf_cookie(response, tokens.csrf_token)


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.get("/csrf", response_model=CsrfResponse)
async def issue_csrf_token(request: Request, response: Response) -> CsrfResponse:
    """Entrega el token CSRF que el cliente debe reenviar en la cabecera.

    Si la cookie existente sigue siendo válida se reutiliza; si falta o está
    manipulada se emite una nueva.
    """
    current = request.cookies.get(CSRF_COOKIE)
    if current and is_valid_csrf_token(current):
        return CsrfResponse(csrf_token=current)

    token = generate_csrf_token()
    set_csrf_cookie(response, token)
    return CsrfResponse(csrf_token=token)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: DbSession,
) -> UserRead:
    service = AuthService(session)
    try:
        user, tokens = await service.register(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
            user_agent=_user_agent(request),
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo",
        ) from exc

    _apply_session_cookies(response, tokens)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=UserRead,
    dependencies=[Depends(require_csrf)],
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: DbSession,
) -> UserRead:
    service = AuthService(session)
    try:
        user, tokens = await service.login(
            email=payload.email,
            password=payload.password,
            user_agent=_user_agent(request),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        ) from exc

    _apply_session_cookies(response, tokens)
    return UserRead.model_validate(user)


@router.post(
    "/refresh",
    response_model=UserRead,
    dependencies=[Depends(require_csrf)],
)
async def refresh(
    request: Request,
    response: Response,
    session: DbSession,
) -> UserRead:
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no iniciada",
        )

    service = AuthService(session)
    try:
        user, tokens = await service.rotate(
            refresh_token=refresh_token,
            user_agent=_user_agent(request),
        )
    except InvalidRefreshTokenError as exc:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión caducada",
        ) from exc

    _apply_session_cookies(response, tokens)
    return UserRead.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def logout(request: Request, response: Response, session: DbSession) -> None:
    service = AuthService(session)
    await service.logout(refresh_token=request.cookies.get(REFRESH_COOKIE))
    clear_auth_cookies(response)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
