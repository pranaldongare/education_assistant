# services/tutor_service.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from agents.tutor_graph import TutorGraph, QuestionContent, EvaluationResult, LearningPlan
from models.database import (
    get_db, get_or_create_student, save_learning_session, 
    get_student_progress, LearningSession, QuestionResponse
)
from config.settings import (
    MATH_CURRICULUM, ENGLISH_CURRICULUM, TOPIC_LABELS, 
    ASSESSMENT_CONFIG, PRACTICE_CONFIG
)

logger = logging.getLogger(__name__)

class TutorService:
    """High-level service for tutoring operations"""
    
    def __init__(self):
        self.tutor_graph = TutorGraph()
        self.current_sessions = {}  # Store active sessions by session_id
    
    def create_session(self, student_name: str, grade: str, subject: str, 
                      topic: str, subtopic: str, session_type: str) -> str:
        """Create a new learning session"""
        session_id = f"{student_name}_{datetime.now().timestamp()}"
        
        self.current_sessions[session_id] = {
            "student_name": student_name,
            "grade": grade,
            "subject": subject,
            "topic": topic,
            "subtopic": subtopic,
            "session_type": session_type,
            "questions": [],
            "responses": [],
            "start_time": datetime.now(),
            "current_difficulty": 1,
            "current_question_index": 0
        }
        
        logger.info(f"Created session {session_id} for {student_name}")
        return session_id
    
    def get_curriculum_topics(self, subject: str, grade: str) -> Dict[str, List[str]]:
        """Get available topics for a subject and grade"""
        try:
            logger.info(f"get_curriculum_topics called with subject='{subject}', grade='{grade}'")
            
            curriculum = MATH_CURRICULUM if subject == "Mathematics" else ENGLISH_CURRICULUM
            logger.info(f"Using curriculum: {'MATH' if subject == 'Mathematics' else 'ENGLISH'}")
            
            if grade not in curriculum:
                logger.warning(f"Grade '{grade}' not found in curriculum")
                return {}
            
            result = {}
            for topic, info in curriculum[grade].items():
                friendly_topic = TOPIC_LABELS.get(topic, topic)
                result[friendly_topic] = info["topics"]
                logger.debug(f"Added topic: {topic} -> {friendly_topic} with {len(info['topics'])} subtopics")
            
            logger.info(f"Returning {len(result)} topics: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"Error in get_curriculum_topics: {e}", exc_info=True)
            return {}
    
    def get_curriculum_subtopics(self, subject: str, grade: str, topic: str) -> List[str]:
        """Get available subtopics for a subject, grade, and topic"""
        try:
            logger.info(f"get_curriculum_subtopics called with subject='{subject}', grade='{grade}', topic='{topic}'")
            
            curriculum = MATH_CURRICULUM if subject == "Mathematics" else ENGLISH_CURRICULUM
            logger.info(f"Using curriculum: {'MATH' if subject == 'Mathematics' else 'ENGLISH'}")
            
            if grade not in curriculum:
                logger.warning(f"Grade '{grade}' not found in curriculum")
                return []
            
            # Find the actual topic name (reverse lookup from friendly name)
            actual_topic = None
            for curr_topic in curriculum[grade].keys():
                friendly_name = TOPIC_LABELS.get(curr_topic, curr_topic)
                if friendly_name == topic:
                    actual_topic = curr_topic
                    break
            
            if not actual_topic:
                logger.warning(f"Topic '{topic}' not found in grade '{grade}' curriculum")
                return []
            
            subtopics = curriculum[grade][actual_topic]["topics"]
            logger.info(f"Found {len(subtopics)} subtopics for topic '{topic}': {subtopics}")
            return subtopics
            
        except Exception as e:
            logger.error(f"Error in get_curriculum_subtopics: {e}", exc_info=True)
            return []
    
    def explain_topic(self, student_name: str, grade: str, subject: str, 
                     topic: str, subtopic: str) -> str:
        """Generate topic explanation"""
        try:
            logger.info(f"explain_topic called with: student_name='{student_name}', grade='{grade}', subject='{subject}', topic='{topic}', subtopic='{subtopic}'")
            
            # Convert friendly label back to actual topic
            actual_topic = self._get_actual_topic(topic)
            logger.info(f"Converted friendly topic '{topic}' to actual topic '{actual_topic}'")
            
            logger.info(f"Calling tutor_graph.create_explanation with subject='{subject}', grade='{grade}', topic='{actual_topic}', subtopic='{subtopic}'")
            explanation = self.tutor_graph.create_explanation(
                subject=subject,
                grade=grade,
                topic=actual_topic,
                subtopic=subtopic
            )
            logger.info(f"Got explanation from tutor_graph: {explanation[:100]}..." if explanation else "No explanation returned")
            
            # Save to database
            db = next(get_db())
            try:
                student = get_or_create_student(db, student_name, grade)
                save_learning_session(
                    db=db,
                    student_id=student.id,
                    subject=subject,
                    topic=actual_topic,
                    subtopic=subtopic,
                    session_type="explanation",
                    session_data={"explanation": explanation}
                )
            finally:
                db.close()
            
            return explanation
            
        except Exception as e:
            logger.error(f"Explanation error: {e}")
            return "I'm having trouble creating the explanation. Let's try again! 🎈"
    
    def start_assessment(self, student_name: str, grade: str, subject: str, 
                        topic: str, subtopic: str) -> Tuple[str, str]:
        """Start a new assessment session"""
        try:
            session_id = self.create_session(
                student_name, grade, subject, topic, subtopic, "assessment"
            )
            
            # Generate first question
            question = self._generate_next_question(session_id)
            
            if question:
                session = self.current_sessions[session_id]
                session["questions"].append(question)
                
                return session_id, f"**Question 1 of {ASSESSMENT_CONFIG['questions_per_assessment']}:**\n\n{question.question}"
            else:
                return "", "I'm having trouble generating questions. Let's try again! 🎯"
                
        except Exception as e:
            logger.error(f"Assessment start error: {e}")
            return "", "Oops! Something went wrong starting the assessment. Let's try again! 🎈"
    
    def submit_assessment_answer(self, session_id: str, answer: str) -> Tuple[str, bool, bool]:
        """Submit answer for assessment question"""
        try:
            if session_id not in self.current_sessions:
                return "Session not found. Please start a new assessment! 📝", False, False
            
            session = self.current_sessions[session_id]
            current_q_index = len(session["responses"])
            
            if current_q_index >= len(session["questions"]):
                return "No question to answer! 🤔", False, False
            
            current_question = session["questions"][current_q_index]
            
            # Evaluate answer
            evaluation = self.tutor_graph.evaluate_answer(
                subject=session["subject"],
                grade=session["grade"],
                topic=self._get_actual_topic(session["topic"]),
                subtopic=session["subtopic"],
                question=current_question,
                student_answer=answer
            )
            
            if not evaluation:
                return "I'm having trouble evaluating your answer. Let's try again! 🎯", False, True
            
            # Store response
            response_data = {
                "question": current_question.question,
                "student_answer": answer,
                "is_correct": evaluation.is_correct,
                "feedback": evaluation.feedback,
                "score": evaluation.score
            }
            session["responses"].append(response_data)
            
            # Check if assessment is complete
            total_questions = ASSESSMENT_CONFIG["questions_per_assessment"]
            questions_answered = len(session["responses"])
            
            can_continue = questions_answered < total_questions
            
            return evaluation.feedback, True, can_continue
            
        except Exception as e:
            logger.error(f"Assessment answer error: {e}")
            return "Let's try checking that answer again! 🎯", False, True
    
    def get_next_assessment_question(self, session_id: str) -> Tuple[str, bool]:
        """Get next assessment question"""
        try:
            if session_id not in self.current_sessions:
                return "Session not found! 📝", False
            
            session = self.current_sessions[session_id]
            total_questions = ASSESSMENT_CONFIG["questions_per_assessment"]
            current_count = len(session["questions"])
            
            if current_count >= total_questions:
                # Assessment complete - generate learning plan
                learning_plan = self._generate_assessment_report(session_id)
                return learning_plan, False
            
            # Generate next question
            question = self._generate_next_question(session_id)
            
            if question:
                session["questions"].append(question)
                question_num = len(session["questions"])
                
                return f"**Question {question_num} of {total_questions}:**\n\n{question.question}", True
            else:
                return "I'm having trouble generating the next question. Let's try again! 🎯", False
                
        except Exception as e:
            logger.error(f"Next question error: {e}")
            return "Oops! Something went wrong. Let's try again! 🎲", False
    
    def start_practice(self, student_name: str, grade: str, subject: str, 
                      topic: str, subtopic: str) -> Tuple[str, str]:
        """Start a practice session"""
        try:
            session_id = self.create_session(
                student_name, grade, subject, topic, subtopic, "practice"
            )
            
            question = self._generate_next_question(session_id)
            
            if question:
                session = self.current_sessions[session_id]
                session["questions"].append(question)
                return session_id, question.question
            else:
                return "", "I'm having trouble generating practice questions. Let's try again! 🎲"
                
        except Exception as e:
            logger.error(f"Practice start error: {e}")
            return "", "Oops! Let's try starting practice again! 🎲"
    
    def submit_practice_answer(self, session_id: str, answer: str) -> Tuple[str, bool, str]:
        """Submit practice answer and get feedback"""
        try:
            if session_id not in self.current_sessions:
                return "Session not found! 📝", False, ""
            
            session = self.current_sessions[session_id]
            current_q_index = len(session["responses"])
            
            if current_q_index >= len(session["questions"]):
                return "No question to answer! 🤔", False, ""
            
            current_question = session["questions"][current_q_index]
            
            # Evaluate answer
            evaluation = self.tutor_graph.evaluate_answer(
                subject=session["subject"],
                grade=session["grade"],
                topic=self._get_actual_topic(session["topic"]),
                subtopic=session["subtopic"],
                question=current_question,
                student_answer=answer
            )
            
            if not evaluation:
                return "Let's try checking that answer again! 🎯", False, ""
            
            # Store response
            response_data = {
                "question": current_question.question,
                "student_answer": answer,
                "is_correct": evaluation.is_correct,
                "feedback": evaluation.feedback,
                "score": evaluation.score
            }
            session["responses"].append(response_data)
            
            # Adjust difficulty based on performance
            if evaluation.is_correct:
                session["current_difficulty"] = min(5, session["current_difficulty"] + 1)
            else:
                session["current_difficulty"] = max(1, session["current_difficulty"] - 1)
            
            hint = current_question.hint if hasattr(current_question, 'hint') else ""
            
            return evaluation.feedback, evaluation.is_correct, hint
            
        except Exception as e:
            logger.error(f"Practice answer error: {e}")
            return "Let's try checking that answer again! 🎯", False, ""
    
    def get_next_practice_question(self, session_id: str) -> str:
        """Get next practice question"""
        try:
            if session_id not in self.current_sessions:
                return "Session not found! 📝"
            
            question = self._generate_next_question(session_id)
            
            if question:
                session = self.current_sessions[session_id]
                session["questions"].append(question)
                return question.question
            else:
                return "Let's try a different problem! 🎲"
                
        except Exception as e:
            logger.error(f"Next practice question error: {e}")
            return "Oops! Something went wrong. Let's try again! 🎲"
    
    def get_practice_summary(self, session_id: str) -> str:
        """Generate practice session summary"""
        try:
            if session_id not in self.current_sessions:
                return "Session not found! 📝"
            
            session = self.current_sessions[session_id]
            responses = session["responses"]
            
            if not responses:
                return "Let's do some practice first! 📝"
            
            # Calculate performance metrics
            total_questions = len(responses)
            correct_answers = sum(1 for r in responses if r["is_correct"])
            accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            # Generate summary using AI
            learning_plan = self.tutor_graph.generate_learning_plan(
                subject=session["subject"],
                grade=session["grade"],
                topic=self._get_actual_topic(session["topic"]),
                subtopic=session["subtopic"],
                responses=responses
            )
            
            summary = f"""
            📊 **Practice Session Summary**
            
            **Performance:**
            - Questions Attempted: {total_questions}
            - Correct Answers: {correct_answers}
            - Accuracy: {accuracy:.1f}%
            
            """
            
            if learning_plan:
                summary += f"""
            **What You Did Well:**
            {chr(10).join(f"• {strength}" for strength in learning_plan.strengths)}
            
            **Areas to Practice More:**
            {chr(10).join(f"• {area}" for area in learning_plan.areas_for_improvement)}
            
            **Recommended Activities:**
            {chr(10).join(f"• {activity}" for activity in learning_plan.recommended_activities)}
            
            {learning_plan.encouragement}
            """
            
            # Save session to database
            self._save_session_to_db(session_id)
            
            return summary
            
        except Exception as e:
            logger.error(f"Practice summary error: {e}")
            return "Great job practicing! You're doing amazing! 🌟"
    
    def _generate_next_question(self, session_id: str) -> Optional[QuestionContent]:
        """Generate next question for a session"""
        try:
            session = self.current_sessions[session_id]
            
            question = self.tutor_graph.generate_question(
                subject=session["subject"],
                grade=session["grade"],
                topic=self._get_actual_topic(session["topic"]),
                subtopic=session["subtopic"],
                difficulty=session["current_difficulty"]
            )
            
            return question
            
        except Exception as e:
            logger.error(f"Question generation error: {e}")
            return None
    
    def _generate_assessment_report(self, session_id: str) -> str:
        """Generate comprehensive assessment report"""
        try:
            session = self.current_sessions[session_id]
            responses = session["responses"]
            
            # Calculate performance
            total_questions = len(responses)
            correct_answers = sum(1 for r in responses if r["is_correct"])
            accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            # Generate learning plan
            learning_plan = self.tutor_graph.generate_learning_plan(
                subject=session["subject"],
                grade=session["grade"],
                topic=self._get_actual_topic(session["topic"]),
                subtopic=session["subtopic"],
                responses=responses
            )
            
            report = f"""
            # 🎉 Assessment Complete!
            
            ## 📊 Your Results
            - **Total Questions:** {total_questions}
            - **Correct Answers:** {correct_answers}
            - **Success Rate:** {accuracy:.1f}%
            
            """
            
            if learning_plan:
                report += f"""
            ## 🌟 What You're Great At
            {chr(10).join(f"• {strength}" for strength in learning_plan.strengths)}
            
            ## 🎯 Let's Work On
            {chr(10).join(f"• {area}" for area in learning_plan.areas_for_improvement)}
            
            ## 📚 Your Learning Plan
            {chr(10).join(f"• {activity}" for activity in learning_plan.recommended_activities)}
            
            ## 🚀 Next Steps
            {chr(10).join(f"• {step}" for step in learning_plan.next_steps)}
            
            ---
            
            {learning_plan.encouragement}
            """
            
            # Save assessment to database
            self._save_session_to_db(session_id)
            
            return report
            
        except Exception as e:
            logger.error(f"Assessment report error: {e}")
            return "Great job completing the assessment! You're learning so much! 🌟"
    
    def _save_session_to_db(self, session_id: str):
        """Save session data to database"""
        try:
            if session_id not in self.current_sessions:
                return
            
            session = self.current_sessions[session_id]
            db = next(get_db())
            
            try:
                # Get or create student
                student = get_or_create_student(
                    db, session["student_name"], session["grade"]
                )
                
                # Calculate metrics
                responses = session["responses"]
                total_questions = len(responses)
                correct_answers = sum(1 for r in responses if r["is_correct"])
                duration = (datetime.now() - session["start_time"]).total_seconds() / 60
                
                # Save learning session
                db_session = save_learning_session(
                    db=db,
                    student_id=student.id,
                    subject=session["subject"],
                    topic=self._get_actual_topic(session["topic"]),
                    subtopic=session["subtopic"],
                    session_type=session["session_type"],
                    session_data=session,
                    questions_attempted=total_questions,
                    questions_correct=correct_answers,
                    duration_minutes=int(duration)
                )
                
                # Save individual question responses
                for response in responses:
                    question_response = QuestionResponse(
                        session_id=db_session.id,
                        question_text=response["question"],
                        student_answer=response["student_answer"],
                        is_correct=response["is_correct"],
                        feedback=response["feedback"]
                    )
                    db.add(question_response)
                
                db.commit()
                logger.info(f"Saved session {session_id} to database")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Database save error: {e}")
    
    def _get_actual_topic(self, friendly_topic: str) -> str:
        """Convert friendly topic label back to actual topic name"""
        for actual, friendly in TOPIC_LABELS.items():
            if friendly == friendly_topic:
                return actual
        return friendly_topic
    
    def get_student_analytics(self, student_name: str, grade: str, subject: str) -> Dict:
        """Get comprehensive student analytics"""
        try:
            db = next(get_db())
            try:
                student = get_or_create_student(db, student_name, grade)
                progress = get_student_progress(db, student.id, subject)
                return progress
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Analytics error: {e}")
            return {}
    
    def cleanup_session(self, session_id: str):
        """Clean up completed session"""
        if session_id in self.current_sessions:
            del self.current_sessions[session_id]
            logger.info(f"Cleaned up session {session_id}")

# Global service instance
tutor_service = TutorService()