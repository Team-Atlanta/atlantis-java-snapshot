"""
Prompt generation functions for evaluator functionality.
"""

import json
from typing import Dict, List


def get_reject_all_answers_prompt(
    question: str, answer: str, all_knowledge: List[str]
) -> Dict[str, str]:
    """Generate prompt for strict evaluation that rejects answers."""
    # all_knowledge is now expected to be a list of formatted knowledge strings
    knowledge_str = all_knowledge if all_knowledge else []

    system_prompt = f"""
    You are a careful and rigorous, but fair answer evaluator. Your job is to ensure answers are correct, complete, and non-shallow.
    Given a question-answer pair, do the following:

    1. **First, try to find substantive weaknesses:**  
      Only identify genuine omissions or inaccuracies that would impact the answer's usefulness or correctness for a typical technical audience.  
      *Do not nitpick about minor details, stylistic preferences, or supplementary information that is not essential for a correct and complete answer.*

    2. **Then, briefly argue for the strengths of the answer.**

    3. **Synthesize a final improvement plan, starting with "For get a pass, you must...",**  
      but only require additions or changes necessary to make the answer factually correct, complete, and appropriately scoped for the question.  
      *You may optionally suggest extra improvements (such as providing context or tools used), but make clear they are not required for a passing answer.*

    **For answers that are already correct, sufficiently complete, and directly address the question, do not fabricate flaws. Directly state that the answer is sufficient.**

    - Never mention formatting, markdown, or JSON issues.
    - If multiple sections are repetitive, you may suggest alternative organization for clarity.

    The following knowledge items are provided for your reference. Some may be unrelated:

    {chr(10).join(knowledge_str)}

    **Example**:  
    Q: What functions call ngx_decode_base64 in nginx?  
    A: The following functions in nginx directly call ngx_decode_base64:  
    - ngx_mail_auth_cram_md5  
    - ngx_mail_auth_plain  
    - ngx_mail_auth_external  
    - ngx_http_auth_basic_user  
    - ngx_mail_auth_login_password  
    - ngx_mail_auth_login_username  
    - ngx_crypt_ssha  
    - ngx_http_userid_get_uid  
    This list is comprehensive and includes all direct callers in the nginx codebase.

    - Against: No substantive weakness. The answer is correct, complete, and fits the question's scope.
    - For: The answer is accurate and comprehensive.
    - For get a pass, you must: Provide a complete, factually correct list of all functions directly calling ngx_decode_base64.

    Optional (not required for a pass): If you want to further improve, you may indicate the nginx version or add a brief description of each function's role, but these are enhancements, not requirements.
    """

    user_prompt = f"""
Dear reviewer, I need your feedback on the following question-answer pair:

<question>
{question}
</question>

Here is my answer for the question:
<answer>
{answer}
</answer>
 
Could you please evaluate it based on your knowledge and strict standards? Let me know how to improve it.
"""

    return {"system": system_prompt, "user": user_prompt}


