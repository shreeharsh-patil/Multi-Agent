from src.agents.base import BaseAgent, AgentManifest, AgentResult


class CodingAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="coding",
            name="Coding Agent",
            description="Code writing, explanation, debugging, and documentation",
            icon="FileCode",
            capabilities=["code_generation", "code_explanation", "debugging", "documentation"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        import re
        from src.services.llm import llm_service

        is_img_prompt = bool(
            re.search(r"(?i)\b(generate|create|draw|make|design|render|paint|show|produce)\b.*\b(image|picture|photo|photograph|illustration|drawing|artwork|poster|logo|icon|graphic|banner|vector|avatar)\b", user_input)
            or re.search(r"(?i)\b(image|picture|photo|drawing|illustration)\b\s+(of|for|with|showing|featuring)\b", user_input)
        ) and not any(w in user_input.lower() for w in ["code", "script", "python", "html", "svg code", "canvas code"])

        if is_img_prompt:
            from src.services.image_generation import generate_and_store_image
            user_id = context.get("user_id", "default")
            workspace_id = context.get("workspace_id")
            drive_token = context.get("google_access_token")
            drive_refresh = context.get("google_refresh_token")
            try:
                img = await generate_and_store_image(
                    prompt=user_input,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    drive_access_token=drive_token,
                    drive_refresh_token=drive_refresh,
                )
                output = f"![Generated image]({img.download_url})"
                if img.revised_prompt and img.revised_prompt != user_input:
                    output += f"\n\n*Prompt used: {img.revised_prompt}*"
                return AgentResult(success=True, output=output)
            except Exception as err:
                logger.warning(f"Image generation fallback in CodingAgent failed: {err}")

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Coding Agent. Write clean, well-documented code. "
                "Support multiple programming languages. Explain code logic, help debug issues, "
                "and generate documentation. Always follow best practices.\n\n"
                "When generating HTML/CSS/JS code, always use markdown code blocks "
                "with the language specified (e.g. ```html, ```css, ```js). "
                "The platform automatically detects these blocks and renders a live preview."
            ),
        )
        return AgentResult(success=True, output=response)
