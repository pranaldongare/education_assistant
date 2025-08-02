# ui/gradio_interface.py
import gradio as gr
import logging
from pathlib import Path
from typing import Optional

from services.tutor_service import tutor_service
from services.tts_service import tts_service
from config.settings import GRADES, SUBJECTS, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# Handler functions defined first
def update_topics(subject, grade):
    """Update topics dropdown based on subject and grade selection"""
    try:
        logger.info(f"update_topics called with subject='{subject}', grade='{grade}'")
        
        if not subject or not grade:
            logger.warning("Subject or grade not provided")
            return (
                gr.Dropdown(choices=[], interactive=False),
                gr.Markdown(value="", visible=False)
            )
        
        logger.info(f"Getting curriculum topics for subject='{subject}', grade='{grade}'")
        topics = tutor_service.get_curriculum_topics(subject, grade)
        logger.info(f"Retrieved topics: {topics}")
        
        topic_choices = list(topics.keys()) if topics else []
        logger.info(f"Topic choices: {topic_choices}")
        
        if not topic_choices:
            error_msg = f"No topics found for {subject} Grade {grade}. Please check your selection."
            logger.warning(error_msg)
            return (
                gr.Dropdown(choices=[], interactive=False),
                gr.Markdown(value=f"⚠️ {error_msg}", visible=True)
            )
        
        result = gr.Dropdown(
            choices=topic_choices,
            interactive=len(topic_choices) > 0,
            value=None
        )
        logger.info(f"Returning dropdown with {len(topic_choices)} choices")
        return (
            result,
            gr.Markdown(value="", visible=False)
        )
        
    except Exception as e:
        error_msg = f"Error loading topics: {str(e)}"
        logger.error(f"Error in update_topics: {e}", exc_info=True)
        return (
            gr.Dropdown(choices=[], interactive=False),
            gr.Markdown(value=f"❌ {error_msg}", visible=True)
        )

def update_subtopics(subject, grade, topic):
    """Update subtopics dropdown based on topic selection"""
    try:
        logger.info(f"update_subtopics called with subject='{subject}', grade='{grade}', topic='{topic}'")
        
        if not subject or not grade or not topic:
            logger.warning("Subject, grade, or topic not provided")
            return (
                gr.Dropdown(choices=[], interactive=False),
                gr.Markdown(value="", visible=False)
            )
        
        logger.info(f"Getting curriculum subtopics for subject='{subject}', grade='{grade}', topic='{topic}'")
        subtopics = tutor_service.get_curriculum_subtopics(subject, grade, topic)
        logger.info(f"Retrieved subtopics: {subtopics}")
        
        subtopic_choices = list(subtopics) if subtopics else []
        logger.info(f"Subtopic choices: {subtopic_choices}")
        
        if not subtopic_choices:
            error_msg = f"No subtopics found for topic '{topic}'. The topic may not have subtopics defined."
            logger.warning(error_msg)
            return (
                gr.Dropdown(choices=[], interactive=False),
                gr.Markdown(value=f"⚠️ {error_msg}", visible=True)
            )
        
        result = gr.Dropdown(
            choices=subtopic_choices,
            interactive=len(subtopic_choices) > 0,
            value=None
        )
        logger.info(f"Returning subtopic dropdown with {len(subtopic_choices)} choices")
        return (
            result,
            gr.Markdown(value="", visible=False)
        )
        
    except Exception as e:
        error_msg = f"Error loading subtopics: {str(e)}"
        logger.error(f"Error in update_subtopics: {e}", exc_info=True)
        return (
            gr.Dropdown(choices=[], interactive=False),
            gr.Markdown(value=f"❌ {error_msg}", visible=True)
        )

def handle_explanation(student_name, subject, grade, topic, subtopic, question_input, session_state, audio_state):
    """Handle explanation request"""
    try:
        if not all([subject, grade, topic]):
            return ERROR_MESSAGES["topic_selection"], session_state, audio_state
        
        # Create or get session
        if not session_state:
            session_state = tutor_service.create_session(
                student_name=student_name or "Student",
                grade=grade,
                subject=subject,
                topic=topic,
                subtopic=subtopic or "",
                session_type="explanation"
            )
        
        # Get explanation
        explanation = tutor_service.explain_topic(
            student_name=student_name,
            grade=grade,
            subject=subject,
            topic=topic,
            subtopic=subtopic or ""
        )
        
        return explanation, session_state, audio_state
        
    except Exception as e:
        logger.error(f"Explanation error: {e}")
        return ERROR_MESSAGES["server_error"], session_state, audio_state

def handle_tts(text, audio_state):
    """Handle text-to-speech conversion"""
    try:
        if not text or not text.strip():
            return None, "No text to convert to speech! 🎈", audio_state
        
        # Stop any existing audio
        if audio_state and audio_state.get('current_audio'):
            audio_state['current_audio'] = None
        
        # Generate new audio
        audio_file = tts_service.text_to_speech(text.strip())
        
        if audio_file and Path(audio_file).exists():
            # Update audio state
            new_audio_state = {
                'current_audio': audio_file,
                'text': text.strip()
            }
            
            return audio_file, "🎵 Audio ready! Click play to listen.", new_audio_state
        else:
            return None, "Sorry, couldn't generate audio right now! 🎈", audio_state
            
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None, "Audio generation failed! 🎈", audio_state