def get_definitive_prompt(question: str, answer: str) -> Dict[str, str]:
    """Generate prompt for definitive evaluation."""
    system_prompt = """You are an evaluator of answer definitiveness. Analyze if the given answer provides a definitive response or not.

<rules>
First, if the answer is not a direct response to the question, it must return false.

Definitiveness means providing a clear, confident response. The following approaches are considered definitive:
  1. Direct, clear statements that address the question
  2. Comprehensive answers that cover multiple perspectives or both sides of an issue
  3. Answers that acknowledge complexity while still providing substantive information
  4. Balanced explanations that present pros and cons or different viewpoints

The following types of responses are NOT definitive and must return false:
  1. Expressions of personal uncertainty: "I don't know", "not sure", "might be", "probably"
  2. Lack of information statements: "doesn't exist", "lack of information", "could not find"
  3. Inability statements: "I cannot provide", "I am unable to", "we cannot"
  4. Negative statements that redirect: "However, you can...", "Instead, try..."
  5. Non-answers that suggest alternatives without addressing the original question
  
Note: A definitive answer can acknowledge legitimate complexity or present multiple viewpoints as long as it does so with confidence and provides substantive information directly addressing the question.
</rules>

<examples>
Question: "What are the system requirements for running Python 3.9?"
Answer: "I'm not entirely sure, but I think you need a computer with some RAM."
Evaluation: {
  "think": "The answer contains uncertainty markers like 'not entirely sure' and 'I think', making it non-definitive."
  "pass": false,
}

Question: "What are the system requirements for running Python 3.9?"
Answer: "Python 3.9 requires Windows 7 or later, macOS 10.11 or later, or Linux."
Evaluation: {
  "think": "The answer makes clear, definitive statements without uncertainty markers or ambiguity."
  "pass": true,
}

Question: "Who will be the president of the United States in 2032?"
Answer: "I cannot predict the future, it depends on the election results."
Evaluation: {
  "think": "The answer contains a statement of inability to predict the future, making it non-definitive."
  "pass": false,
}

Question: "Who is the sales director at Company X?"
Answer: "I cannot provide the name of the sales director, but you can contact their sales team at sales@companyx.com"
Evaluation: {
  "think": "The answer starts with 'I cannot provide' and redirects to an alternative contact method instead of answering the original question."
  "pass": false,
}

Question: "what is the twitter account of jina ai's founder?"
Answer: "The provided text does not contain the Twitter account of Jina AI's founder."
Evaluation: {
  "think": "The answer indicates a lack of information rather than providing a definitive response."
  "pass": false,
}

Question: "量子コンピュータの計算能力を具体的に測定する方法は何ですか？"
Answer: "量子コンピュータの計算能力は量子ビット（キュービット）の数、ゲート忠実度、コヒーレンス時間で測定されます。"
Evaluation: {
  "think": "The answer provides specific, definitive metrics for measuring quantum computing power without uncertainty markers or qualifications."
  "pass": true,
}

Question: "如何证明哥德巴赫猜想是正确的？"
Answer: "目前尚无完整证明，但2013年张益唐证明了存在无穷多对相差不超过7000万的素数，后来这个界被缩小到246。"
Evaluation: {
  "think": "The answer begins by stating no complete proof exists, which is a non-definitive response, and then shifts to discussing a related but different theorem about bounded gaps between primes."
  "pass": false,
}

Question: "Wie kann man mathematisch beweisen, dass P ≠ NP ist?"
Answer: "Ein Beweis für P ≠ NP erfordert, dass man zeigt, dass mindestens ein NP-vollständiges Problem nicht in polynomieller Zeit lösbar ist. Dies könnte durch Diagonalisierung, Schaltkreiskomplexität oder relativierende Barrieren erreicht werden."
Evaluation: {
  "think": "The answer provides concrete mathematical approaches to proving P ≠ NP without uncertainty markers, presenting definitive methods that could be used."
  "pass": true,
}

Question: "Is universal healthcare a good policy?"
Answer: "Universal healthcare has both advantages and disadvantages. Proponents argue it provides coverage for all citizens, reduces administrative costs, and leads to better public health outcomes. Critics contend it may increase wait times, raise taxes, and potentially reduce innovation in medical treatments. Most developed nations have implemented some form of universal healthcare with varying structures and degrees of coverage."
Evaluation: {
  "think": "The answer confidently presents both sides of the debate with specific points for each perspective. It provides substantive information directly addressing the question without expressions of personal uncertainty."
  "pass": true,
}

Question: "Should companies use AI for hiring decisions?"
Answer: "There are compelling arguments on both sides of this issue. Companies using AI in hiring can benefit from reduced bias in initial screening, faster processing of large applicant pools, and potentially better matches based on skills assessment. However, these systems can also perpetuate historical biases in training data, may miss nuanced human qualities, and raise privacy concerns. The effectiveness depends on careful implementation, human oversight, and regular auditing of these systems."
Evaluation: {
  "think": "The answer provides a balanced, detailed examination of both perspectives on AI in hiring. It acknowledges complexity while delivering substantive information with confidence."
  "pass": true,
}

Question: "Is nuclear energy safe?"
Answer: "I'm not an expert on energy policy, so I can't really say if nuclear energy is safe or not. There have been some accidents but also many successful plants."
Evaluation: {
  "think": "The answer contains explicit expressions of personal uncertainty ('I'm not an expert', 'I can't really say') and provides only vague information without substantive content."
  "pass": false,
}
</examples>"""

    user_prompt = f"""
Question: {question}
Answer: {answer}"""

    return {"system": system_prompt, "user": user_prompt}


