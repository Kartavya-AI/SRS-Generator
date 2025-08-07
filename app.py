import streamlit as st
from tool import generate_srs, generate_questions
from fpdf import FPDF
from gtts import gTTS
import io
import os
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder

st.set_page_config(layout="wide", page_title="Conversational SRS Agent")

if 'stage' not in st.session_state:
    st.session_state.stage = 'initial_input'
if 'srs_content' not in st.session_state:
    st.session_state.srs_content = ""
if 'requirements_text' not in st.session_state:
    st.session_state.requirements_text = ""
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = ""

with st.sidebar:
    st.header("Configuration")
    gemini_api_key_input = st.text_input("Enter your Gemini API Key", type="password")
    if gemini_api_key_input:
        st.session_state.gemini_api_key = gemini_api_key_input

    st.header("Choose Your Specialist")
    specialist = st.selectbox(
        "Select the type of project:",
        ("AI/ML Specialist", "Android Specialist", "iOS Specialist", "Full Stack Web Specialist", "Game Development Specialist", "Data Science Specialist"),
        key='specialist_selector'
    )

    st.header("Your Requirements")
    st.write("Select the language for voice input:")
    lang_options = {
        "English (US)": "en-US",
        "Hindi (India)": "hi-IN",
        "Tamil (India)": "ta-IN",
        "Malayalam (India)": "ml-IN"
    }
    selected_lang_name = st.selectbox("Language:", options=list(lang_options.keys()))
    selected_lang_code = lang_options[selected_lang_name]

    if st.session_state.stage == 'initial_input':
        st.write("Record your initial requirements:")
        audio_info = mic_recorder(
            start_prompt="🔴 Start Recording",
            stop_prompt="⏹️ Stop Recording",
            key='recorder'
        )

        if audio_info and audio_info.get('bytes'):
            st.write("Transcribing audio...")
            recognizer = sr.Recognizer()
            try:
                sample_width = audio_info.get('sample_width', 2)
                audio_data = sr.AudioData(
                    audio_info['bytes'],
                    audio_info['sample_rate'],
                    sample_width
                )
                transcribed_text = recognizer.recognize_google(
                    audio_data,
                    language=selected_lang_code
                )
                st.session_state.requirements_text = transcribed_text
                st.success("Transcription complete.")
                st.session_state.stage = 'review_requirements'
            except sr.UnknownValueError:
                st.error("Could not understand the audio. Please try again.")
            except sr.RequestError as e:
                st.error(f"Speech recognition service error: {e}")

        requirements = st.text_area(
            "Describe your project requirements (or edit transcribed text):",
            value=st.session_state.requirements_text,
            height=250
        )
        st.session_state.requirements_text = requirements

        if st.button("Start Clarification", use_container_width=True):
            if not st.session_state.gemini_api_key:
                st.error("Please enter your Gemini API Key to begin.")
            elif not st.session_state.requirements_text:
                st.error("Please provide an initial project description.")
            else:
                with st.spinner("Agent is thinking of questions..."):
                    initial_req = f"User's Initial Requirement: {st.session_state.requirements_text}"
                    st.session_state.conversation_history.append(initial_req)
                    st.session_state.questions = generate_questions(
                        st.session_state.gemini_api_key, specialist, st.session_state.requirements_text
                    )
                    if st.session_state.questions:
                        st.session_state.stage = 'asking_questions'
                        st.rerun()
                    else:
                        st.error("The agent could not generate questions. Please try refining your initial description.")

st.title("SRS Generator Agent")

if st.session_state.stage == 'initial_input':
    st.write("This agent helps you create a Software Requirements Specification (SRS) by having a conversation to understand your needs.")
    st.info("Please fill in your API key, choose a specialist, and provide your initial project description in the sidebar to get started.")

elif st.session_state.stage == 'asking_questions':
    st.header("Let's Clarify Your Requirements")
    st.write("Please answer the following questions to help me build a detailed SRS.")

    for entry in st.session_state.conversation_history:
        if entry.startswith("User's Initial Requirement:") or entry.startswith("User Answer:"):
            st.chat_message("user").write(entry.split(":", 1)[1].strip())
        else:
            st.chat_message("assistant").write(entry.split(":", 1)[1].strip())

    index = st.session_state.current_question_index
    if index < len(st.session_state.questions):
        current_question = st.session_state.questions[index]
        st.chat_message("assistant").write(current_question)
        try:
            tts_lang = selected_lang_code.split('-')[0]
            tts = gTTS(text=current_question, lang=tts_lang)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')
        except Exception as e:
            st.error(f"Could not generate audio for the question: {e}")

        user_answer = st.text_input("Your Answer:", key=f"answer_{index}")

        if st.button("Submit Answer", key=f"submit_{index}"):
            if user_answer:
                st.session_state.conversation_history.append(f"Agent Question: {current_question}")
                st.session_state.conversation_history.append(f"User Answer: {user_answer}")
                st.session_state.current_question_index += 1
                st.rerun()
            else:
                st.warning("Please provide an answer.")
    else:
        st.success("Thank you! All questions have been answered. Generating the final document now.")
        st.session_state.stage = 'generating_srs'
        st.rerun()

elif st.session_state.stage == 'generating_srs':
    st.header("Generating Final SRS Document")
    with st.spinner(f"The {specialist} is drafting the final SRS based on our conversation..."):
        full_conversation = "\n".join(st.session_state.conversation_history)
        try:
            srs_result = generate_srs(st.session_state.gemini_api_key, specialist, full_conversation)
            st.session_state.srs_content = srs_result
            st.session_state.stage = 'display_srs'
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred during final SRS generation: {e}")
            st.session_state.stage = 'initial_input'

elif st.session_state.stage == 'display_srs':
    st.header("Generated Software Requirements Specification (SRS)")
    srs_edited = st.text_area(
        "You can review and edit the final SRS below:",
        value=st.session_state.srs_content,
        height=600
    )
    if srs_edited:
        st.session_state.srs_content = srs_edited

    if st.session_state.srs_content:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Listen to the SRS")
            with st.spinner("Generating audio..."):
                try:
                    tts = gTTS(text=st.session_state.srs_content, lang='en')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, format='audio/mp3')
                except Exception as e:
                    st.error(f"Failed to generate audio: {e}")
        with col2:
            st.subheader("Download SRS")
            def create_pdf(text):
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
                pdf.set_font('DejaVu', '', 12)
                pdf.multi_cell(0, 10, text)
                return pdf.output(dest='S').encode('latin-1')
            
            if not os.path.exists("DejaVuSans.ttf"):
                 st.warning("To enable PDF download, please add the 'DejaVuSans.ttf' font file to your project directory.")
            else:
                try:
                    pdf_data = create_pdf(st.session_state.srs_content)
                    st.download_button(
                        label="Download SRS as PDF",
                        data=pdf_data,
                        file_name="SRS_Document.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Failed to generate PDF: {e}")

st.markdown("---")
st.info("Note: Voice input requires microphone permissions. Accuracy depends on various factors.")