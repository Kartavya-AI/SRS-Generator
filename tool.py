import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def cleanup_text(text: str) -> str:
    text = text.replace('*', '')
    text = text.replace('#', '')
    return text

def generate_srs(api_key: str, specialist: str, requirements: str) -> str:
    os.environ["GOOGLE_API_KEY"] = api_key
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)


    srs_template = """
    As an expert {specialist}, your task is to create a formal Software Requirements Specification (SRS) document.
    The user has provided the following project requirements:

    --- USER REQUIREMENTS ---
    {requirements}
    --- END OF REQUIREMENTS ---

    Based on these requirements, please generate a comprehensive SRS document with the following sections.
    Be detailed and professional in your writing. If a section is not applicable, state that.

    1.  **Introduction**
        1.1. Purpose of the Document
        1.2. Scope of the Project
        1.3. Target Audience

    2.  **Overall Description**
        2.1. Product Perspective
        2.2. Product Functions (Summarize the key features)
        2.3. User Characteristics
        2.4. Constraints (e.g., technology stack, platform, security)
        2.5. Assumptions and Dependencies

    3.  **System Features**
        (Break down the requirements into specific, detailed features. For each feature, describe its functionality.)
        3.1. Feature 1: [Name of Feature]
             - Description: ...
             - Functional Requirements: ...
        3.2. Feature 2: [Name of Feature]
             - Description: ...
             - Functional Requirements: ...
        (Continue for all major features based on the user's input)

    4.  **Non-Functional Requirements**
        4.1. Performance
        4.2. Security
        4.3. Usability
        4.4. Reliability

    5.  **Appendices (Optional)**
        (If you can infer any, add definitions, acronyms, or abbreviations here.)

    **FORMATTING RULES (VERY IMPORTANT):**
    - **DO NOT USE MARKDOWN.**
    - Use hyphens (-) for lists.
    - Use all-caps for section headers (e.g., 1. INTRODUCTION).
    - The output must be plain text.

    Please generate the complete SRS document now.
    """

    prompt = ChatPromptTemplate.from_template(srs_template)
    output_parser = StrOutputParser()
    srs_chain = prompt | llm | output_parser
    response = srs_chain.invoke({
        "specialist": specialist,
        "requirements": requirements
    })

    clean_response = cleanup_text(response)
    return clean_response