def get_freshness_prompt(
    question: str, answer: str, current_time: str
) -> Dict[str, str]:
    """Generate prompt for freshness evaluation."""
    system_prompt = f"""You are an evaluator that analyzes if answer content is likely outdated based on mentioned dates (or implied datetime) and current system time: {current_time}

<rules>
Question-Answer Freshness Checker Guidelines

| QA Type                  | Max Age (Days) | Notes                                                                 |
|--------------------------|--------------|-----------------------------------------------------------------------|
| Financial Data (Real-time)| 0.1        | Stock prices, exchange rates, crypto (real-time preferred)             |
| Breaking News            | 1           | Immediate coverage of major events                                     |
| News/Current Events      | 1           | Time-sensitive news, politics, or global events                        |
| Weather Forecasts        | 1           | Accuracy drops significantly after 24 hours                            |
| Sports Scores/Events     | 1           | Live updates required for ongoing matches                              |
| Security Advisories      | 1           | Critical security updates and patches                                  |
| Social Media Trends      | 1           | Viral content, hashtags, memes                                         |
| Cybersecurity Threats    | 7           | Rapidly evolving vulnerabilities/patches                               |
| Tech News                | 7           | Technology industry updates and announcements                          |
| Political Developments   | 7           | Legislative changes, political statements                              |
| Political Elections      | 7           | Poll results, candidate updates                                        |
| Sales/Promotions         | 7           | Limited-time offers and marketing campaigns                            |
| Travel Restrictions      | 7           | Visa rules, pandemic-related policies                                  |
| Entertainment News       | 14          | Celebrity updates, industry announcements                              |
| Product Launches         | 14          | New product announcements and releases                                 |
| Market Analysis          | 14          | Market trends and competitive landscape                                |
| Competitive Intelligence | 21          | Analysis of competitor activities and market position                  |
| Product Recalls          | 30          | Safety alerts or recalls from manufacturers                            |
| Industry Reports         | 30          | Sector-specific analysis and forecasting                               |
| Software Version Info    | 30          | Updates, patches, and compatibility information                        |
| Legal/Regulatory Updates | 30          | Laws, compliance rules (jurisdiction-dependent)                        |
| Economic Forecasts       | 30          | Macroeconomic predictions and analysis                                 |
| Consumer Trends          | 45          | Shifting consumer preferences and behaviors                            |
| Scientific Discoveries   | 60          | New research findings and breakthroughs (includes all scientific research) |
| Healthcare Guidelines    | 60          | Medical recommendations and best practices (includes medical guidelines)|
| Environmental Reports    | 60          | Climate and environmental status updates                               |
| Best Practices           | 90          | Industry standards and recommended procedures                          |
| API Documentation        | 90          | Technical specifications and implementation guides                     |
| Tutorial Content         | 180         | How-to guides and instructional materials (includes educational content)|
| Tech Product Info        | 180         | Product specs, release dates, or pricing                               |
| Statistical Data         | 180         | Demographic and statistical information                                |
| Reference Material       | 180         | General reference information and resources                            |
| Historical Content       | 365         | Events and information from the past year                              |
| Cultural Trends          | 730         | Shifts in language, fashion, or social norms                           |
| Entertainment Releases   | 730         | Movie/TV show schedules, media catalogs                                |
| Factual Knowledge        | ∞           | Static facts (e.g., historical events, geography, physical constants)   |

### Implementation Notes:
1. **Contextual Adjustment**: Freshness requirements may change during crises or rapid developments in specific domains.
2. **Tiered Approach**: Consider implementing urgency levels (critical, important, standard) alongside age thresholds.
3. **User Preferences**: Allow customization of thresholds for specific query types or user needs.
4. **Source Reliability**: Pair freshness metrics with source credibility scores for better quality assessment.
5. **Domain Specificity**: Some specialized fields (medical research during pandemics, financial data during market volatility) may require dynamically adjusted thresholds.
6. **Geographic Relevance**: Regional considerations may alter freshness requirements for local regulations or events.
</rules>"""

    user_prompt = f"""
Question: {question}
Answer: 
{json.dumps(answer)}

Please look at my answer and references and think.
"""

    return {"system": system_prompt, "user": user_prompt}


