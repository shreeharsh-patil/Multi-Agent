import json
import re

from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.utils.logger import logger


class ContactsAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="contacts",
            name="Contacts Agent",
            description="Lists, searches, and fetches Google Contacts details including emails and phone numbers",
            icon="Users",
            capabilities=["list_contacts", "search_contacts", "contact_details"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.contacts.service import contacts_service

        token = context.get("google_access_token", "")
        refresh_token = context.get("google_refresh_token", "")
        if not token and context.get("user_id"):
            from src.adk.tools import find_user_access_token
            token = await find_user_access_token(context["user_id"])

        if not token:
            return AgentResult(
                success=True,
                output=(
                    "📇 **Google Contacts Integration Available**\n\n"
                    "I can search and list your Google Contacts, retrieve email addresses, phone numbers, and company details!\n\n"
                    "To enable Contacts access:\n"
                    "1. Open **Settings → Integrations** in the sidebar menu.\n"
                    "2. Click **Connect Google Account**.\n"
                    "3. Once connected, ask me anytime to find contact details or email addresses!"
                ),
                error="missing_google_contacts_token",
            )

        extraction = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Google Contacts command parser. Return ONLY valid JSON with keys: action, query. "
                "action must be one of: list, search. "
                "Set query to the contact name, email, or keyword mentioned by the user (if any). "
                "Do not include markdown explanation."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except Exception:
            command = {"action": "list", "query": ""}

        query = (command.get("query") or "").strip()

        # Fallback check if user input contains a name or email request
        if not query and any(w in user_input.lower() for w in ["contact", "contacts", "email of", "number of", "phone of", "who is", "find"]):
            name_match = re.search(r"(?:for|of|named|contact|who is)\s+([a-zA-Z0-9_\- ]+)", user_input, re.IGNORECASE)
            if name_match:
                query = name_match.group(1).strip()

        try:
            contacts = await contacts_service.list_contacts(token, refresh_token=refresh_token, query=query)
            if not contacts:
                # If query is general QA or document context, fallback to answering directly
                if context.get("conversation_history") or any(w in user_input.lower() for w in ["principal", "college", "university", "school", "director", "president", "who is"]):
                    try:
                        fallback = await llm_service.generate(
                            prompt=user_input,
                            system_instruction="Answer the user's question accurately using conversation context and general knowledge. Do not talk about address books or personal contacts unless explicitly relevant.",
                        )
                        if fallback and len(fallback.strip()) > 5:
                            return AgentResult(success=True, output=fallback)
                    except Exception as err:
                        logger.warning(f"ContactsAgent fallback failed: {err}")
                msg = f'No contacts found matching "{query}".' if query else "Your Google Contacts list is empty."
                return AgentResult(success=True, output=msg)

            header_suffix = f' matching "{query}"' if query else ''
            lines = [f"### Google Contacts{header_suffix}:\n"]
            for c in contacts:
                details = [f"- **{c['name']}**"]
                if c.get("email"):
                    details.append(f"  - **Email:** `{c['email']}`")
                if c.get("phone"):
                    details.append(f"  - **Phone:** `{c['phone']}`")
                if c.get("company"):
                    details.append(f"  - **Company:** {c['company']}")
                lines.append("\n".join(details))

            return AgentResult(success=True, output="\n\n".join(lines))
        except Exception as exc:
            logger.error(f"Contacts agent error: {exc}")
            return AgentResult(success=False, output=f"Contacts action failed: {exc}", error=str(exc))
