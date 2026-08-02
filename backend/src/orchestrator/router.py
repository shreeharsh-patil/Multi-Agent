import re
from typing import Optional
from src.utils.logger import logger


class AgentRouter:
    def __init__(self):
        self.routing_rules = [
            (r"(?i)\b(generate|create|draw|make|design|render|paint|show|produce)\b.*\b(image|picture|photo|photograph|illustration|drawing|artwork|poster|logo|icon|graphic|banner|vector|avatar)\b", "image"),
            (r"(?i)\b(image|picture|photo|drawing|illustration)\b\s+(of|for|with|showing|featuring)\b", "image"),
            (r"(?i)\b(logo|icon|avatar)\b\s+(for|of|with|showing|featuring)\b", "image"),
            # Contacts: catch explicit contact/phone/email lookups before calendar
            (r"(?i)\b(contact|contacts|phone\s*book|address\s*book|phone\s*number|cell\s*number|mobile\s*number|email\s*address|who\s+is\s+in\s+my\s+contacts|find\s+contact|get\s+number|contact\s+info)\b", "contacts"),
            (r"(?i)\b(number\s+of|phone\s+of|mobile\s+of|email\s+of|contact\s+details|number\s+for|phone\s+for)\b", "contacts"),
            # Doctor: symptoms, conditions, general health inquiries (before research/knowledge)
            (r"(?i)\b(symptom|symptoms|diagnos|medical condition|medical advice|disease|infection|fever|cough|cold|headache|migraine|chest pain|shortness of breath|rash|nausea|vomiting|diarrhea|blood pressure|blood sugar|diabetes|flu|allergy|surgery|injury|first aid|bp|cholesterol|why do i feel|what is wrong with me)\b", "doctor"),
            # Pharmacologist: drugs, medicines, interactions, doses
            (r"(?i)\b(pharmacol|drug interaction|drug\b|drugs?|medication|medicine|dosage|dose\b|prescription|pharmaceutical|contraindication|antibiotic|paracetamol|ibuprofen|antidepressant|antibiotic|insulin|statins?|vaccine|opioid|adverse reaction)\b", "pharmacologist"),
            # Engineer: engineering, system design, architecture, circuits, code review
            (r"(?i)\b(engineering|engineer|system architecture|microservice|api design|circuit|embedded|mechanical|electrical design|code review|refactor|scalabilit|performance optimization|load balancer|ci/cd|deployment pipeline|database design|softw are design)\b", "engineer"),
            # Finance: statements, valuation, markets, investing (before calendar/research)
            (r"(?i)\b(finance|financial|valuation|eps\b|ebitda|pe\s+ratio|dividend|stock|shares?|equity|bond|yield|mutual\s+fund|portfolio|investing\b|discounted\s+cash\s+flow|dcf|working\s+capital|capital\s+structure|financial\s+statements?)\b", "finance"),
            # Accountant / CA: accounting, entries, audit, taxation
            (r"(?i)\b(accounting|accountant|chartered\s+accountant|journal\s+entry|ledger|trial\s+balance|final\s+accounts|debit|credit|audit|gst|income\s+tax|direct\s+tax|indirect\s+tax|depreciation|bad\s+debts|provision|cash\s+book|tally)\b", "accountant"),
            # Economics: micro/macro concepts
            (r"(?i)\b(economics|economy|microeconomic|macroeconomic|supply\s+and\s+demand|elasticity|opportunity\s+cost|inflation\s+rate\b|gdp\b|monetary\s+policy|fiscal\s+policy|central\s+bank|market\s+structure|consumer\s+surplus|producer\s+surplus)\b", "economics"),
            # Architect: architecture, buildings, construction, structures, drafting
            (r"(?i)\b(architecture|architect|building\s+construction|construction\b|structural\s+design|civil\s+engineering|blueprint|drafting|cad\b|building\s+materials|foundations?|beam|column|rcc|reinforced\s+concrete|sustainable\s+design|urban\s+design)\b", "architect"),
            # Cyber & Security: networks, hacking, encryption, security of systems + disambiguation
            (r"(?i)\b(cybersecurity|cyber\s+security|ethical\s+hacking|penetration\s+testing|pentest|hacking\b|hacker\b|vulnerability|exploit\b|malware|ransomware|phishing|cryptography|encryption|decrypt|network\s+security|firewall|intrusion\s+detection|capture\s+the\s+flag|ctf\b|owasp|sql\s+injection|xss\b)\b", "hacker"),
            # Cooking/Chef: cooking, culinary, recipes, food
            (r"(?i)\b(cooking|cuisine|culinary|chef\b|recipe|recipes|baking\b|pastry|sauce\b|grilling\b|knife\s+skills|mise\s+en\s+place|gastronomy|food\s+science|meal\s+prep|plating|dough|fermentation)\b", "cooking"),
            # Music: theory, instruments, composition
            (r"(?i)\b(music\b|musical|music\s+theory|melody|harmony|rhythm|scale\b|scales\b|chord\b|chords\b|intervals\b|ear\s+training|composition\b|songwriting|guitar\b|piano\b|violin\b|orchestra|symphony|note\s+reading|solfege)\b", "music"),
            # Fitness: exercise, gym, workout, nutrition
            (r"(?i)\b(fitness|workout|gym\b|exercise\b|exercises?\b|muscle\b|muscles\b|reps\b|bodyweight|squat\b|deadlift|bench\s+press|cardio\b|sports\s+science|kinesiology|nutrition\b|protein\b|macros?\b|weight\s+training|calisthenics)\b", "fitness"),
            # Art: drawing, painting, design
            (r"(?i)\b(art\b|artist|drawing\b|sketch\b|painting\b|paint\b|color\s+theory|colour\s+theory|perspective\s+drawing|portrait\b|landscape\s+art|graphic\s+design|composition\b|art\s+history|impressionism|renaissance\b|watercolour|watercolor)\b", "art"),
            # Calendar: catch all natural calendar/scheduling requests
            (r"(?i)\b(calendar|calender|calander)\b", "calendar"),
            (r"(?i)\b(meeting|appointment|event|availability|free\s*time|reschedule|book\s+(a\s+)?(slot|time|meeting)|add\s+to\s+(my\s+)?calendar|what.s\s+on\s+my|my\s+agenda|my\s+schedule|upcoming\s+events?|today.s\s+events?|tomorrow.s\s+events?|check\s+(my\s+)?schedule|show\s+(my\s+)?events?|list\s+(my\s+)?events?|delete\s+(the\s+)?(event|meeting|appointment)|cancel\s+(the\s+)?(event|meeting|appointment)|create\s+(a\s+)?(meeting|event|appointment)|schedule\s+(a\s+)?(meeting|call|event|appointment))\b", "calendar"),
            (r"(?i)\b(summarize|summarise|summary|extract|what is|explain|tell me about|find|search)\b.*\b(document|pdf|file|knowledge|upload|note|article|paper)\b", "knowledge"),
            (r"(?i)\b(google\s+drive|gdrive|drive)\b", "drive"),
            (r"(?i)\b(drive|google drive|upload|download|sync|folder|file)\b.*\b(document|file|folder|upload|download)\b", "drive"),
            (r"(?i)\b(note|notes|flashcards?|revision|study note|anki|pdf|export pdf|generate pdf|create pdf|make pdf)\b", "notes"),
            (r"(?i)\b(quiz|mcq|multiple choice|exam|practice question|test)\b", "quiz"),
            (r"(?i)\b(google\s+task|google\s+tasks|tasks|to-do list|checklist)\b", "tasks"),
            (r"(?i)\b(plan|deadline|remind|task\s+list)\b", "planner"),
            (r"(?i)\b(research|search\s+(the\s+)?internet|web\s+search|find\s+online|report\s+on|investigate)\b", "research"),
            (r"(?i)\b(write code|code|program|debug|function|class|algorithm|implement)\b", "coding"),
            (r"(?i)\b(remember|memory|recall|what did i|my name|my preference)\b", "memory"),
            (r"(?i)\b(gmail|email|inbox|mail|message|messages)\b", "gmail"),
            (r"(?i)\b(youtube|video|videos|yt)\b", "youtube"),
            (r"(?i)\b(weather|temperature|forecast|rain|humidity|climate|news|headlines|breaking news)\b", "weather_news"),
            (r"(?i)\b(calculate|math|calculator|api|integration)\b", "tool"),
        ]

    def route(self, user_input: str) -> Optional[str]:
        for pattern, agent_id in self.routing_rules:
            if re.search(pattern, user_input):
                logger.info(f"Routed to agent: {agent_id}", extra={"input": user_input[:100]})
                return agent_id
        return None

    def route_smart(self, user_input: str, requested_agent_id: Optional[str] = None) -> str:
        """Dynamically select the best agent for a user prompt, auto-correcting misaligned dropdown selections."""
        # 1. Pattern rule match takes priority for explicit actions (images, calendar, contacts, etc.)
        matched = self.route(user_input)
        if matched:
            return matched

        input_lower = user_input.lower().strip()
        cleaned_words = re.sub(r"[^\w\s]", "", input_lower).strip()

        # 2. Greetings and general conversational chat should always route to general assistant (auto)
        greetings = {
            "hello", "hi", "hey", "whats up", "what's up", "whast up", "how are you",
            "good morning", "good afternoon", "good evening", "thanks", "thank you",
            "ok", "okay", "cool", "great", "awesome", "sup"
        }
        if cleaned_words in greetings or any(cleaned_words.startswith(g) for g in ["hello", "hi ", "hey ", "whats up", "what's up", "whast up", "how are you"]):
            return "auto"

        # 3. If requested_agent_id is provided, validate it against the prompt nature
        if requested_agent_id and requested_agent_id != "auto":
            if requested_agent_id == "image":
                # Image agent should only execute when user explicitly requests image generation
                return "auto"
            if requested_agent_id == "coding":
                coding_keywords = ["code", "script", "python", "javascript", "typescript", "html", "css", "sql", "java", "c++", "c#", "rust", "go", "function", "class", "algorithm", "debug", "error", "exception", "bug", "program", "api", "refactor", "syntax"]
                if not any(k in input_lower for k in coding_keywords):
                    return "knowledge"
            return requested_agent_id

        # 4. For general explanations, questions, or concepts, default to knowledge agent
        explanation_keywords = ["explain", "what is", "define", "how does", "why", "tell me about", "concept", "meaning", "overview", "difference between"]
        if any(k in input_lower for k in explanation_keywords):
            return "knowledge"

        return "auto"