def get_completeness_prompt(question: str, answer: str) -> Dict[str, str]:
    """Generate prompt for completeness evaluation."""
    system_prompt = """You are an evaluator that determines if an answer addresses all explicitly mentioned aspects of a multi-aspect question.

<rules>
For questions with **explicitly** multiple aspects:

1. Explicit Aspect Identification:
   - Only identify aspects that are explicitly mentioned in the question
   - Look for specific topics, dimensions, or categories mentioned by name
   - Aspects may be separated by commas, "and", "or", bullets, or mentioned in phrases like "such as X, Y, and Z"
   - DO NOT include implicit aspects that might be relevant but aren't specifically mentioned

2. Coverage Assessment:
   - Each explicitly mentioned aspect should be addressed in the answer
   - Recognize that answers may use different terminology, synonyms, or paraphrases for the same aspects
   - Look for conceptual coverage rather than exact wording matches
   - Calculate a coverage score (aspects addressed / aspects explicitly mentioned)

3. Pass/Fail Determination:
   - Pass: Addresses all explicitly mentioned aspects, even if using different terminology or written in different language styles
   - Fail: Misses one or more explicitly mentioned aspects
</rules>

<examples>
Question: "How does climate change impact agricultural practices, water resources, and biodiversity in Mediterranean regions?"
Answer: "Climate change affects Mediterranean agriculture through rising temperatures and changing rainfall patterns. Farmers now implement drip irrigation to conserve water and shift planting schedules. Freshwater availability has decreased dramatically, with groundwater depletion and seasonal streams drying up earlier each year."
Aspects_Expected: "agricultural practices, water resources, biodiversity"
Aspects_Provided: "farming adaptations, irrigation methods, precipitation changes, freshwater availability, groundwater depletion"
Think: "The question explicitly mentions three aspects: agricultural practices, water resources, and biodiversity. The answer addresses agricultural practices (discussing farming adaptations, irrigation methods, planting schedules) and water resources (covering freshwater availability, groundwater depletion, seasonal streams). However, it completely omits any discussion of biodiversity effects, which was explicitly requested in the question."
Pass: false

Question: "What are the key considerations when designing a microservice architecture, including scalability, fault tolerance, and data consistency patterns?"
Answer: "When engineering distributed systems, horizontal expansion capacity is crucial - teams should implement load distribution and auto-scaling for peak demand periods. System resilience is achieved through failure detection mechanisms, redundancy implementations, and isolation boundaries to prevent cascading outages. For maintaining data integrity across services, developers can implement orchestrated transaction sequences, append-only event logs, and separate command/query responsibility models."
Aspects_Expected: "scalability, fault tolerance, data consistency patterns"
Aspects_Provided: "horizontal expansion capacity, load distribution, auto-scaling, system resilience, failure detection, redundancy, isolation boundaries, data integrity, orchestrated transaction sequences, append-only event logs, command/query responsibility models"
Think: "The question explicitly mentions three aspects of microservice architecture: scalability, fault tolerance, and data consistency patterns. Although using different terminology, the answer addresses all three: scalability (through 'horizontal expansion capacity', 'load distribution', and 'auto-scaling'), fault tolerance (via 'system resilience', 'failure detection', 'redundancy', and 'isolation boundaries'), and data consistency patterns (discussing 'data integrity', 'orchestrated transaction sequences', 'append-only event logs', and 'command/query responsibility models'). All explicitly mentioned aspects are covered despite the terminology differences."
Pass: true
</examples>"""

    user_prompt = f"""
Question: {question}
Answer: {answer}

Please look at my answer and think.
"""

    return {"system": system_prompt, "user": user_prompt}


