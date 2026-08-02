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
        """Run a deep-research loop with sub-question decomposition and parallel evidence gathering.

        Decomposes the topic into focused sub-questions, runs broad + per-sub-question web
        searches concurrently, scrapes the strongest primary sources, drafts a synthesis,
        hunts information gaps with a targeted follow-up, and publishes a cited Markdown report.
        """
        import re
        import asyncio
        from src.adk.tools import web_search, scrape_page
        from src.services.llm import llm_service

        stages = []
        sources_found = []

        # 1. Research plan
        plan = await llm_service.generate(
            prompt=query,
            system_instruction=(
                "You are a senior research planner. Create a concise investigation plan for the topic. "
                "List the questions to answer, source types to seek, and signals of credible evidence."
            ),
        )
        stages.append({"id": "plan", "label": "Research plan", "detail": "Defined questions and source strategy"})

        # 2. Sub-question decomposition
        subq = await llm_service.generate(
            prompt=query,
            system_instruction=(
                "Decompose the research topic into 3-4 distinct sub-questions whose combined answers fully "
                "cover the topic. Return them as a simple numbered list, one per line, with no other text."
            ),
        )
        sub_questions = [line.lstrip("0123456789.)- \t").strip() for line in subq.splitlines() if line.strip()]
        sub_questions = sub_questions[:4]
        if not sub_questions:
            sub_questions = [query]
        stages.append({
            "id": "subq",
            "label": "Sub-question decomposition",
            "detail": f"Split topic into {len(sub_questions)} focused angles",
        })

        # 3. Parallel evidence gathering — broad search + one search per sub-question
        async def run_search(question: str) -> str:
            return await web_search(f"{question}\nResearch plan context:\n{plan}", for_research=True)

        search_tasks = [run_search(query)] + [run_search(sq) for sq in sub_questions]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        search_block = "\n\n".join(
            f"=== SEARCH {'BROAD' if i == 0 else f'SUBQ {i}'} ===\n{res}"
            for i, res in enumerate(search_results)
            if isinstance(res, str)
        )
        stages.append({
            "id": "search",
            "label": "Parallel evidence gathering",
            "detail": f"Ran {len(search_tasks)} concurrent searches",
        })

        # 4. Extract URLs from all search results and scrape full content
        urls = []
        for url in re.findall(r"https?://[^\s)<>]+", search_block):
            clean = url.rstrip(".,;\"'")
            if clean not in urls:
                urls.append(clean)
        urls = urls[:5]

        scraped_sources = []
        for url in urls:
            content = await scrape_page(url)
            if content and "Error:" not in content:
                scraped_sources.append({"url": url, "content": content[:12000]})
                sources_found.append(url)
        stages.append({"id": "sources", "label": "Source review", "detail": f"Read {len(scraped_sources)} primary pages from {len(urls)} candidates"})

        # 5. Draft synthesis combining searches + scraped content
        source_block = "\n\n".join(
            f"SOURCE {i + 1}: {s['url']}\n{s['content']}"
            for i, s in enumerate(scraped_sources)
        )
        draft = await llm_service.generate(
            prompt=(
                f"Topic: {query}\n\n"
                f"Plan:\n{plan}\n\n"
                f"Sub-questions:\n{chr(10).join(f'- {sq}' for sq in sub_questions)}\n\n"
                f"Search results:\n{search_block[:16000]}\n\n"
                f"Scraped sources:\n{source_block}"
            ),
            system_instruction=(
                "You are a research analyst. Synthesize a factual draft organized by the sub-questions, "
                "distinguish evidence from inference, and explicitly list unanswered questions or weakly "
                "supported claims under INFORMATION GAPS."
            ),
        )
        stages.append({"id": "draft", "label": "Draft synthesis", "detail": "Compared evidence and identified gaps"})

        # 6. Identify information gaps and do a targeted follow-up search
        gaps = await llm_service.generate(
            prompt=draft,
            system_instruction=(
                "Extract the most important information gaps that could materially change the answer. "
                "Return 3 or fewer concise search questions. If the draft is complete, return COMPLETE."
            ),
        )
        follow_up = ""
        if "COMPLETE" not in gaps.upper():
            follow_up = await web_search(f"Follow-up research for {query}: {gaps}", for_research=True)
            stages.append({"id": "followup", "label": "Gap search", "detail": "Ran a targeted secondary search"})
        else:
            stages.append({"id": "followup", "label": "Gap search", "detail": "No material gaps required a second search"})

        # 7. Final publication-grade report
        final = await llm_service.generate(
            prompt=(
                f"Research topic: {query}\n\nPLAN:\n{plan}\n\nDRAFT:\n{draft}\n\n"
                f"INFORMATION GAPS:\n{gaps}\n\nFOLLOW-UP EVIDENCE:\n{follow_up[:12000]}\n\n"
                f"SOURCE URLS:\n{chr(10).join(sources_found)}"
            ),
            system_instruction=(
                "You are a publication-grade research editor. Produce a rigorous Markdown report with: "
                "title, executive summary, methodology, key findings, detailed analysis, limitations, conclusion, "
                "and a numbered bibliography. Cite claims inline as [1], [2], etc. Only cite sources present in the "
                "provided evidence, clearly mark uncertainty, and never invent URLs or statistics."
            ),
        )
        stages.append({"id": "final", "label": "Final report", "detail": "Published Markdown with bibliography"})
        return {"output": final, "stages": stages, "sources": sources_found}
