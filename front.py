import streamlit as st
import requests
import json
import io
import time
from audio_recorder_streamlit import audio_recorder
import uuid

# Configuration
API_BASE_URL = "https://mental-health-backend-08bz.onrender.com"  # Change this to your Docker container URL if needed
HEADERS = {"Content-Type": "application/json"}

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'assessment_mode' not in st.session_state:
    st.session_state.assessment_mode = False
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'assessment_complete' not in st.session_state:
    st.session_state.assessment_complete = False
if 'show_assessment_prompt' not in st.session_state:
    st.session_state.show_assessment_prompt = False
if 'assessment_declined' not in st.session_state:
    st.session_state.assessment_declined = False
if 'current_answer_submitted' not in st.session_state:
    st.session_state.current_answer_submitted = False
if 'last_transcription' not in st.session_state:
    st.session_state.last_transcription = ""
if 'streaming_new_message' not in st.session_state:
    st.session_state.streaming_new_message = False
if 'generated_report' not in st.session_state:
    st.session_state.generated_report = None
if 'report_generation_in_progress' not in st.session_state:
    st.session_state.report_generation_in_progress = False

# Page configuration
st.set_page_config(
    page_title="Mental Health Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 300;
        letter-spacing: 1px;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        border: 1px solid #495057;
    }
    .user-message {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-left: 4px solid #007bff;
    }
    .assistant-message {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-left: 4px solid #28a745;
    }
    .assessment-card {
        background-color: #000000 !important;
        color: #ffffff !important;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #495057;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(255,255,255,0.1);
    }
    .assessment-prompt {
        background-color: #000000 !important;
        color: #ffffff !important;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #007bff;
        margin: 1rem 0;
    }
    .success-message {
        background-color: #000000 !important;
        color: #28a745 !important;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
        border: 1px solid #28a745;
    }
    .declined-message {
        background-color: #000000 !important;
        color: #ffc107 !important;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
        border: 1px solid #ffc107;
    }
    .debug-info {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #495057;
        font-family: monospace;
        font-size: 0.8rem;
    }
    .report-container {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #404040;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 20px 0;
    }
    .stTextInput > div > div > input {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #495057 !important;
    }
    .stTextArea > div > div > textarea {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #495057 !important;
    }
    .stSelectbox > div > div > select {
        background-color: #000000 !important;
        color: #ffffff !important;
    }
    .sidebar-section {
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 6px;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    /* Chat input styling */
    .stChatInput > div > div > div > div > div {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #495057 !important;
    }
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background-color: #007bff !important;
    }
    .error-container {
        background-color: #2d1b1b;
        color: #ff6b6b;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #ff6b6b;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

def stream_response(text):
    """Display text with typing effect"""
    placeholder = st.empty()
    displayed_text = ""
    
    for char in text:
        displayed_text += char
        placeholder.markdown(f'<div class="chat-message assistant-message"><strong>Assistant:</strong> {displayed_text}</div>', 
                           unsafe_allow_html=True)
        time.sleep(0.02)  # Adjust speed as needed
    
    return displayed_text

# API Helper Functions
def test_api_connection():
    """Test API connection"""
    try:
        response = requests.get(f"{API_BASE_URL}/session_status/{st.session_state.user_id}", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_session_status():
    """Get current session status"""
    try:
        response = requests.get(f"{API_BASE_URL}/session_status/{st.session_state.user_id}")
        if response.status_code == 200:
            return response.json()
        return {"exists": False}
    except requests.exceptions.RequestException:
        st.error("Cannot connect to the API. Make sure the Docker container is running.")
        return {"exists": False}

def debug_session():
    """Debug session data"""
    try:
        response = requests.get(f"{API_BASE_URL}/debug_session/{st.session_state.user_id}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Debug failed: {response.status_code}", "response_text": response.text}
    except Exception as e:
        return {"error": str(e)}

def send_chat_message(message):
    """Send chat message to API"""
    try:
        payload = {
            "user_id": st.session_state.user_id,
            "message": message
        }
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def send_assessment_response(accept_assessment):
    """Send user's response to assessment suggestion"""
    try:
        payload = {
            "user_id": st.session_state.user_id,
            "accept_assessment": accept_assessment
        }
        response = requests.post(f"{API_BASE_URL}/assessment_response", json=payload, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {str(e)}")
        return None

def get_assessment_questions():
    """Get assessment questions from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/get_questions/{st.session_state.user_id}")
        if response.status_code == 200:
            return response.json()["questions"]
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching questions: {str(e)}")
        return []

def submit_audio_answer(question_id, audio_bytes):
    """Submit audio answer to API with enhanced error handling"""
    try:
        if not audio_bytes:
            st.error("No audio data received")
            return None
            
        # Debug logging
        st.write(f"DEBUG: Submitting audio for question {question_id}")
        st.write(f"DEBUG: Audio bytes length: {len(audio_bytes) if audio_bytes else 0}")
        
        files = {
            "audio_file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")
        }
        data = {
            "user_id": st.session_state.user_id,
            "question_id": question_id
        }
        
        st.write(f"DEBUG: Making request to {API_BASE_URL}/submit_answer")
        
        response = requests.post(
            f"{API_BASE_URL}/submit_answer", 
            files=files, 
            data=data, 
            timeout=30
        )
        
        st.write(f"DEBUG: Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            st.write(f"DEBUG: Response data: {result}")
            return result
        else:
            error_text = response.text
            st.error(f"Error submitting answer: {response.status_code}")
            st.write(f"DEBUG: Error response: {error_text}")
            try:
                error_json = response.json()
                st.write(f"DEBUG: Error details: {error_json}")
            except:
                pass
            return None
            
    except requests.exceptions.ConnectionError as e:
        st.error("Cannot connect to the backend API. Please ensure the server is running.")
        st.write(f"DEBUG: Connection error: {str(e)}")
        return None
    except requests.exceptions.Timeout as e:
        st.error("Request timed out. Please try again.")
        st.write(f"DEBUG: Timeout error: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {str(e)}")
        st.write(f"DEBUG: Request exception: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        st.write(f"DEBUG: Unexpected error: {str(e)}")
        import traceback
        st.write("DEBUG: Full traceback:")
        st.code(traceback.format_exc())
        return None

def generate_report():
    """Generate comprehensive report"""
    try:
        payload = {"user_id": st.session_state.user_id}
        
        response = requests.post(
            f"{API_BASE_URL}/generate_report", 
            json=payload, 
            headers=HEADERS, 
            timeout=120  # Increased timeout for report generation
        )
        
        if response.status_code == 200:
            report_data = response.json()
            
            # Validate report data
            if "report" in report_data and report_data["report"]:
                if len(str(report_data["report"]).strip()) > 50:
                    return report_data
                else:
                    st.error("Generated report is too short or empty")
                    return None
            else:
                st.error("Report data missing 'report' field")
                return None
        else:
            error_msg = f"Error generating report: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                st.error(f"{error_msg}\nDetails: {error_detail.get('detail', 'Unknown error')}")
            except:
                st.error(f"{error_msg}\nResponse: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Report generation timed out. The AI service might be overloaded. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend API. Please ensure the server is running.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during report generation: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

def validate_report_data():
    """Validate data before report generation"""
    try:
        debug_data = debug_session()
        
        if "error" in debug_data:
            st.error(f"Session validation failed: {debug_data['error']}")
            return False
        
        chat_count = debug_data.get('chat_history_count', 0)
        assessment_count = debug_data.get('assessment_responses_count', 0)
        
        if chat_count == 0:
            st.error("No chat history found. Please have a conversation first.")
            return False
        
        if assessment_count == 0:
            st.warning("No assessment responses found. Report will be based on chat history only.")
        
        st.success(f"Data validation passed: {chat_count} chat messages, {assessment_count} assessment responses")
        return True
        
    except Exception as e:
        st.error(f"Validation error: {str(e)}")
        return False

def clear_session():
    """Clear user session"""
    try:
        response = requests.delete(f"{API_BASE_URL}/clear_session/{st.session_state.user_id}")
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def is_assessment_complete():
    """Check if assessment is truly complete"""
    if not st.session_state.questions:
        return False
    
    session_status = get_session_status()
    expected_responses = len(st.session_state.questions)
    actual_responses = session_status.get('assessment_responses_count', 0)
    
    return actual_responses >= expected_responses

# Main App
def main():
    st.markdown('<h1 class="main-header">Mental Health Assessment Platform</h1>', unsafe_allow_html=True)
    
    # API Connection Check
    if not test_api_connection():
        st.error("Cannot connect to backend API. Please ensure the server is running on http://localhost:8000")
        st.info("To start the backend server, run: `uvicorn main:app --host 0.0.0.0 --port 8000`")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("Session Information")
        session_status = get_session_status()
        
        if session_status.get("exists", False):
            st.success("Session Active")
            st.info(f"Chat Messages: {session_status.get('chat_count', 0)}")
            st.info(f"Assessment Responses: {session_status.get('assessment_responses_count', 0)}")
            
            if session_status.get('ready_for_assessment', False) and not session_status.get('assessment_declined', False):
                st.warning("Assessment Available")
            elif session_status.get('assessment_declined', False):
                st.info("Assessment Declined - Continuing Chat")
        else:
            st.info("New Session")
        
        st.divider()
        
        # Debug Panel
        with st.expander("Debug Panel"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Check Session", key="debug_session_btn"):
                    debug_info = debug_session()
                    st.json(debug_info)
            
            with col2:
                if st.button("API Status", key="api_status_btn"):
                    try:
                        response = requests.get(f"{API_BASE_URL}/")
                        st.success(f"API Online: {response.status_code}")
                    except:
                        st.error("API Offline")
            
            st.write("**Session State:**")
            st.write(f"User ID: {st.session_state.user_id[:8]}...")
            st.write(f"Assessment Mode: {st.session_state.assessment_mode}")
            st.write(f"Assessment Complete: {st.session_state.assessment_complete}")
            st.write(f"Current Question: {st.session_state.current_question}")
            st.write(f"Questions Loaded: {len(st.session_state.questions)}")
            st.write(f"Report Generated: {st.session_state.generated_report is not None}")
        
        st.divider()
        
        if st.button("Clear Session", type="secondary"):
            with st.spinner("Clearing session..."):
                if clear_session():
                    st.session_state.clear()
                    st.success("Session cleared!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to clear session")
        
        st.divider()
        st.markdown("### Process Overview:")
        st.markdown("""
        1. **Chat** with the AI assistant (3-4 messages)
        2. **Assessment** will be offered when appropriate
        3. Choose to **accept or decline** the assessment
        4. If accepted, answer questions using **voice recordings**
        5. Receive a **comprehensive report**
        """)

    # Main Content Area
    if not st.session_state.assessment_mode and not st.session_state.assessment_complete:
        # Chat Mode
        st.header("AI Assistant Chat")
        
        # Display chat history
        for message in st.session_state.chat_history[:-1]:  # All messages except the last one
            with st.container():
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {message["user"]}</div>', 
                           unsafe_allow_html=True)
                st.markdown(f'<div class="chat-message assistant-message"><strong>Assistant:</strong> {message["assistant"]}</div>', 
                           unsafe_allow_html=True)
        
        # Handle the latest message separately
        if st.session_state.chat_history and st.session_state.streaming_new_message:
            latest_message = st.session_state.chat_history[-1]
            with st.container():
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {latest_message["user"]}</div>', 
                           unsafe_allow_html=True)
                stream_response(latest_message["assistant"])
                st.session_state.streaming_new_message = False
        elif st.session_state.chat_history:
            # Display the last message normally if not streaming
            latest_message = st.session_state.chat_history[-1]
            with st.container():
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {latest_message["user"]}</div>', 
                           unsafe_allow_html=True)
                st.markdown(f'<div class="chat-message assistant-message"><strong>Assistant:</strong> {latest_message["assistant"]}</div>', 
                           unsafe_allow_html=True)
        
        # Show assessment prompt if triggered and not yet responded to
        if st.session_state.show_assessment_prompt and not st.session_state.assessment_declined:
            st.markdown(f'<div class="assessment-prompt">'
                      f'<h3>Assessment Recommendation</h3>'
                      f'<p>Based on our conversation, would you like to take a mental health assessment? '
                      f'This could provide more personalized insights and recommendations tailored to your needs.</p>'
                      f'<p><em>This is completely optional and you can continue chatting if you prefer.</em></p>'
                      f'</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Start Assessment", type="primary", key="accept_assessment"):
                    with st.spinner("Setting up assessment..."):
                        response = send_assessment_response(True)
                        if response:
                            st.session_state.show_assessment_prompt = False
                            st.session_state.assessment_mode = True
                            st.session_state.questions = get_assessment_questions()
                            st.success("Assessment will begin!")
                            time.sleep(1)
                            st.rerun()
            
            with col2:
                if st.button("No, Continue Chatting", type="secondary", key="decline_assessment"):
                    response = send_assessment_response(False)
                    if response:
                        st.session_state.show_assessment_prompt = False
                        st.session_state.assessment_declined = True
                        st.markdown(f'<div class="declined-message">'
                                  f'No problem! We can continue our conversation. The assessment option won\'t be offered again.'
                                  f'</div>', unsafe_allow_html=True)
                        time.sleep(2)
                        st.rerun()
        
        # Chat input
        user_input = st.chat_input("Type your message here...")
        
        if user_input:
            with st.spinner("Processing your message..."):
                response = send_chat_message(user_input)
                
                if response:
                    # Add to chat history
                    st.session_state.chat_history.append({
                        "user": user_input,
                        "assistant": response["response"]
                    })
                    
                    # Set flag to stream the new message
                    st.session_state.streaming_new_message = True
                    
                    # Check if assessment should be triggered
                    if response.get("assessment_triggered", False) and not st.session_state.assessment_declined:
                        st.session_state.show_assessment_prompt = True
                    
                    st.rerun()
    
    elif st.session_state.assessment_mode:
        # Assessment Mode
        st.header("Mental Health Assessment")
        
        if not st.session_state.questions:
            st.session_state.questions = get_assessment_questions()
        
        if st.session_state.questions:
            current_q = st.session_state.current_question
            total_q = len(st.session_state.questions)
            
            # Progress bar
            progress = current_q / total_q if total_q > 0 else 0
            st.progress(progress, text=f"Question {current_q + 1} of {total_q}")
            
            if current_q < total_q:
                question = st.session_state.questions[current_q]
                
                st.markdown(f'<div class="assessment-card">'
                          f'<h3>Question {current_q + 1}</h3>'
                          f'<p style="font-size: 1.2rem;">{question["question"]}</p>'
                          f'</div>', unsafe_allow_html=True)
                
                st.info("Click the microphone button below to record your answer")
                
                # Audio recorder
                audio_bytes = audio_recorder(
                    text="Record Answer",
                    recording_color="#e74c3c",
                    neutral_color="#34495e",
                    icon_name="microphone",
                    icon_size="2x",
                    key=f"audio_recorder_{current_q}"
                )
                
                # Show transcription if answer was submitted
                if st.session_state.current_answer_submitted and st.session_state.last_transcription:
                    st.markdown(f'<div class="success-message">'
                              f'<strong>Your Answer:</strong> {st.session_state.last_transcription}'
                              f'</div>', unsafe_allow_html=True)
                
                # Handle audio submission - Fixed logic
                if audio_bytes is not None and not st.session_state.current_answer_submitted:
                    # Store the audio bytes immediately to prevent loss on rerun
                    st.session_state[f"temp_audio_{current_q}"] = audio_bytes
                    
                    with st.spinner("Processing your answer..."):
                        try:
                            result = submit_audio_answer(current_q, audio_bytes)
                            
                            if result and "transcribed_text" in result:
                                st.session_state.current_answer_submitted = True
                                st.session_state.last_transcription = result.get("transcribed_text", "")
                                st.success(f"Answer recorded for question {current_q + 1}")
                                # Clean up temp audio
                                if f"temp_audio_{current_q}" in st.session_state:
                                    del st.session_state[f"temp_audio_{current_q}"]
                                st.rerun()
                            else:
                                st.error("Failed to process your answer. Please try recording again.")
                        except Exception as e:
                            st.error(f"Error processing audio: {str(e)}")

                # Alternative: Manual retry button if audio processing fails
                if not st.session_state.current_answer_submitted and f"temp_audio_{current_q}" in st.session_state:
                    if st.button("Retry Audio Processing", key=f"retry_audio_{current_q}"):
                        with st.spinner("Retrying audio processing..."):
                            try:
                                stored_audio = st.session_state[f"temp_audio_{current_q}"]
                                result = submit_audio_answer(current_q, stored_audio)
                                
                                if result and "transcribed_text" in result:
                                    st.session_state.current_answer_submitted = True
                                    st.session_state.last_transcription = result.get("transcribed_text", "")
                                    st.success(f"Answer recorded for question {current_q + 1}")
                                    del st.session_state[f"temp_audio_{current_q}"]
                                    st.rerun()
                                else:
                                    st.error("Failed to process your answer. Please record again.")
                            except Exception as e:
                                st.error(f"Error processing audio: {str(e)}")
                
                # Navigation buttons
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    # Previous question button (only show if not on first question)
                    if current_q > 0:
                        if st.button("Previous", key=f"prev_btn_{current_q}"):
                            st.session_state.current_question -= 1
                            st.session_state.current_answer_submitted = False
                            st.session_state.last_transcription = ""
                            st.rerun()
                
                with col3:
                    # Next question button
                    next_disabled = not (st.session_state.current_answer_submitted or st.session_state.last_transcription)
                    next_button_type = "primary" if not next_disabled else "secondary"
                    
                    if st.button("Next", key=f"next_btn_{current_q}", 
                                type=next_button_type, disabled=next_disabled):
                        if st.session_state.current_answer_submitted or st.session_state.last_transcription:
                            st.session_state.current_question += 1
                            st.session_state.current_answer_submitted = False
                            st.session_state.last_transcription = ""
                            st.rerun()
                        else:
                            st.warning("Please record an answer before proceeding to the next question.")
            else:
                # All questions completed - validate before showing completion
                session_status = get_session_status()
                assessment_count = session_status.get('assessment_responses_count', 0)
                
                if assessment_count >= total_q:
                    st.success("Assessment Complete!")
                    st.balloons()
                    st.markdown(f'<div class="success-message">'
                              f'<h3>All {total_q} questions completed successfully!</h3>'
                              f'<p>Responses recorded: {assessment_count}/{total_q}</p>'
                              f'<p>You can now generate your comprehensive mental health report.</p>'
                              f'</div>', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("Generate My Report", type="primary", key="generate_report_btn"):
                            st.session_state.assessment_complete = True
                            st.rerun()
                else:
                    st.warning(f"Assessment Incomplete: {assessment_count}/{total_q} responses recorded")
                    st.info("Please ensure all questions have been answered before generating the report.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Refresh Status", key="refresh_assessment_status"):
                            st.rerun()
                    with col2:
                        if st.button("Go Back", key="go_back_to_questions"):
                            st.session_state.current_question = max(0, total_q - 1)
                            st.rerun()
        else:
            st.error("Could not load assessment questions. Please try refreshing.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Retry Loading Questions"):
                    st.session_state.questions = get_assessment_questions()
                    st.rerun()
            with col2:
                if st.button("Back to Chat"):
                    st.session_state.assessment_mode = False
                    st.rerun()
    
    elif st.session_state.assessment_complete:
        # Report Generation and Display Mode
        st.header("Your Mental Health Report")
        
        # Check if report generation is in progress
        if st.session_state.report_generation_in_progress:
            st.info("Report generation is in progress. Please wait...")
            progress_bar = st.progress(0, text="Generating your comprehensive report...")
            
            # Simulate progress updates (you could make this more sophisticated)
            for i in range(1, 101, 10):
                progress_bar.progress(i, text=f"Processing... {i}%")
                time.sleep(0.1)
            
            progress_bar.empty()
            st.session_state.report_generation_in_progress = False
            st.rerun()
        
        # Check if we have a generated report
        if st.session_state.generated_report is None:
            st.info("Ready to generate your comprehensive mental health report.")
            
            # Validate data before allowing report generation
            if validate_report_data():
                st.markdown("""
                **Your report will include:**
                - Executive Summary of your mental health assessment
                - Analysis of your chat conversation patterns
                - Assessment questionnaire results analysis
                - Risk assessment and professional recommendations
                - Personalized self-care strategies
                - Resources for further support
                """)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("Generate Report", type="primary", key="start_report_generation", use_container_width=True):
                        st.session_state.report_generation_in_progress = True
                        
                        with st.spinner("Generating your report... This may take up to 2 minutes."):
                            try:
                                report_data = generate_report()
                                
                                if report_data and "report" in report_data:
                                    st.session_state.generated_report = report_data
                                    st.session_state.report_generation_in_progress = False
                                    st.success("Report generated successfully!")
                                    st.rerun()
                                else:
                                    st.session_state.report_generation_in_progress = False
                                    st.error("Failed to generate report. Please try again.")
                                    
                            except Exception as e:
                                st.session_state.report_generation_in_progress = False
                                st.error(f"Error generating report: {str(e)}")
                
                # Additional options while waiting for report generation
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Back to Assessment", key="back_to_assessment_from_report"):
                        st.session_state.assessment_complete = False
                        st.rerun()
                with col2:
                    if st.button("Start New Session", key="new_session_from_report"):
                        if clear_session():
                            st.session_state.clear()
                            st.success("Starting new session...")
                            st.rerun()
            else:
                st.error("Cannot generate report due to insufficient data.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Back to Assessment"):
                        st.session_state.assessment_complete = False
                        st.rerun()
                with col2:
                    if st.button("Start New Session"):
                        if clear_session():
                            st.session_state.clear()
                            st.rerun()
        else:
            # Display the generated report
            st.success("Your report is ready!")
            
            # Get report data
            report_data = st.session_state.generated_report
            report_content = report_data.get("report", "No report content available")
            
            # Display report in a nice container
            st.markdown("---")
            st.markdown("### Your Mental Health Assessment Report")
            
            with st.container():
                st.markdown('<div class="report-container">', unsafe_allow_html=True)
                st.markdown(report_content)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Display session statistics
            st.markdown("---")
            st.markdown("### Session Statistics")
            
            session_status = get_session_status()
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Chat Messages", session_status.get("chat_count", 0))
            with col2:
                st.metric("Assessment Responses", session_status.get("assessment_responses_count", 0))
            with col3:
                st.metric("Total Questions", len(st.session_state.questions))
            with col4:
                st.metric("Session ID", st.session_state.user_id[:8] + "...")
            
            # Action buttons
            st.markdown("---")
            st.markdown("### Actions")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Download report as text file
                report_filename = f"mental_health_report_{st.session_state.user_id[:8]}.txt"
                st.download_button(
                    label="Download Report",
                    data=report_content,
                    file_name=report_filename,
                    mime="text/plain",
                    type="primary",
                    help="Download your report as a text file"
                )
            
            with col2:
                if st.button("Regenerate Report", type="secondary"):
                    st.session_state.generated_report = None
                    st.info("Report cleared. You can now generate a new one.")
                    st.rerun()
            
            with col3:
                if st.button("Start New Session", type="secondary"):
                    if clear_session():
                        st.session_state.clear()
                        st.success("Starting new session...")
                        st.rerun()
                    else:
                        st.error("Failed to clear session")
            
            with col4:
                if st.button("Back to Chat", type="secondary"):
                    st.session_state.assessment_complete = False
                    st.session_state.assessment_mode = False
                    st.rerun()
            
            # Additional information and help
            st.markdown("---")
            
            with st.expander("Understanding Your Report"):
                st.markdown("""
                **Your mental health report includes:**
                
                - **Executive Summary**: Overview of your current mental health status
                - **Chat Analysis**: Insights from your conversation patterns
                - **Assessment Results**: Analysis of your questionnaire responses
                - **Risk Assessment**: Professional evaluation of potential concerns
                - **Key Findings**: Most important observations from your session
                - **Recommendations**: Personalized suggestions for your wellbeing
                - **Professional Resources**: Information about professional help options
                - **Self-Care Strategies**: Practical daily strategies you can implement
                
                **Important Notes:**
                - This report is for informational purposes and should not replace professional medical advice
                - If you're experiencing a mental health crisis, please contact emergency services or a mental health professional immediately
                - Consider sharing this report with a healthcare provider for professional interpretation
                """)
            
            with st.expander("Technical Details"):
                debug_info = debug_session()
                
                st.write("**Report Metadata:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.json({
                        "user_id": st.session_state.user_id,
                        "report_generated": True,
                        "report_length": len(report_content),
                        "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                
                with col2:
                    if "error" not in debug_info:
                        st.json(debug_info)
                    else:
                        st.error(f"Debug info error: {debug_info['error']}")
                
                with st.expander("Raw Report Data"):
                    st.json(report_data)
            
            with st.expander("Feedback"):
                st.markdown("**How was your experience?**")
                st.markdown("We're continuously improving this mental health assessment platform.")
                
                feedback_rating = st.select_slider(
                    "Rate your overall experience:",
                    options=["Very Poor", "Poor", "Fair", "Good", "Excellent"],
                    value="Good",
                    key="feedback_rating"
                )
                
                feedback_text = st.text_area(
                    "Additional comments (optional):",
                    placeholder="Share your thoughts about the assessment process, report quality, or suggestions for improvement...",
                    key="feedback_text"
                )
                
                if st.button("Submit Feedback", key="submit_feedback"):
                    st.success("Thank you for your feedback!")
                    st.balloons()

if __name__ == "__main__":

    main()
