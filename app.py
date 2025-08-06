# app.py
import streamlit as st
from tool import generate_srs
from fpdf import FPDF
from gtts import gTTS
import io
import os
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="SRS Generator Agent")

st.title("📝 SRS Generator Agent")
st.write("This agent helps you create a Software Requirements Specification (SRS) by collecting your requirements via voice.")

if 'srs_content' not in st.session_state:
    st.session_state.srs_content = ""
if 'requirements_text' not in st.session_state:
    st.session_state.requirements_text = ""

with st.sidebar:
    st.header("Configuration")
    gemini_api_key = st.text_input("Enter your Gemini API Key", type="password")

    st.header("Choose Your Specialist")
    specialist = st.selectbox(
        "Select the type of project:",
        ("AI/ML Specialist", "Android Specialist", "iOS Specialist", "Full Stack Web Specialist", "Game Development Specialist", "Data Science Specialist")
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

    st.write("Record your requirements:")
    audio_info = mic_recorder(
        start_prompt="🔴 Start Recording",
        stop_prompt="⏹️ Stop Recording",
        key='recorder'
    )

    if audio_info and audio_info['bytes']:
        st.write("Transcribing audio...")
        recognizer = sr.Recognizer()
        try:
            audio_data = sr.AudioData(audio_info['bytes'], audio_info['sample_rate'], 2)
            transcribed_text = recognizer.recognize_google(audio_data, language=selected_lang_code)
            st.session_state.requirements_text = transcribed_text
            st.success("Transcription complete.")
        except sr.UnknownValueError:
            st.error("Could not understand the audio. Please try again.")
        except sr.RequestError as e:
            st.error(f"Speech recognition service error; {e}")
        except Exception as e:
            st.error(f"An error occurred during transcription: {e}")

    requirements = st.text_area(
        "Describe your project requirements (or edit transcribed text):",
        value=st.session_state.requirements_text,
        height=250
    )
    st.session_state.requirements_text = requirements

    generate_button = st.button("Generate SRS Document", use_container_width=True)

st.header("Generated Software Requirements Specification (SRS)")

if generate_button:
    if not gemini_api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not requirements:
        st.error("Please enter your project requirements in the sidebar.")
    else:
        with st.spinner(f"Asking the {specialist} to draft the SRS..."):
            try:
                srs_result = generate_srs(gemini_api_key, specialist, requirements)
                st.session_state.srs_content = srs_result
                st.success("SRS document has been generated!")
            except Exception as e:
                st.error(f"An error occurred: {e}")

srs_edited = st.text_area(
    "You can review and edit the SRS below:",
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
                tts = gTTS(text=st.session_state.srs_content, lang='en', slow=False)
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp, format='audio/mp3', start_time=0)
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
        try:
            st.warning("PDF download for non-English text requires the 'DejaVuSans.ttf' font file to be in your project directory.")
            if os.path.exists("DejaVuSans.ttf"):
                pdf_data = create_pdf(st.session_state.srs_content)
                st.download_button(
                    label="Download SRS as PDF",
                    data=pdf_data,
                    file_name="SRS_Document.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.error("DejaVuSans.ttf not found. Please download it to enable PDF downloads.")
        except Exception as e:
            st.error(f"Failed to generate PDF: {e}")

st.markdown("---")
st.info("Note: Voice input requires microphone permissions. Accuracy depends on your browser's speech recognition engine.")
