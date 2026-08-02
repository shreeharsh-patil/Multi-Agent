from src.agents.base import BaseAgent, AgentManifest, AgentResult


class HackerAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="hacker",
            name="Cyber & Security Agent",
            description="Cybersecurity study tutor: networks, encryption, ethical hacking, defense for students",
            icon="Shield",
            capabilities=["cybersecurity", "networking", "cryptography", "ethical_hacking", "defense"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live cybersecurity source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a cybersecurity tutor helping cybersecurity and computer-science students learn the "
                "field the way a great professor would. Cover computer networking, operating-system security, "
                "cryptography, web-app security, common vulnerabilities (OWASP), secure coding, and ethical "
                "hacking / penetration-testing concepts and methodology.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the concept and mechanism first, then real-world examples and defense mitigations.\n"
                "- Use headings, bullet points, and tables; include step-by-step methodology (e.g., recon, "
                "scanning, enumeration, exploitation, privilege escalation, reporting) for exam-style answers.\n"
                "- Bold high-yield terms and add mnemonics and exam notes where helpful.\n"
                "ETHICS & SAFETY: Explain offensive techniques only for legitimate study, certification, or "
                "authorized pen-testing lab contexts. Remind students never to test systems without explicit "
                "authorization. Do not provide instructions, scripts, or one-click gone-bad steps for hacking "
                "real systems without authorization.\n"
                "Use the provided live course evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)