import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def cleanup_text(text: str) -> str:
    text = text.replace('*', '')
    text = text.replace('#', '')
    return text


def generate_questions(api_key: str, specialist: str, requirements: str) -> list[str]:
    os.environ["GOOGLE_API_KEY"] = api_key
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.8)

    question_generation_template = """
    You are an expert {specialist}. A user has provided the following initial project description:
    "{requirements}"

    Your task is to act as a project manager and identify areas that need more clarification.
    Generate a list of 5 to 6 critical follow-up questions to ask the user. These questions will help you gather the necessary details to write a comprehensive Software Requirements Specification (SRS).

    RULES:
    - Ask questions that cover functional requirements, target users, constraints, and potential features.
    - The questions should be clear, concise, and open-ended to encourage detailed responses.
    - Return ONLY the questions, with each question on a new line. Do not add any other text, numbering, or salutations.
    """

    prompt = ChatPromptTemplate.from_template(question_generation_template)
    chain = prompt | llm | StrOutputParser()

    response = chain.invoke({
        "specialist": specialist,
        "requirements": requirements
    })
    questions = [q.strip() for q in response.split('\n') if q.strip()]
    return questions


def generate_srs(api_key: str, specialist: str, conversation: str) -> str:
    os.environ["GOOGLE_API_KEY"] = api_key
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)

    srs_template = """
    As an expert {specialist}, your task is to create a formal Software Requirements Specification (SRS) document.
    You have conducted a Q&A session with the user. The full transcript is provided below:

    --- CONVERSATION TRANSCRIPT ---
    {conversation}
    --- END OF TRANSCRIPT ---

    Based on the ENTIRE conversation, please generate a comprehensive and well-structured SRS document.
    The user's responses might be informal, but your output must be professional.
    Infer details and structure the information logically into the following sections.

    1.  INTRODUCTION
        1.1. Purpose of the Document
        1.2. Scope of the Project
        1.3. Target Audience

    2.  OVERALL DESCRIPTION
        2.1. Product Perspective
        2.2. Product Functions (Summarize the key features)
        2.3. User Characteristics
        2.4. Constraints (e.g., technology stack, platform, security)
        2.5. Assumptions and Dependencies

    3.  SYSTEM FEATURES
        (Break down the requirements into specific, detailed features based on the conversation.)
        3.1. Feature 1: [Name of Feature]
             - Description: ...
             - Functional Requirements: ...
        3.2. Feature 2: [Name of Feature]
             - Description: ...
             - Functional Requirements: ...
        (Continue for all major features)

    4.  NON-FUNCTIONAL REQUIREMENTS
        4.1. Performance
        4.2. Security
        4.3. Usability
        4.4. Reliability

    5.  APPENDICES (Optional)
        (Add definitions, acronyms, or abbreviations if inferred from the context.)

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
        "conversation": conversation
    })

    clean_response = cleanup_text(response)
    return clean_response
