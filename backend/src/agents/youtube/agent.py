import json
import re
from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.utils.logger import logger


class YouTubeAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="youtube",
            name="YouTube Agent",
            description="Searches YouTube videos, channels, and educational playlists",
            icon="Youtube",
            capabilities=["search_videos", "youtube_channels"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.youtube.service import youtube_service

        token = context.get("google_access_token", "")
        refresh_token = context.get("google_refresh_token", "")
        if not token and context.get("user_id"):
            try:
                from src.adk.tools import find_user_access_token
                token = await find_user_access_token(context["user_id"])
            except Exception:
                token = ""

        query = user_input
        try:
            extraction = await llm_service.generate(
                prompt=user_input,
                system_instruction="Extract YouTube search query into JSON key 'query'.",
            )
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                query = parsed.get("query", user_input)
        except Exception:
            query = user_input

        videos = []
        try:
            videos = await youtube_service.search_videos(token, query, max_results=5, refresh_token=refresh_token)
        except Exception as exc:
            logger.warning(f"YouTube API execution failed: {exc}, using search recommendation fallback")

        if videos:
            lines = [f"### 📺 Top YouTube Search Results for '{query}'\n"]
            for v in videos:
                lines.append(f"- **[{v['title']}]({v['link']})**\n  *Channel: {v['channel']}*\n")
            return AgentResult(success=True, output="\n".join(lines))

        # Fallback: Synthesize top YouTube channel recommendations with active Markdown links
        fallback_prompt = (
            f"User Question: {user_input}\n\n"
            f"INSTRUCTIONS:\n"
            f"Provide a comprehensive, well-structured list of the best YouTube channels and playlists for this topic.\n"
            f"For GATE (Graduate Aptitude Test in Engineering) or exam preparation, list the top Indian YouTube channels "
            f"(e.g., Gate Smashers by Varun Singla, Neso Academy, Knowledge Gate by Sanchit Jain, Made Easy Official, Unacademy GATE, Amit Khurana).\n"
            f"Format with bold headings, channel descriptions, key subjects taught, and clickable YouTube channel links "
            f"[Channel Name](https://www.youtube.com/results?search_query=channel_name)."
        )
        synthesis = await llm_service.generate(
            prompt=fallback_prompt,
            system_instruction="You are YouTube Agent. Recommend top YouTube channels and playlists with active Markdown hyperlinks.",
        )
        return AgentResult(success=True, output=synthesis)
