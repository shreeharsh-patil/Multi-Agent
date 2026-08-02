"""AI Study Agent Core Service.

Powers the complete AI Learning System:
- Multi-style note generation (Beginner, Exam, Detailed, Revision, Cheat Sheet)
- Reference understanding, citation extraction, & multi-document knowledge merging
- Knowledge graph construction & concept map extraction
- Formula derivation & step-by-step mathematical breakdowns (KaTeX)
- Automated Mermaid flowcharts & architectural diagrams
- Structured comparison tables (pros/cons, complexities, use cases)
- Memory techniques (mnemonics, analogies, story-based learning)
- Bloom's Taxonomy question generation & active learning suites
- 7 specialized learning modes (Teach me, ELI10, Professor, Research, Exam, Revision, Interview)
"""

import json
import re
from typing import Any, Dict, List, Optional
from src.services.llm.service import llm_service
from src.services.rag.retriever import get_retriever
from src.utils.logger import logger


LEARNING_MODE_PROMPTS: Dict[str, str] = {
    "teach_me": (
        "You are an expert Socratic tutor. Teach the user step-by-step. "
        "Break down complex concepts into intuitive pieces, ask engaging questions to test understanding, "
        "use clear analogies, provide visual Mermaid diagrams, and include solved examples."
    ),
    "eli10": (
        "You are a master educator explaining to a 10-year-old child. "
        "Use simple, relatable everyday analogies, fun stories, zero technical jargon without immediate explanation, "
        "and clear bullet points. Avoid complex math assumptions."
    ),
    "professor": (
        "You are a distinguished University Professor. Provide rigorous, academically complete explanations. "
        "Include formal definitions, historical context, step-by-step mathematical proofs or derivations using KaTeX, "
        "theoretical foundations, and citations to underlying research papers or textbook sections."
    ),
    "research": (
        "You are a Senior Principal AI & Systems Researcher. Analyze documents with deep technical scrutiny. "
        "Compare methodologies, evaluate trade-offs, identify open challenges, extract citations/references (DOIs/IEEE), "
        "and synthesize multi-paper findings into structured academic insights."
    ),
    "exam": (
        "You are a Top University Examiner and Exam Creator. Focus on high-yield exam material. "
        "Format responses into 2-mark, 5-mark, 8-mark, 10-mark, and 15-mark structured answers. "
        "Highlight exact definitions, critical formulas with units, key diagrams, common student mistakes, and scoring criteria."
    ),
    "revision": (
        "You are a Rapid Revision Coach. Provide ultra-concise, high-impact revision summaries. "
        "Use 1-page structured bullet points, key takeaways, formula cheat sheets, and quick mnemonics for last-minute review."
    ),
    "interview": (
        "You are a Staff Technical Interviewer at a top-tier tech firm. Frame explanations as technical interview questions. "
        "Cover core concepts, time/space complexity analysis, edge cases, trade-offs (e.g. system design choice A vs B), "
        "and step-by-step dry-run code explanations."
    ),
}


NOTE_STYLE_INSTRUCTIONS: Dict[str, str] = {
    "beginner": (
        "Create Beginner-Friendly Notes. Use simple language, real-world analogies, zero assumed prior knowledge, "
        "clear definitions for all terms, step-by-step walkthroughs, and simple illustrative Mermaid flowcharts."
    ),
    "exam": (
        "Create High-Scoring Exam Notes. Structure into clear point-wise sections with headings. "
        "Include important definitions, key formulas with units, university/GATE pattern 2/5/10 mark answers, "
        "common exam traps/mistakes, and high-yield scoring keywords."
    ),
    "detailed": (
        "Create Exhaustive Detailed Notes. Provide complete deep-dive explanations for every concept, "
        "step-by-step mathematical derivations using KaTeX math formatting ($...$ and $$...$$), architectural Mermaid diagrams, "
        "detailed comparison tables, real-world applications, and limitations."
    ),
    "revision": (
        "Create a 1-Page Rapid Revision Guide. Make it extremely concise, dense with high-impact facts, "
        "key takeaways, bullet points, core formulas, and quick mnemonics."
    ),
    "cheatsheet": (
        "Create an Ultimate Cheat Sheet. Focus on bullet points, formula reference tables, "
        "syntax/code blocks, time & space complexities, shortcuts, and key terminology matrices."
    ),
}


