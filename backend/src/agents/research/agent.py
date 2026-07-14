from src.agents.base import BaseAgent, AgentManifest, AgentResult


class ResearchAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="research",
            name="Research Agent",
            description="Internet search, source comparison, report generation, citations",
            icon="Search",
            capabilities=["web_search", "source_comparison", "report_generation", "citations"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Research Agent. Conduct thorough research, compare multiple sources, "
                "and generate comprehensive reports with proper citations. "
                "Structure reports with: abstract, methodology, findings, analysis, conclusions, references."
            ),
        )
        return AgentResult(success=True, output=response)

    async def deep_research(self, query: str) -> dict:
        """Run a bounded research loop with one deliberate follow-up pass."""
        import re
        from src.adk.tools import web_search, scrape_page
        from src.services.llm import llm_service

        stages = []
        plan = await llm_service.generate(
            prompt=query,
            system_instruction=(
                "You are a senior research planner. Create a concise investigation plan for the topic. "
                "List the questions to answer, source types to seek, and signals of credible evidence."
            ),
        )
        stages.append({"id": "plan", "label": "Research plan", "detail": "Defined questions and source strategy"})

        initial_search = await web_search(f"{query}\nResearch plan:\n{plan}")
        stages.append({"id": "search", "label": "Initial search", "detail": "Collected broad evidence and candidate sources"})
        urls = []
        for url in re.findall(r"https?://[^\s)<>]+", initial_search):
            clean = url.rstrip(".,;\"'")
            if clean not in urls:
                urls.append(clean)
        urls = urls[:3]

        scraped_sources = []
        for url in urls:
            content = await scrape_page(url)
            scraped_sources.append({"url": url, "content": content[:9000]})
        stages.append({"id": "sources", "label": "Source review", "detail": f"Read {len(scraped_sources)} primary pages"})

        source_block = "\n\n".join(f"SOURCE {i + 1}: {s['url']}\n{s['content']}" for i, s in enumerate(scraped_sources))
        draft = await llm_service.generate(
            prompt=f"Topic: {query}\n\nPlan:\n{plan}\n\nSearch results:\n{initial_search[:10000]}\n\nScraped sources:\n{source_block}",
            system_instruction=(
                "You are a research analyst. Synthesize a factual draft, distinguish evidence from inference, "
                "and explicitly list unanswered questions or weakly supported claims under INFORMATION GAPS."
            ),
        )
        stages.append({"id": "draft", "label": "Draft synthesis", "detail": "Compared evidence and identified gaps"})

        gaps = await llm_service.generate(
            prompt=draft,
            system_instruction=(
                "Extract the most important information gaps that could materially change the answer. "
                "Return 3 or fewer concise search questions. If the draft is complete, return COMPLETE."
            ),
        )
        follow_up = ""
        if "COMPLETE" not in gaps.upper():
            follow_up = await web_search(f"Follow-up research for {query}: {gaps}")
            stages.append({"id": "followup", "label": "Gap search", "detail": "Ran a targeted secondary search"})
        else:
            stages.append({"id": "followup", "label": "Gap search", "detail": "No material gaps required a second search"})

        final = await llm_service.generate(
            prompt=(
                f"Research topic: {query}\n\nPLAN:\n{plan}\n\nDRAFT:\n{draft}\n\n"
                f"INFORMATION GAPS:\n{gaps}\n\nFOLLOW-UP EVIDENCE:\n{follow_up[:10000]}\n\n"
                f"SOURCE URLS:\n{chr(10).join(urls)}"
            ),
            system_instruction=(
                "You are a publication-grade research editor. Produce a rigorous Markdown report with: "
                "title, executive summary, methodology, key findings, detailed analysis, limitations, conclusion, "
                "and a numbered bibliography. Cite claims inline as [1], [2], etc. Only cite sources present in the "
                "provided evidence, clearly mark uncertainty, and never invent URLs or statistics."
            ),
        )
        stages.append({"id": "final", "label": "Final report", "detail": "Published Markdown with bibliography"})
        return {"output": final, "stages": stages, "sources": urls}