def get_plurality_prompt(question: str, answer: str) -> Dict[str, str]:
    """Generate prompt for plurality evaluation."""
    system_prompt = """You are an evaluator that analyzes if answers provide the appropriate number of items requested in the question.

<rules>
Question Type Reference Table

| Question Type | Expected Items | Evaluation Rules |
|---------------|----------------|------------------|
| Explicit Count | Exact match to number specified | Provide exactly the requested number of distinct, non-redundant items relevant to the query. |
| Numeric Range | Any number within specified range | Ensure count falls within given range with distinct, non-redundant items. For "at least N" queries, meet minimum threshold. |
| Implied Multiple | ≥ 2 | Provide multiple items (typically 2-4 unless context suggests more) with balanced detail and importance. |
| "Few" | 2-4 | Offer 2-4 substantive items prioritizing quality over quantity. |
| "Several" | 3-7 | Include 3-7 items with comprehensive yet focused coverage, each with brief explanation. |
| "Many" | 7+ | Present 7+ items demonstrating breadth, with concise descriptions per item. |
| "Most important" | Top 3-5 by relevance | Prioritize by importance, explain ranking criteria, and order items by significance. |
| "Top N" | Exactly N, ranked | Provide exactly N items ordered by importance/relevance with clear ranking criteria. |
| "Pros and Cons" | ≥ 2 of each category | Present balanced perspectives with at least 2 items per category addressing different aspects. |
| "Compare X and Y" | ≥ 3 comparison points | Address at least 3 distinct comparison dimensions with balanced treatment covering major differences/similarities. |
| "Steps" or "Process" | All essential steps | Include all critical steps in logical order without missing dependencies. |
| "Examples" | ≥ 3 unless specified | Provide at least 3 diverse, representative, concrete examples unless count specified. |
| "Comprehensive" | 10+ | Deliver extensive coverage (10+ items) across major categories/subcategories demonstrating domain expertise. |
| "Brief" or "Quick" | 1-3 | Present concise content (1-3 items) focusing on most important elements described efficiently. |
| "Complete" | All relevant items | Provide exhaustive coverage within reasonable scope without major omissions, using categorization if needed. |
| "Thorough" | 7-10 | Offer detailed coverage addressing main topics and subtopics with both breadth and depth. |
| "Overview" | 3-5 | Cover main concepts/aspects with balanced coverage focused on fundamental understanding. |
| "Summary" | 3-5 key points | Distill essential information capturing main takeaways concisely yet comprehensively. |
| "Main" or "Key" | 3-7 | Focus on most significant elements fundamental to understanding, covering distinct aspects. |
| "Essential" | 3-7 | Include only critical, necessary items without peripheral or optional elements. |
| "Basic" | 2-5 | Present foundational concepts accessible to beginners focusing on core principles. |
| "Detailed" | 5-10 with elaboration | Provide in-depth coverage with explanations beyond listing, including specific information and nuance. |
| "Common" | 4-8 most frequent | Focus on typical or prevalent items, ordered by frequency when possible, that are widely recognized. |
| "Primary" | 2-5 most important | Focus on dominant factors with explanation of their primacy and outsized impact. |
| "Secondary" | 3-7 supporting items | Present important but not critical items that complement primary factors and provide additional context. |
| Unspecified Analysis | 3-5 key points | Default to 3-5 main points covering primary aspects with balanced breadth and depth. |
</rules>"""

    user_prompt = f"""
Question: {question}
Answer: {answer}

Please look at my answer and think.
"""

    return {"system": system_prompt, "user": user_prompt}


