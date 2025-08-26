from fastapi import FastAPI, UploadFile, File, HTTPException , Form
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
import uvicorn
from dotenv import load_dotenv

# Langchain imports
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

app = FastAPI(title="Mental Health Assessment Chatbot", version="1.0.0")

# Global variables for session management
user_sessions = {}

# Pydantic models
class ChatMessage(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    chat_count: int
    assessment_triggered: bool = False
    assessment_suggestion_count: int = 0

class AssessmentAnswer(BaseModel):
    user_id: str
    question_id: int
    audio_file: UploadFile

class ReportRequest(BaseModel):
    user_id: str

class AssessmentResponse(BaseModel):
    user_id: str
    accept_assessment: bool

# Initialize components
class MentalHealthChatbot:
    def __init__(self):
        # Initialize Groq LLM
        self.llm = ChatGroq(
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7
        )
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEndpointEmbeddings(
            model='sentence-transformers/all-mpnet-base-v2',
            task="feature-extraction",
            huggingfacehub_api_token=os.getenv('HUGGINGFACE_API_KEY'))
        
        
        # Load pre-built FAISS vector store
        self.vector_store = FAISS.load_local(
            "mhguide_db", 
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Load assessment questions
        with open('questionnaire.json', 'r') as f:
            self.questions = json.load(f)
        
        # Chat prompt template (only last 3 conversations)
        self.chat_prompt = PromptTemplate(
            input_variables=["context", "chat_history", "user_message", "chat_count", "assessment_declined"],
            template="""
            You are a compassionate mental health assistant. Use the following context to provide helpful, supportive responses.
            
            Context from knowledge base:
            {context}
            
            Previous conversation (last 3 exchanges):
            {chat_history}
            
            Current chat count: {chat_count}
            Assessment previously declined: {assessment_declined}
            
            User message: {user_message}
            
            Guidelines:
            1. Provide a supportive, informative response that is conversational and empathetic.
            2. If this is the 3rd or 4th interaction AND assessment hasn't been declined, gently suggest taking a mental health assessment to get more personalized insights.
            3. If the user has already declined the assessment, continue with regular supportive conversation without mentioning assessment again.
            4. Keep your response natural and don't force the assessment suggestion.
            5. The assessment suggestion should feel organic to the conversation flow.
            6. Keep your responses consize and medium to short sized.
            
            Response:"""
        )
        
        # Report generation prompt (full history)
        self.report_prompt = PromptTemplate(
            input_variables=["full_chat_history", "assessment_responses"],
            template="""
            Generate a comprehensive mental health assessment report based on the following information:
            
            Complete Chat History:
            {full_chat_history}
            
            Assessment Responses:
            {assessment_responses}
            
            Please provide a structured report with the following sections:
            
            # Mental Health Assessment Report
            
            ## Executive Summary
            Brief overview of the assessment findings and overall mental health status
            
            ## Chat Analysis
            Analysis of conversation patterns, concerns expressed, and emotional themes throughout the entire conversation
            
            ## Assessment Results
            Detailed analysis of questionnaire responses with specific insights
            
            ## Risk Assessment
            Evaluation of potential mental health risks (Low/Medium/High) with specific reasoning
            
            ## Key Findings
            Most significant observations and patterns identified
            
            ## Recommendations
            Specific, actionable recommendations for mental health support and self-care
            
            ## Professional Resources
            Suggested professional resources, therapy options, and next steps
            
            ## Self-Care Strategies
            Practical daily strategies and coping mechanisms
            
            Keep the tone professional yet compassionate. Focus on providing actionable insights and hope.
            """
        )

    def get_relevant_context(self, query: str) -> str:
        """Retrieve relevant context from vector store"""
        try:
            docs = self.vector_store.similarity_search(query, k=3)
            context = "\n".join([doc.page_content for doc in docs])
            return context
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return ""

    def process_audio_to_text(self, audio_file: UploadFile) -> str:
        """Convert audio to text using Groq Whisper"""
        try:
            # Save uploaded audio temporarily
            temp_path = f"temp_audio_{audio_file.filename}"
            with open(temp_path, "wb") as buffer:
                buffer.write(audio_file.file.read())
            
            # Initialize Groq client for Whisper
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            with open(temp_path, "rb") as audio:
                transcription = client.audio.transcriptions.create(
                    file=audio,
                    model="whisper-large-v3"
                )
            
            # Clean up temp file
            os.remove(temp_path)
            
            return transcription.text
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            return ""

# Initialize chatbot
chatbot = MentalHealthChatbot()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """Main chat endpoint"""
    try:
        user_id = message.user_id
        user_message = message.message
        
        # Initialize user session if not exists
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                "chat_history": [],
                "chat_count": 0,
                "assessment_responses": [],
                "assessment_declined": False,
                "assessment_suggestion_count": 0,
                "assessment_offered": False
            }
        
        session = user_sessions[user_id]
        session["chat_count"] += 1
        
        # Get relevant context
        context = chatbot.get_relevant_context(user_message)
        
        # Prepare chat history string (only last 3 exchanges for system prompt)
        recent_chat_history = "\n".join([
            f"User: {msg['user']}\nAssistant: {msg['assistant']}" 
            for msg in session["chat_history"][-3:]
        ])
        
        # Check if we should suggest assessment (3-4 chats, not declined, not already offered)
        should_suggest_assessment = (
            session["chat_count"] >= 3 and 
            session["chat_count"] <= 4 and 
            not session["assessment_declined"] and
            not session["assessment_offered"]
        )
        
        # Generate response
        prompt = chatbot.chat_prompt.format(
            context=context,
            chat_history=recent_chat_history,
            user_message=user_message,
            chat_count=session["chat_count"],
            assessment_declined=session["assessment_declined"]
        )
        
        response = chatbot.llm.invoke([HumanMessage(content=prompt)])
        assistant_response = response.content
        
        # Update chat history
        session["chat_history"].append({
            "user": user_message,
            "assistant": assistant_response
        })
        
        # Determine if assessment should be triggered
        assessment_triggered = should_suggest_assessment
        if assessment_triggered:
            session["assessment_offered"] = True
            session["assessment_suggestion_count"] += 1
        
        return ChatResponse(
            response=assistant_response,
            chat_count=session["chat_count"],
            assessment_triggered=assessment_triggered,
            assessment_suggestion_count=session["assessment_suggestion_count"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/assessment_response")
async def handle_assessment_response(response: AssessmentResponse):
    """Handle user's response to assessment suggestion"""
    try:
        user_id = response.user_id
        
        if user_id not in user_sessions:
            raise HTTPException(status_code=404, detail="User session not found")
        
        session = user_sessions[user_id]
        
        if response.accept_assessment:
            # User accepted assessment
            return {"status": "assessment_accepted", "message": "Great! Let's proceed with the assessment."}
        else:
            # User declined assessment
            session["assessment_declined"] = True
            return {"status": "assessment_declined", "message": "No problem! We can continue our conversation. I'm here to help whenever you need support."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_questions/{user_id}")
async def get_assessment_questions(user_id: str):
    """Get assessment questions"""
    try:
        if user_id not in user_sessions:
            raise HTTPException(status_code=404, detail="User session not found")
        
        # Reset assessment responses for new attempt
        user_sessions[user_id]["assessment_responses"] = []
        
        return {"questions": chatbot.questions}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 1. Enhanced report generation endpoint with better error handling
@app.post("/generate_report")
async def generate_comprehensive_report(request: ReportRequest):
    """Generate final mental health assessment report"""
    try:
        user_id = request.user_id
        
        print(f"=== REPORT GENERATION STARTED ===")
        print(f"User ID received: {user_id}")
        print(f"Current user_sessions keys: {list(user_sessions.keys())}")
        
        if user_id not in user_sessions:
            print(f"ERROR: User session not found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="User session not found")
        
        session = user_sessions[user_id]
        
        print(f"Session found - chat_count: {session['chat_count']}, assessment_responses: {len(session['assessment_responses'])}")
        print(f"Chat history length: {len(session['chat_history'])}")
        
        # Validate we have data to generate report from
        if not session["chat_history"] and not session["assessment_responses"]:
            print("ERROR: No conversation or assessment data found")
            raise HTTPException(status_code=400, detail="No conversation or assessment data found")
        
        # Prepare FULL chat history for report
        full_chat_history_str = "\n".join([
            f"User: {msg['user']}\nAssistant: {msg['assistant']}" 
            for msg in session["chat_history"]
        ])
        
        # Prepare assessment responses
        assessment_str = "\n".join([
            f"Q{resp['question_id'] + 1}: {resp['question']}\nAnswer: {resp['answer']}\n"
            for resp in session["assessment_responses"]
        ])
        
        print(f"Full chat history length: {len(full_chat_history_str)}")
        print(f"Assessment responses length: {len(assessment_str)}")
        
        # Handle case where no assessment was taken
        if not assessment_str:
            assessment_str = "No formal assessment was completed. Analysis based on chat conversation only."
        
        # Generate comprehensive report using full history
        report_prompt = chatbot.report_prompt.format(
            full_chat_history=full_chat_history_str,
            assessment_responses=assessment_str
        )
        
        print("Calling LLM for report generation...")
        print(f"Prompt length: {len(report_prompt)}")
        
        try:
            report_response = chatbot.llm.invoke([HumanMessage(content=report_prompt)])
            comprehensive_report = report_response.content
            print(f"Report generated successfully. Length: {len(comprehensive_report)}")
        except Exception as llm_error:
            print(f"LLM Error: {str(llm_error)}")
            raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(llm_error)}")
        
        response_data = {
            "user_id": user_id,
            "report": comprehensive_report,
            "chat_count": session["chat_count"],
            "assessment_completed": len(session["assessment_responses"]),
            "total_chat_exchanges": len(session["chat_history"]),
            "status": "success"
        }
        
        print(f"Response data prepared. Report length: {len(comprehensive_report)}")
        print(f"=== REPORT GENERATION COMPLETED ===")
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"UNEXPECTED ERROR in generate_report: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

# 2. Add a debug endpoint to check session data
@app.get("/debug_session/{user_id}")
async def debug_session(user_id: str):
    """Debug endpoint to check session data"""
    if user_id not in user_sessions:
        return {"error": "Session not found"}
    
    session = user_sessions[user_id]
    return {
        "user_id": user_id,
        "chat_count": session["chat_count"],
        "chat_history_count": len(session["chat_history"]),
        "assessment_responses_count": len(session["assessment_responses"]),
        "assessment_declined": session.get("assessment_declined", False),
        "assessment_offered": session.get("assessment_offered", False),
        "sample_chat": session["chat_history"][-1] if session["chat_history"] else None,
        "sample_assessment": session["assessment_responses"][-1] if session["assessment_responses"] else None
    }

# 3. Enhanced submit_answer endpoint with better validation
@app.post("/submit_answer")
async def submit_audio_answer(
    user_id: str = Form(...),
    question_id: int = Form(...),
    audio_file: UploadFile = File(...)
):
    """Submit audio answer for assessment question"""
    try:
        print(f"Submitting answer for user {user_id}, question {question_id}")
        
        if user_id not in user_sessions:
            raise HTTPException(status_code=404, detail="User session not found")
        
        # Validate question_id
        if question_id < 0 or question_id >= len(chatbot.questions):
            raise HTTPException(status_code=400, detail="Invalid question ID")
        
        # Convert audio to text
        answer_text = chatbot.process_audio_to_text(audio_file)
        
        if not answer_text or answer_text.strip() == "":
            raise HTTPException(status_code=400, detail="Failed to process audio or audio was empty")
        
        # Store the response
        session = user_sessions[user_id]
        
        # Check if answer already exists for this question and update it
        existing_answer = None
        for i, resp in enumerate(session["assessment_responses"]):
            if resp["question_id"] == question_id:
                existing_answer = i
                break
        
        answer_data = {
            "question_id": question_id,
            "question": chatbot.questions[question_id]["question"],
            "answer": answer_text.strip()
        }
        
        if existing_answer is not None:
            session["assessment_responses"][existing_answer] = answer_data
            print(f"Updated existing answer for question {question_id}")
        else:
            session["assessment_responses"].append(answer_data)
            print(f"Added new answer for question {question_id}")
        
        print(f"Total assessment responses: {len(session['assessment_responses'])}")
        
        return {
            "status": "success",
            "transcribed_text": answer_text.strip(),
            "question_id": question_id,
            "total_responses": len(session["assessment_responses"])
        }
        
    except Exception as e:
        print(f"Error in submit_answer: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session_status/{user_id}")
async def get_session_status(user_id: str):
    """Get current session status"""
    if user_id not in user_sessions:
        return {"exists": False}
    
    session = user_sessions[user_id]
    return {
        "exists": True,
        "chat_count": session["chat_count"],
        "assessment_responses_count": len(session["assessment_responses"]),
        "ready_for_assessment": session["chat_count"] >= 3 and not session["assessment_declined"],
        "assessment_declined": session.get("assessment_declined", False),
        "assessment_offered": session.get("assessment_offered", False)
    }

@app.delete("/clear_session/{user_id}")
async def clear_user_session(user_id: str):
    """Clear user session data"""
    if user_id in user_sessions:
        del user_sessions[user_id]
        return {"status": "session cleared"}
    return {"status": "session not found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)