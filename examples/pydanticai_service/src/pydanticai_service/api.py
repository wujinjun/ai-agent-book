"""FastAPI adapter with explicit and stable error mapping."""

from fastapi import FastAPI, HTTPException

from pydanticai_service.domain import (
    DependencyUnavailable,
    ErrorBody,
    InvalidAgentResult,
    PolicyDenied,
    SupportReport,
    SupportRequest,
)
from pydanticai_service.providers import Scenario, build_fixture_model
from pydanticai_service.service import SupportService


def create_app(service: SupportService, *, scenario: Scenario = "happy") -> FastAPI:
    app = FastAPI(title="PydanticAI Support Service", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/v1/support",
        response_model=SupportReport,
        responses={
            403: {"model": ErrorBody},
            422: {"model": ErrorBody},
            503: {"model": ErrorBody},
            504: {"model": ErrorBody},
        },
    )
    async def support(request: SupportRequest) -> SupportReport:
        try:
            return await service.answer(request, model=build_fixture_model(scenario))
        except PolicyDenied as exc:
            raise HTTPException(403, detail={"code": "policy_denied", "message": str(exc)}) from exc
        except InvalidAgentResult as exc:
            raise HTTPException(
                422,
                detail={"code": "invalid_agent_result", "message": str(exc)},
            ) from exc
        except DependencyUnavailable as exc:
            raise HTTPException(
                503, detail={"code": "dependency_unavailable", "message": str(exc)}
            ) from exc
        except TimeoutError as exc:
            raise HTTPException(
                504,
                detail={"code": "timeout", "message": "request timed out"},
            ) from exc

    return app