class StudyAgentService:
    async def get_document_context(
        self, user_id: str, query: str, workspace_id: Optional[str] = None, top_k: int = 6
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Retrieve relevant context chunks and metadata from document index."""
        try:
            retriever = get_retriever()
            results = await retriever.retrieve(
                query=query,
                user_id=user_id,
                workspace_id=workspace_id,
                top_k=top_k,
            )
            context_blocks = []
            citations = []
            for r in results:
                file_name = r.get("metadata", {}).get("file_name", "Document")
                page_num = r.get("metadata", {}).get("page_number", "")
                page_str = f" (Page {page_num})" if page_num else ""
                content = r.get("content", "")
                context_blocks.append(f"[{file_name}{page_str}]\n{content}")
                citations.append({
                    "document_id": r.get("document_id"),
                    "file_name": file_name,
                    "page_number": page_num,
                    "snippet": content[:200],
                })
            return "\n\n---\n\n".join(context_blocks), citations
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return "", []

    async def generate_study_notes(
        self,
        topic: str,
        user_id: str,
        style: str = "detailed",
        workspace_id: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured AI study notes in any of 5 styles with KaTeX & Mermaid diagrams."""
        style_key = style.lower() if style.lower() in NOTE_STYLE_INSTRUCTIONS else "detailed"
        style_prompt = NOTE_STYLE_INSTRUCTIONS[style_key]

        rag_context, citations = await self.get_document_context(user_id, topic, workspace_id=workspace_id, top_k=8)

        system_instruction = (
            "You are a World-Class Professor and AI Learning Specialist. "
            f"{style_prompt}\n\n"
            "FORMATTING RULES:\n"
            "1. Use LaTeX for math: inline $E = mc^2$ or block $$...$$.\n"
            "2. Render Mermaid diagrams (```mermaid ... ```) for mind maps, flowcharts, or architecture whenever helpful.\n"
            "3. Render Markdown comparison tables with clear columns.\n"
            "4. Include Callout blocks (> [!TIP], > [!IMPORTANT], > [!NOTE]) for key insights and memory tricks.\n"
            "5. Cite uploaded sources with document name and page numbers when referencing facts."
        )

        user_prompt = f"Generate comprehensive study notes for topic: '{topic}'"
        if rag_context:
            user_prompt += f"\n\nUse the following extracted document knowledge:\n{rag_context}"
        if custom_instructions:
            user_prompt += f"\n\nAdditional user requirements:\n{custom_instructions}"

        content = await llm_service.generate(
            prompt=user_prompt,
            system_instruction=system_instruction,
            temperature=0.4,
            max_output_tokens=4096,
        )

        title = f"{topic.title()} - {style_key.title()} Study Notes"
        return {
            "title": title,
            "content": content,
            "style": style_key,
            "citations": citations,
        }

    async def generate_questions(
        self,
        topic: str,
        user_id: str,
        count: int = 5,
        blooms_level: str = "all",
        question_types: List[str] = None,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate Bloom's Taxonomy aligned study questions with step-by-step solutions and memory tricks."""
        rag_context, _ = await self.get_document_context(user_id, topic, workspace_id=workspace_id, top_k=6)
        types_str = ", ".join(question_types) if question_types else "MCQ, Short Answer, Long Answer, Solved Numerical"

        system_prompt = (
            "You are an Expert Educational Assessment Specialist. "
            "Generate high-quality study questions aligned with Bloom's Taxonomy levels "
            "(Remember, Understand, Apply, Analyze, Evaluate, Create).\n\n"
            "Return a JSON array of question objects with exact key names:\n"
            "[\n"
            "  {\n"
            '    "id": "q1",\n'
            '    "question": "Question text with $KaTeX$ if math...",\n'
            '    "type": "mcq|short_answer|long_answer|numerical|case_study",\n'
            '    "bloomsLevel": "Remember|Understand|Apply|Analyze|Evaluate|Create",\n'
            '    "options": ["A", "B", "C", "D"], // required for mcq\n'
            '    "correctAnswer": "Exact correct answer or option text",\n'
            '    "explanation": "Detailed step-by-step solution and reasoning",\n'
            '    "formulaDerivation": "Formula derivation if applicable else empty",\n'
            '    "memoryTrick": "Mnemonic, analogy, or memory trick to remember this",\n'
            '    "commonMistakes": "Common mistakes students make on this topic"\n'
            "  }\n"
            "]\n\n"
            "Return ONLY raw valid JSON array, no markdown formatting around JSON."
        )

        prompt = (
            f"Generate {count} questions for topic: '{topic}'.\n"
            f"Bloom's taxonomy target: {blooms_level}.\n"
            f"Requested types: {types_str}.\n"
        )
        if rag_context:
            prompt += f"\nReference Knowledge:\n{rag_context}"

        raw_response = await llm_service.generate(
            prompt=prompt,
            system_instruction=system_prompt,
            temperature=0.3,
            max_output_tokens=4096,
        )

        try:
            cleaned = re.sub(r"^```json\s*", "", raw_response.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            questions = json.loads(cleaned)
            if isinstance(questions, list):
                return questions
        except Exception as e:
            logger.warning(f"Failed to parse question JSON: {e}")

        # Fallback question structure if JSON parsing fails
        return [
            {
                "id": "q1",
                "question": f"Explain the fundamental principles of {topic}.",
                "type": "long_answer",
                "bloomsLevel": "Understand",
                "options": [],
                "correctAnswer": f"Core principles of {topic} involve foundational theoretical concepts and practical applications.",
                "explanation": raw_response,
                "formulaDerivation": "",
                "memoryTrick": "Focus on main definitions and key formulas.",
                "commonMistakes": "Confusing definitions with application steps.",
            }
        ]

    async def explain_formula(
        self, formula: str, user_id: str, workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a complete mathematical breakdown for any formula."""
        rag_context, citations = await self.get_document_context(user_id, formula, workspace_id=workspace_id, top_k=4)

        system_instruction = (
            "You are a Senior Mathematical & Physics Educator. Provide an exhaustive breakdown of the given formula.\n"
            "Include:\n"
            "1. **Rendered Formula**: Render in $...$ or $$...$$\n"
            "2. **Physical/Mathematical Meaning**: Intuitive explanation\n"
            "3. **Variable Definitions & Units**: Table of variable name, symbol, SI units, description\n"
            "4. **Step-by-Step Derivation**: Mathematical proof from first principles\n"
            "5. **Real-World Applications**: Practical engineering or scientific use cases\n"
            "6. **Limitations & Edge Cases**: When the formula fails or assumptions break\n"
            "7. **Solved Numerical Example**: Complete problem statement with step-by-step numbers\n"
            "8. **Practice Problem**: Unsolved problem for the student to attempt"
        )

        user_prompt = f"Provide a complete mathematical breakdown of the formula / concept: '{formula}'"
        if rag_context:
            user_prompt += f"\n\nDocument Context:\n{rag_context}"

        breakdown = await llm_service.generate(
            prompt=user_prompt,
            system_instruction=system_instruction,
            temperature=0.3,
        )

        return {
            "formula": formula,
            "breakdown": breakdown,
            "citations": citations,
        }

    async def generate_concept_graph(
        self, topic: str, user_id: str, workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract concept hierarchy and generate a Knowledge Graph representation with Mermaid code."""
        rag_context, _ = await self.get_document_context(user_id, topic, workspace_id=workspace_id, top_k=8)

        system_prompt = (
            "You are a Knowledge Graph Architect. Analyze the topic/document and extract a concept node hierarchy.\n"
            "Return a JSON object with two fields:\n"
            "1. `mermaid`: A valid Mermaid flowchart (`graph TD ...`) string visualizing the relationships.\n"
            "2. `nodes`: Array of objects: `[{\"id\": \"concept_name\", \"label\": \"Display Name\", \"type\": \"core|subconcept|prerequisite\", \"description\": \"Short 1-sentence definition\"}]`\n"
            "Return ONLY raw JSON."
        )

        prompt = f"Build a Knowledge Graph for topic: '{topic}'"
        if rag_context:
            prompt += f"\n\nSource Content:\n{rag_context}"

        raw_response = await llm_service.generate(
            prompt=prompt,
            system_instruction=system_prompt,
            temperature=0.2,
        )

        try:
            cleaned = re.sub(r"^```json\s*", "", raw_response.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.warning(f"Failed to parse concept graph JSON: {e}")
            return {
                "mermaid": f"graph TD\n  A[{topic}] --> B[Core Concept]\n  A --> C[Applications]\n  B --> D[Details]",
                "nodes": [
                    {"id": topic, "label": topic, "type": "core", "description": f"Main topic: {topic}"}
                ]
            }

    async def resolve_references(
        self, user_id: str, workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract and link citations, section references, DOIs, and IEEE references across workspace documents."""
        retriever = get_retriever()
        try:
            results = await retriever.retrieve(
                query="references citations bibliography IEEE DOI section chapter paper textbook",
                user_id=user_id,
                workspace_id=workspace_id,
                top_k=10,
            )
            extracted_refs = []
            for item in results:
                content = item.get("content", "")
                file_name = item.get("metadata", {}).get("file_name", "Document")
                page_num = item.get("metadata", {}).get("page_number", "")
                
                # Regex match DOIs, IEEE, section numbers, citations
                matches = re.findall(
                    r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+|IEEE\s+[A-Za-z0-9.]+|Section\s+\d+(\.\d+)*|Chapter\s+\d+|\[\d+\]\s+[A-Z][a-z]+[^.\n]+\.\d{4})",
                    content,
                )
                for match in matches:
                    ref_str = match[0] if isinstance(match, tuple) else match
                    extracted_refs.append({
                        "reference": ref_str,
                        "sourceDocument": file_name,
                        "pageNumber": page_num,
                        "context": content[:180],
                    })

            # Deduplicate by reference string
            seen = set()
            unique_refs = []
            for r in extracted_refs:
                if r["reference"] not in seen:
                    seen.add(r["reference"])
                    unique_refs.append(r)
            return unique_refs
        except Exception as e:
            logger.warning(f"Reference extraction failed: {e}")
            return []


study_agent_service = StudyAgentService()