def stop_audio(audio_state):
    """Stop current audio playback"""
    try:
        if audio_state and audio_state.get('current_audio'):
            audio_state['current_audio'] = None
            return "🔇 Audio stopped!", audio_state
        return "No audio playing! 🎵", audio_state
    except Exception as e:
        logger.error(f"Stop audio error: {e}")
        return "Error stopping audio! 🎈", audio_state

# Create the Gradio interface
def create_interface():
    """Create the main Gradio interface"""
    
    # Custom CSS
    custom_css = """
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        text-align: center;
    }
    .success-message {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .error-message {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    """
    
    with gr.Blocks(
        title="🌈 AI Learning Adventure",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as interface:
        
        # Header
        gr.Markdown("""
        # 🌈 Welcome to Your AI Learning Adventure! 🚀
        
        *Your personal AI tutor is here to help you learn and grow!*
        """)
        
        # State variables
        session_state = gr.State(value=None)
        audio_state = gr.State(value=None)
        student_name_state = gr.State(value="Student")
        
        # Student setup section
        with gr.Row():
            with gr.Column(scale=1):
                student_name = gr.Textbox(
                    label="👋 What's your name?",
                    placeholder="Enter your name here...",
                    value="Student"
                )
            
            with gr.Column(scale=1):
                grade_select = gr.Dropdown(
                    choices=list(GRADES.keys()),
                    label="📚 What grade are you in?",
                    interactive=True
                )
            
            with gr.Column(scale=1):
                subject_select = gr.Dropdown(
                    choices=list(SUBJECTS.keys()),
                    label="🎯 Choose your subject",
                    interactive=True
                )
        
        # Topic selection
        with gr.Row():
            with gr.Column(scale=1):
                topic_select = gr.Dropdown(
                    choices=[],
                    label="⭐ Pick a topic to explore",
                    interactive=False
                )
            
            with gr.Column(scale=1):
                subtopic_select = gr.Dropdown(
                    choices=[],
                    label="🔍 Choose a subtopic (optional)",
                    interactive=False
                )
        
        # Error display area
        error_display = gr.Markdown(
            value="",
            visible=False,
            elem_classes=["error-message"]
        )
        
        # Main content area
        with gr.Tab("📚 Learn & Explore"):
            with gr.Row():
                with gr.Column(scale=2):
                    question_input = gr.Textbox(
                        label="❓ Ask me anything about this topic!",
                        placeholder="What would you like to learn?",
                        lines=3
                    )
                    
                    with gr.Row():
                        explain_btn = gr.Button(
                            "✨ Get Explanation",
                            variant="primary",
                            size="lg"
                        )
                        
                        speak_btn = gr.Button(
                            "🎵 Listen",
                            variant="secondary"
                        )
                        
                        stop_btn = gr.Button(
                            "🔇 Stop",
                            variant="secondary"
                        )
                
                with gr.Column(scale=1):
                    audio_output = gr.Audio(
                        label="🎵 Audio Player",
                        visible=True,
                        interactive=False
                    )
                    
                    audio_status = gr.Markdown(
                        value="Ready to help you learn! 🌟"
                    )
            
            # Response area
            explanation_output = gr.Markdown(
                label="📖 Your Learning Content",
                value="Select your grade, subject, and topic to start learning! 🚀"
            )
        
        # Simple Assessment tab
        with gr.Tab("🎯 Quick Quiz"):
            gr.Markdown("### Quick assessment feature coming soon! 🎉")
        
        # Progress tab
        with gr.Tab("📈 My Progress"):
            gr.Markdown("### Your learning progress will appear here! ⭐")
        
        # Event bindings
        # Subject/Grade selection handlers
        subject_select.change(
            fn=update_topics,
            inputs=[subject_select, grade_select],
            outputs=[topic_select, error_display]
        )
        
        grade_select.change(
            fn=update_topics,
            inputs=[subject_select, grade_select],
            outputs=[topic_select, error_display]
        )
        
        topic_select.change(
            fn=update_subtopics,
            inputs=[subject_select, grade_select, topic_select],
            outputs=[subtopic_select, error_display]
        )
        
        # Main interaction handlers
        explain_btn.click(
            fn=handle_explanation,
            inputs=[student_name, subject_select, grade_select, topic_select, subtopic_select, question_input, session_state, audio_state],
            outputs=[explanation_output, session_state, audio_state]
        )
        
        speak_btn.click(
            fn=handle_tts,
            inputs=[explanation_output, audio_state],
            outputs=[audio_output, audio_status, audio_state]
        )
        
        stop_btn.click(
            fn=stop_audio,
            inputs=[audio_state],
            outputs=[audio_status, audio_state]
        )
        
        # Update student name state
        student_name.change(
            fn=lambda name: name,
            inputs=[student_name],
            outputs=[student_name_state]
        )
    
    return interface

# Create and export the interface
gradio_interface = create_interface()