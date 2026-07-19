import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.middleware import resolve_user_id
from src.models.prompt_template import PromptTemplate, PromptTemplateVersion


router = APIRouter(prefix="/api/templates", tags=["Prompt Templates"])
VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*}}")


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="General", max_length=80)
    tags: list[str] = Field(default_factory=list)
    content: str = Field(min_length=1, max_length=30000)
    change_note: str = "Initial version"


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = None
    content: str = Field(min_length=1, max_length=30000)
    change_note: str = "Updated prompt"


class RestoreInput(BaseModel):
    version: int


class RenderInput(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


def variables_in(content: str) -> list[str]:
    return list(dict.fromkeys(VARIABLE_PATTERN.findall(content)))


def serialize_template(template: PromptTemplate, include_versions: bool = False) -> dict:
    current = next((v for v in template.versions if v.version == template.current_version), template.versions[-1])
    value = {
        "id": str(template.id), "name": template.name, "description": template.description,
        "category": template.category, "tags": template.tags, "currentVersion": template.current_version,
        "content": current.content, "variables": current.variables,
        "createdAt": template.created_at.isoformat(), "updatedAt": template.updated_at.isoformat(),
    }
    if include_versions:
        value["versions"] = [{
            "version": version.version, "content": version.content, "variables": version.variables,
            "changeNote": version.change_note, "createdAt": version.created_at.isoformat(),
        } for version in reversed(template.versions)]
    return value


async def owned_template(template_id: str, user_id: str) -> PromptTemplate:
    template = await PromptTemplate.get(template_id)
    if not template or template.user_id != user_id:
        raise HTTPException(404, "Template not found")
    return template


@router.get("")
async def list_templates(request: Request) -> list[dict]:
    templates = await PromptTemplate.find(PromptTemplate.user_id == resolve_user_id(request)).sort(-PromptTemplate.updated_at).to_list()
    return [serialize_template(template) for template in templates]


@router.post("")
async def create_template(request: Request, body: TemplateCreate) -> dict:
    now = datetime.now(timezone.utc)
    version = PromptTemplateVersion(version=1, content=body.content, variables=variables_in(body.content), change_note=body.change_note, created_at=now)
    template = PromptTemplate(
        user_id=resolve_user_id(request), name=body.name.strip(), description=body.description.strip(),
        category=body.category.strip() or "General", tags=body.tags[:20], versions=[version],
        created_at=now, updated_at=now,
    )
    await template.insert()
    return serialize_template(template, True)


@router.get("/{template_id}")
async def get_template(template_id: str, request: Request) -> dict:
    return serialize_template(await owned_template(template_id, resolve_user_id(request)), True)


@router.put("/{template_id}")
async def update_template(template_id: str, request: Request, body: TemplateUpdate) -> dict:
    template = await owned_template(template_id, resolve_user_id(request))
    if body.name is not None and body.name.strip():
        template.name = body.name.strip()
    if body.description is not None:
        template.description = body.description.strip()
    if body.category is not None:
        template.category = body.category.strip() or "General"
    if body.tags is not None:
        template.tags = body.tags[:20]
    next_version = template.current_version + 1
    template.versions.append(PromptTemplateVersion(
        version=next_version, content=body.content, variables=variables_in(body.content), change_note=body.change_note,
    ))
    template.current_version = next_version
    template.updated_at = datetime.now(timezone.utc)
    await template.save()
    return serialize_template(template, True)


@router.post("/{template_id}/restore")
async def restore_template(template_id: str, request: Request, body: RestoreInput) -> dict:
    template = await owned_template(template_id, resolve_user_id(request))
    source = next((version for version in template.versions if version.version == body.version), None)
    if not source:
        raise HTTPException(404, "Template version not found")
    next_version = template.current_version + 1
    template.versions.append(PromptTemplateVersion(
        version=next_version, content=source.content, variables=source.variables,
        change_note=f"Restored version {source.version}",
    ))
    template.current_version = next_version
    template.updated_at = datetime.now(timezone.utc)
    await template.save()
    return serialize_template(template, True)


@router.post("/{template_id}/render")
async def render_template(template_id: str, request: Request, body: RenderInput) -> dict:
    template = await owned_template(template_id, resolve_user_id(request))
    current = next(version for version in template.versions if version.version == template.current_version)
    missing = [variable for variable in current.variables if not body.values.get(variable, "").strip()]
    if missing:
        raise HTTPException(400, f"Missing values: {', '.join(missing)}")
    rendered = VARIABLE_PATTERN.sub(lambda match: body.values.get(match.group(1), match.group(0)), current.content)
    return {"content": rendered, "version": current.version}


@router.delete("/{template_id}")
async def delete_template(template_id: str, request: Request) -> dict:
    template = await owned_template(template_id, resolve_user_id(request))
    await template.delete()
    return {"deleted": True}

