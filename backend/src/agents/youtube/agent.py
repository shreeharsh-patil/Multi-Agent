import json
import re
from src.agents.base import BaseAgent, AgentManifest, AgentResult

class YouTubeAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="youtube",
            name="YouTube Agent",
            description="Searches YouTube videos and content",
            icon="Youtube",
            capabilities=["search_videos"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.youtube.service import youtube_service

        token = context.get("google_access_token", "")
        refresh_token = context.get("google_refresh_token", "")
        if not token and context.get("user_id"):
            from src.adk.tools import find_user_access_token
            token = await find_user_access_token(context["user_id"])

        if not token:
            return AgentResult(success=False, output="Connect Google in Settings to search YouTube.", error="missing_youtube_token")

        extraction = await llm_service.generate(
            prompt=user_input,
            system_instruction="Extract YouTube search query into JSON key 'query'.",
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            query = json.loads(match.group(0) if match else extraction).get("query", user_input)
        except Exception:
            query = user_input

        try:
            videos = await youtube_service.search_videos(token, query, max_results=5, refresh_token=refresh_token)
            if not videos:
                return AgentResult(success=True, output=f"No videos found for '{query}'.")
            lines = [f"### YouTube Search Results for '{query}'\n"]
            for v in videos:
                lines.append(f"- **[{v['title']}]({v['link']})**\n  *Channel: {v['channel']}*\n")
            return AgentResult(success=True, output="\n".join(lines))
        except Exception as exc:
            return AgentResult(success=False, output=f"YouTube search failed: {exc}", error=str(exc))
