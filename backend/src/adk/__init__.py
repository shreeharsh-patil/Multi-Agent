"""Google ADK-based multi-agent system."""

from src.adk.search_plan import (
    SearchPlan,
    SearchPlanQuery,
    SearchPlanMode,
    IntelligentSearchPlanner,
    store_search_plan_in_session,
    get_search_plan_from_session,
)
from src.adk.parallel_research import (
    create_parallel_web_research_agent,
    IndependentSpecialistSelector,
    ParallelWebResearchExecutor,
    INDEPENDENT_SEARCH_SPECIALISTS,
    DEPENDENT_ANALYSIS_SPECIALISTS,
    is_independent_specialist,
)

from src.adk.url_reader import (
    URLReaderService,
    StructuredWebExtract,
    URLReaderSecurity,
)
from src.adk.search_ranker import (
    SearchResultRanker,
    SearchResultRanking,
    RankedSource,
    RejectedSource,
)

from src.adk.passage_extractor import (
    PassageChunk,
    ExtractedPassagesPacket,
    ContentExtractorEngine,
    PassageRankerEngine,
)

from src.adk.verification import (
    ClaimStatus,
    VerifiedClaim,
    VerificationTeamResult,
    VerificationTeamEngine,
)

from src.adk.sequential_pipeline import (
    create_verified_web_pipeline_agent,
    VerifiedWebPipelineExecutor,
    store_pipeline_stage_data,
    get_pipeline_stage_data,
    SESSION_KEY_SEARCH_PLAN,
    SESSION_KEY_RAW_SEARCH_RESULTS,
    SESSION_KEY_RANKED_SOURCES,
    SESSION_KEY_READ_WEBPAGES,
    SESSION_KEY_EXTRACTED_PASSAGES,
    SESSION_KEY_VERIFIED_CLAIMS,
    SESSION_KEY_EVIDENCE_PACKET,
)

from src.adk.evidence_gap import (
    EvidenceGapReport,
    EvidenceGapAnalyzer,
    create_evidence_gap_agent,
    create_adaptive_research_loop_agent,
    AdaptiveResearchLoopExecutor,
)

from src.adk.research_synthesizer import (
    ResearchSynthesisPacket,
    ResearchSynthesizer,
    SynthesizedClaimRecord,
    SynthesizedEvidenceItem,
    SynthesizedSourceRecord,
    ConflictRecord,
    UncertaintyRecord,
)

__all__ = [
    "SearchPlan",
    "SearchPlanQuery",
    "SearchPlanMode",
    "IntelligentSearchPlanner",
    "store_search_plan_in_session",
    "get_search_plan_from_session",
    "create_parallel_web_research_agent",
    "IndependentSpecialistSelector",
    "ParallelWebResearchExecutor",
    "INDEPENDENT_SEARCH_SPECIALISTS",
    "DEPENDENT_ANALYSIS_SPECIALISTS",
    "is_independent_specialist",
    "URLReaderService",
    "StructuredWebExtract",
    "URLReaderSecurity",
    "SearchResultRanker",
    "SearchResultRanking",
    "RankedSource",
    "RejectedSource",
    "PassageChunk",
    "ExtractedPassagesPacket",
    "ContentExtractorEngine",
    "PassageRankerEngine",
    "ClaimStatus",
    "VerifiedClaim",
    "VerificationTeamResult",
    "VerificationTeamEngine",
    "create_verified_web_pipeline_agent",
    "VerifiedWebPipelineExecutor",
    "store_pipeline_stage_data",
    "get_pipeline_stage_data",
    "SESSION_KEY_SEARCH_PLAN",
    "SESSION_KEY_RAW_SEARCH_RESULTS",
    "SESSION_KEY_RANKED_SOURCES",
    "SESSION_KEY_READ_WEBPAGES",
    "SESSION_KEY_EXTRACTED_PASSAGES",
    "SESSION_KEY_VERIFIED_CLAIMS",
    "SESSION_KEY_EVIDENCE_PACKET",
    "EvidenceGapReport",
    "EvidenceGapAnalyzer",
    "create_evidence_gap_agent",
    "create_adaptive_research_loop_agent",
    "AdaptiveResearchLoopExecutor",
    # Phase 11
    "ResearchSynthesisPacket",
    "ResearchSynthesizer",
    "SynthesizedClaimRecord",
    "SynthesizedEvidenceItem",
    "SynthesizedSourceRecord",
    "ConflictRecord",
    "UncertaintyRecord",
]
