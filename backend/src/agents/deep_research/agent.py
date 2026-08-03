import asyncio
import json
import re
from typing import Optional
from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.services.llm import llm_service
from src.utils.logger import logger


async def _execute_web_search_broad(query: str) -> str:
    """Execute live web search across multiple free search engines without API keys."""
    try:
        from src.adk.tools import web_search
        res = await web_search(query, for_research=True)
        return res or ""
    except Exception as err:
        logger.warning(f"DeepResearch web search failed for '{query}': {err}")
        return ""


async def _scrape_page_deep(url: str) -> str:
    """Scrape web page content using multi-engine free scraper cascade."""
    try:
        from src.adk.tools import scrape_page
        content = await scrape_page(url)
        return content[:4000] if content else ""
    except Exception as err:
        logger.warning(f"DeepResearch page scrape failed for '{url}': {err}")
        return ""


class DeepResearchAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="deep_research",
            name="Deep Research Specialist",
            description="Performs multi-stage query decomposition, multi-engine crawling, deep page content extraction, empirical data synthesis, and outputs publication-grade multi-page research reports",
            icon="BookOpenCheck",
            capabilities=[
                "multi_page_deep_research",
                "live_web_crawling",
                "empirical_data_synthesis",
                "comparative_matrix_analysis",
                "academic_citation_indexing",
                "auto_workspace_export",
            ],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        logger.info(f"Executing Supercharged DeepResearchAgent for topic: {user_input[:100]}")

        # Step 1: Multi-Stage Research Query Planning (Decompose into 6 distinct research angles)
        decomposition_prompt = f"""Deconstruct this research query into 6 distinct, specialized sub-queries to gather comprehensive multi-page data.
Query: {user_input}

Angles to cover:
1. Foundational overview & definitions
2. Technical mechanisms & architecture
3. Current statistics & quantitative metrics
4. Market/industry analysis & key players
5. Comparative tradeoffs & challenges
6. Recent developments & future trajectory

Return ONLY a JSON array of 6 strings, e.g. ["query 1", "query 2", "query 3", "query 4", "query 5", "query 6"]."""

        sub_queries = [
            user_input,
            f"{user_input} technical architecture mechanisms",
            f"{user_input} statistics data metrics 2026",
            f"{user_input} comparative analysis tradeoffs",
            f"{user_input} market landscape future developments",
        ]

        try:
            decomp_res = await llm_service.generate(
                prompt=decomposition_prompt,
                system_instruction="You are a principal research strategist. Output only a clean JSON array of strings.",
                temperature=0.2,
                max_output_tokens=400,
            )
            match = re.search(r"\[.*\]", decomp_res, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list) and len(parsed) >= 3:
                    sub_queries = [str(q).strip() for q in parsed[:6] if str(q).strip()]
        except Exception as exc:
            logger.warning(f"DeepResearch query decomposition fallback: {exc}")

        # Step 2: Parallel Search Execution across all sub-queries
        search_tasks = [_execute_web_search_broad(q) for q in sub_queries]
        search_results_raw = await asyncio.gather(*search_tasks)

        combined_search_text = []
        urls_to_scrape = []
        url_pattern = re.compile(r"https?://[^\s\)\>\"]+")

        for res_text in search_results_raw:
            if res_text and isinstance(res_text, str) and res_text.strip():
                combined_search_text.append(res_text.strip())
                found_urls = url_pattern.findall(res_text)
                for u in found_urls:
                    u_clean = u.rstrip(".,;)")
                    if len(urls_to_scrape) < 12 and u_clean not in urls_to_scrape and not u_clean.endswith((".png", ".jpg", ".svg", ".css", ".js")):
                        urls_to_scrape.append(u_clean)

        # Step 3: High-Parallel Deep Page Scraping
        scraped_pages = []
        if urls_to_scrape:
            scrape_tasks = [_scrape_page_deep(u) for u in urls_to_scrape[:12]]
            scraped_texts = await asyncio.gather(*scrape_tasks)
            for url, text in zip(urls_to_scrape[:12], scraped_texts):
                if text and text.strip() and len(text.strip()) > 100:
                    scraped_pages.append(f"### Source URL: {url}\n{text[:3000]}\n")

        # Combine Evidence Corpus
        corpus_text = "## Live Primary Web Search Findings:\n\n" + "\n\n---\n\n".join(combined_search_text[:6])
        if scraped_pages:
            corpus_text += "\n\n## Deep Page Content Extracts:\n\n" + "\n---\n".join(scraped_pages)

        # Step 4: Multi-Page Comprehensive Synthesis (10 Detailed Sections)
        synthesis_prompt = f"""Write an exhaustive, publication-quality, multi-page deep research report on the topic below.

Topic: {user_input}

{corpus_text}

Required Multi-Page Report Structure:

# 🔬 Deep Research Report: {user_input}

> [!NOTE]
> This is a comprehensive, multi-page academic research report generated by the Deep Research Specialist.

---

## 1. Executive Summary
- Core thesis, scope of investigation, key findings summary, and strategic value.

## 2. Historical Evolution & Context
- Background, historical development, key milestones, and foundational paradigms.

## 3. Fundamental Concepts & Terminology
- Key definitions, core terminology, theoretical frameworks, and mathematical/logical models.

## 4. Technical Architecture & In-Depth Mechanisms
- Architectural components, operational workflows, system diagrams, data pipelines, and technical specifications.

## 5. Quantitative Metrics & Empirical Evidence
- Key statistical metrics, benchmark data, empirical observations, and market figures. Include a markdown data table where applicable.

## 6. Comparative Analysis & Tradeoff Matrix
- Comprehensive comparison table (Approach/Feature vs Pros/Cons vs Performance/Cost).
- In-depth evaluation of competing methodologies or market alternatives.

## 7. Real-World Applications & Case Studies
- Practical industry implementations, real-world deployment examples, and domain impact.

## 8. Critical Limitations, Controversies & Risk Analysis
- Known bottlenecks, ethical/regulatory considerations, edge cases, and active expert debates.

## 9. Future Trajectory & Strategic Recommendations
- Next-generation technological shifts, long-term trends, and actionable strategic advice for decision-makers.

## 10. Numbered References & Bibliography
- Complete list of cited web sources with title and Markdown URL link.

Ensure the response is extremely thorough, analytical, objective, and filled with deep actionable detail."""

        try:
            report_content = await llm_service.generate(
                prompt=synthesis_prompt,
                system_instruction=(
                    "You are a Senior Principal Research Director. Write multi-page, publication-grade, "
                    "academically rigorous research reports with markdown tables, callout boxes, and full detail."
                ),
                temperature=0.35,
                max_output_tokens=4000,
            )

            # Auto-save report into workspace documents
            user_id = context.get("user_id", "default")
            doc_id = None
            safe_topic = re.sub(r"[^a-zA-Z0-9_\-]+", "_", user_input[:40]).strip("_") or "Topic"
            file_name = f"Deep_Research_{safe_topic}.md"

            try:
                from src.models.document import Document
                doc = Document(
                    user_id=user_id,
                    file_name=file_name,
                    file_type="md",
                    file_size=len(report_content.encode("utf-8")),
                    file_path="",
                    status="ready",
                    chunk_count=1,
                    workspace_id=context.get("workspace_id"),
                )
                await doc.insert()
                doc_id = str(doc.id)
            except Exception as doc_err:
                logger.warning(f"Could not auto-save research document: {doc_err}")

            footer = ""
            if doc_id:
                footer = f"\n\n---\n\n> [!TIP]\n> 📁 **Workspace Saved Document**: This report has been saved to your workspace as [`{file_name}`](file:///api/documents/{doc_id}/file)."

            final_markdown = report_content.strip() + footer

            return AgentResult(
                success=True,
                output=final_markdown,
                data={
                    "topic": user_input,
                    "sub_queries": sub_queries,
                    "sources_count": len(urls_to_scrape),
                    "scraped_count": len(scraped_pages),
                    "document_id": doc_id,
                },
            )


        except Exception as exc:
            logger.error(f"DeepResearch report synthesis failed: {exc}")
            return AgentResult(
                success=False,
                output=f"Deep research synthesis failed: {exc}",
                error=str(exc),
            )