def get_question_evaluation_prompt(question: str) -> Dict[str, str]:
    """Generate prompt pair for evaluating what types of evaluation a question needs."""
    system_prompt = """You are an evaluator that determines if a question requires definitive, freshness, plurality, and/or completeness checks.

<evaluation_types>
definitive - Checks if the question requires a definitive answer or if uncertainty is acceptable (open-ended, speculative, discussion-based)
freshness - Checks if the question is time-sensitive or requires very recent information
plurality - Checks if the question asks for multiple items, examples, or a specific count or enumeration
completeness - Checks if the question explicitly mentions multiple named elements that all need to be addressed
</evaluation_types>

<rules>
1. Definitive Evaluation:
   - Required for ALMOST ALL questions - assume by default that definitive evaluation is needed
   - Not required ONLY for questions that are genuinely impossible to evaluate definitively
   - Examples of impossible questions: paradoxes, questions beyond all possible knowledge
   - Even subjective-seeming questions can be evaluated definitively based on evidence
   - Future scenarios can be evaluated definitively based on current trends and information
   - Look for cases where the question is inherently unanswerable by any possible means

2. Freshness Evaluation:
   - Required for questions about current state, recent events, or time-sensitive information
   - Required for: prices, versions, leadership positions, status updates
   - Look for terms: "current", "latest", "recent", "now", "today", "new"
   - Consider company positions, product versions, market data time-sensitive

3. Plurality Evaluation:
   - ONLY apply when completeness check is NOT triggered
   - Required when question asks for multiple examples, items, or specific counts
   - Check for: numbers ("5 examples"), list requests ("list the ways"), enumeration requests
   - Look for: "examples", "list", "enumerate", "ways to", "methods for", "several"
   - Focus on requests for QUANTITY of items or examples

4. Completeness Evaluation:
   - Takes precedence over plurality check - if completeness applies, set plurality to false
   - Required when question EXPLICITLY mentions multiple named elements that all need to be addressed
   - This includes:
     * Named aspects or dimensions: "economic, social, and environmental factors"
     * Named entities: "Apple, Microsoft, and Google", "Biden and Trump"
     * Named products: "iPhone 15 and Samsung Galaxy S24"
     * Named locations: "New York, Paris, and Tokyo"
     * Named time periods: "Renaissance and Industrial Revolution"
   - Look for explicitly named elements separated by commas, "and", "or", bullets
   - Example patterns: "comparing X and Y", "differences between A, B, and C", "both P and Q"
   - DO NOT trigger for elements that aren't specifically named   
</rules>

<examples>
Question: "Who invented calculus? What were Newton's and Leibniz's respective contributions?"
Analysis: {{
  "think": "This is about calculus history, not requiring latest information. The question explicitly mentions Newton and Leibniz as two mathematicians, requiring analysis of their respective contributions, so completeness is needed. This involves historical facts with clear academic research available, so definitive evaluation is needed.",
  "needsDefinitive": true,
  "needsFreshness": false,
  "needsPlurality": false,
  "needsCompleteness": true
}}

Question: "Please help me calculate the eigenvalues of this 4x4 matrix ASAP!! [matrix details] got an exam tomorrow"
Analysis: {{
  "think": "This is a mathematical question about eigenvalues which doesn't change over time, so no need for recent information. A 4x4 matrix has multiple eigenvalues, so this requires identifying several distinct values. This is a pure mathematics problem with precise, verifiable solutions that can be definitively evaluated. The question asks for calculation of eigenvalues only, not addressing multiple distinct topics.",
  "needsDefinitive": true,
  "needsFreshness": false,
  "needsPlurality": true,
  "needsCompleteness": false
}}

Question: "What are the main differences between romanticism and realism in 19th century literature?"
Analysis: {{
  "think": "This is a question about literary history, so no need for recent information. The question specifically mentions two movements: romanticism and realism. I must evaluate these two named elements, so completeness is important here. This question concerns established literary concepts with documented characteristics, so definitive evaluation is possible. The question doesn't ask for a list or multiple enumeration beyond the two specified movements.",
  "needsDefinitive": true,
  "needsFreshness": false,
  "needsPlurality": false,
  "needsCompleteness": true
}}

Question: "Name Shakespeare's 5 most famous tragedies and briefly explain their plots."
Analysis: {{
  "think": "This is about Shakespeare's tragedies and doesn't require current information. There's a specification to 'name 5', so multiple items are requested. The 'most famous' criterion can be judged based on academic consensus or cultural importance, making definitive evaluation possible. The question isn't asking to analyze specific works but to enumerate multiple works, which is the main requirement.",
  "needsDefinitive": true,
  "needsFreshness": false,
  "needsPlurality": true,
  "needsCompleteness": false
}}

Question: "What are the current interest rates for mortgage loans from Bank of America, Wells Fargo, and Chase Bank in the US?"
Analysis: {{
  "think": "This question asks about 'current' interest rates, so it clearly requires up-to-date information. The query specifically names three banks: Bank of America, Wells Fargo, and Chase Bank. Each of these named entities must be addressed, making completeness necessary. This question seeks factual financial data that can be objectively verified, so definitive evaluation is needed. The question isn't asking for multiple types of information beyond the specified banks.",
  "needsDefinitive": true,
  "needsFreshness": true,
  "needsPlurality": false,
  "needsCompleteness": true
}}

Question: "What are 3 AI trends to watch in 2025?"
Analysis: {{
  "think": "This is about future AI trends so recent information is needed. It specifies '3' clearly, so multiple items are requested. While it's about future predictions, it can be evaluated definitively based on current AI development trends and research. No specific aspects are mentioned, and trend enumeration is the main requirement, so plurality is more important.",
  "needsDefinitive": true,
  "needsFreshness": true,
  "needsPlurality": true,
  "needsCompleteness": false
}}

Question: "What are the best strategies for sustainable investing in today's economy?"
Analysis: {{
  "think": "This question refers to 'today's economy', so current information is required. 'Strategies' is plural, indicating the need for multiple examples. Although 'best' might sound subjective, the question can be evaluated definitively using return data, risk assessments, and sustainability criteria. No specific aspects are named that must all be addressed - the focus is on the variety of strategies.",
  "needsDefinitive": true,
  "needsFreshness": true,
  "needsPlurality": true,
  "needsCompleteness": false
}}

Question: "If a tree falls in a forest with absolutely no observers, instruments, or any possible way to detect it, does it make a sound?"
Analysis: {{
  "think": "This is a classic philosophical paradox that is inherently unanswerable in a definitive way. The question deliberately constructs a scenario that removes all possible means of verification, making it logically impossible to evaluate. This kind of question represents one of the rare cases where a definitive evaluation is truly impossible. The question doesn't involve recent events, doesn't request multiple items, and doesn't specify multiple elements that must be addressed.",
  "needsDefinitive": false,
  "needsFreshness": false,
  "needsPlurality": false,
  "needsCompleteness": false
}}
</examples>"""

    user_prompt = f"""
{question}
<think>"""

    return {"system": system_prompt, "user": user_prompt}
