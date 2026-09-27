from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas.project import ProjectCreate, ProjectRead
from apps.api.services import projects as project_service

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    project = project_service.create_project(db, payload.name, payload.description)
    return ProjectRead.model_validate(project)


@router.post("/api/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_api_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    return ProjectRead.model_validate(project_service.create_project(db, payload.name, payload.description))


@router.get("/api/projects", response_model=list[ProjectRead])
def list_api_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return [ProjectRead.model_validate(project) for project in project_service.list_projects(db)]


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectRead:
    return ProjectRead.model_validate(project_service.get_project(db, project_id))


@router.get("/api/projects/{project_id}", response_model=ProjectRead)
def get_api_project(project_id: str, db: Session = Depends(get_db)) -> ProjectRead:
    return ProjectRead.model_validate(project_service.get_project(db, project_id))
