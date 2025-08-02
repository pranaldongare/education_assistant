# agents/tutor_graph.py
from typing import Dict, List, Optional, Tuple, Annotated, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import json
import logging
from config.settings import settings, MATH_CURRICULUM, ENGLISH_CURRICULUM

logger = logging.getLogger(__name__)

# Pydantic Models for structured outputs
class QuestionContent(BaseModel):
    """Structured question content"""
    question: str = Field(description="The main question text")
    hint: str = Field(description="A helpful hint for the student")
    solution: str = Field(description="Complete solution with explanation")
    difficulty_level: int = Field(description="Difficulty level 1-5")
    topic_alignment: str = Field(description="How well this aligns with the topic")

class ValidationResult(BaseModel):
    """Question validation result"""
    is_valid: bool = Field(description="Whether the question is valid")
    feedback: str = Field(description="Validation feedback")
    improved_question: Optional[str] = Field(description="Improved version if needed")
    confidence_score: float = Field(description="Confidence in validation (0-1)")

class EvaluationResult(BaseModel):
    """Answer evaluation result"""
    is_correct: bool = Field(description="Whether the answer is correct")
    feedback: str = Field(description="Encouraging feedback for the student")
    score: float = Field(description="Score between 0-1")
    suggestions: List[str] = Field(description="Specific suggestions for improvement")

class LearningPlan(BaseModel):
    """Personalized learning plan"""
    strengths: List[str] = Field(description="Identified strengths")
    areas_for_improvement: List[str] = Field(description="Areas needing work")
    recommended_activities: List[str] = Field(description="Specific practice activities")
    next_steps: List[str] = Field(description="Next learning steps")
    encouragement: str = Field(description="Motivational message")

# State definition for the tutor graph
class TutorState(BaseModel):
    """State management for the tutor agent system"""
    messages: Annotated[List[BaseMessage], add_messages]
    student_info: Dict = Field(default_factory=dict)
    current_subject: str = ""
    current_grade: str = ""
    current_topic: str = ""
    current_subtopic: str = ""
    session_type: str = ""  # 'practice', 'assessment', 'explanation'
    
    # Session data
    questions_generated: List[QuestionContent] = Field(default_factory=list)
    student_responses: List[Dict] = Field(default_factory=list)
    current_question_index: int = 0
    
    # Performance tracking
    correct_answers: int = 0
    total_questions: int = 0
    difficulty_level: int = 1
    
    # Outputs
    current_question: Optional[QuestionContent] = None
    evaluation_result: Optional[EvaluationResult] = None
    learning_plan: Optional[LearningPlan] = None
    explanation_content: str = ""
    
    # Control flags
    needs_validation: bool = False
    session_complete: bool = False
    error_occurred: bool = False
    retry_count: int = 0

class TutorGraph:
    """LangGraph-based tutor system"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.temperature,
            api_key=settings.openai_api_key
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Define the workflow graph
        workflow = StateGraph(TutorState)
        
        # Add nodes
        workflow.add_node("route_request", self._route_request)
        workflow.add_node("generate_question", self._generate_question)
        workflow.add_node("validate_question", self._validate_question)
        workflow.add_node("evaluate_answer", self._evaluate_answer)
        workflow.add_node("create_explanation", self._create_explanation)
        workflow.add_node("generate_learning_plan", self._generate_learning_plan)
        workflow.add_node("handle_error", self._handle_error)
        
        # Define entry point
        workflow.set_entry_point("route_request")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "route_request",
            self._routing_condition,
            {
                "generate_question": "generate_question",
                "evaluate_answer": "evaluate_answer", 
                "create_explanation": "create_explanation",
                "generate_plan": "generate_learning_plan",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_question",
            self._question_condition,
            {
                "validate": "validate_question",
                "complete": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "validate_question",
            self._validation_condition,
            {
                "approved": END,
                "retry": "generate_question",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("evaluate_answer", END)
        workflow.add_edge("create_explanation", END)
        workflow.add_edge("generate_learning_plan", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    def _route_request(self, state: TutorState) -> TutorState:
        """Route the request to appropriate handler"""
        try:
            if not state.messages:
                state.error_occurred = True
                return state
                
            last_message = state.messages[-1].content
            
            # Determine action based on session_type or message content
            if state.session_type == "explanation":
                # Route to explanation generation
                pass
            elif state.session_type == "assessment" or state.session_type == "practice":
                if "evaluate:" in last_message:
                    # Route to answer evaluation
                    pass
                else:
                    # Route to question generation
                    pass
            elif "learning_plan" in last_message:
                # Route to learning plan generation
                pass
                
            return state
            
        except Exception as e:
            logger.error(f"Routing error: {e}")
            state.error_occurred = True
            return state
    
    def _generate_question(self, state: TutorState) -> TutorState:
        """Generate educational questions using LangChain"""
        try:
            # Get curriculum context
            curriculum = self._get_curriculum_context(
                state.current_subject, 
                state.current_grade, 
                state.current_topic
            )
            
            # Create prompt for question generation
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert educational content creator for grade {grade} students.
                Create engaging {subject} questions for the topic: {topic} - {subtopic}.
                
                Curriculum Context: {curriculum}
                
                Requirements:
                1. Age-appropriate for grade {grade}
                2. Focused exactly on {subtopic}
                3. Clear and unambiguous
                4. Include helpful hint
                5. Provide complete solution
                6. Real-world context when possible
                7. Difficulty level: {difficulty}/5
                
                Generate ONE high-quality question that helps students learn {subtopic}."""),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            # Set up output parser
            parser = PydanticOutputParser(pydantic_object=QuestionContent)
            
            # Create the chain
            chain = prompt | self.llm | parser
            
            # Generate question
            result = chain.invoke({
                "grade": state.current_grade,
                "subject": state.current_subject,
                "topic": state.current_topic,
                "subtopic": state.current_subtopic,
                "curriculum": curriculum,
                "difficulty": state.difficulty_level,
                "messages": state.messages
            })
            
            state.current_question = result
            state.questions_generated.append(result)
            state.needs_validation = True
            
            return state
            
        except Exception as e:
            logger.error(f"Question generation error: {e}")
            state.error_occurred = True
            state.retry_count += 1
            return state
    
    def _validate_question(self, state: TutorState) -> TutorState:
        """Validate generated questions"""
        try:
            if not state.current_question:
                state.error_occurred = True
                return state
            
            # Create validation prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert educational validator. Evaluate this question for grade {grade} {subject}.
                
                Topic: {topic} - {subtopic}
                Question: {question}
                
                Validation Criteria:
                1. Appropriate for grade {grade} level
                2. Focuses exactly on {subtopic}
                3. Clear and unambiguous
                4. Has a definitive solution path
                5. Age-appropriate vocabulary
                6. Engaging and educational
                
                Provide detailed validation feedback."""),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            parser = PydanticOutputParser(pydantic_object=ValidationResult)
            chain = prompt | self.llm | parser
            
            validation = chain.invoke({
                "grade": state.current_grade,
                "subject": state.current_subject,
                "topic": state.current_topic,
                "subtopic": state.current_subtopic,
                "question": state.current_question.question,
                "messages": state.messages
            })
            
            # Update question if improved version provided
            if validation.improved_question:
                state.current_question.question = validation.improved_question
            
            # Set validation flags
            state.needs_validation = False
            if not validation.is_valid and state.retry_count < 3:
                state.retry_count += 1
                state.current_question = None
            else:
                state.retry_count = 0
            
            return state
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            state.error_occurred = True
            return state
    
    def _evaluate_answer(self, state: TutorState) -> TutorState:
        """Evaluate student answers"""
        try:
            if not state.messages:
                state.error_occurred = True
                return state
            
            # Extract student answer from last message
            student_answer = state.messages[-1].content.replace("evaluate:", "").strip()
            
            # Get current question
            current_question = state.current_question or (
                state.questions_generated[state.current_question_index] 
                if state.questions_generated else None
            )
            
            if not current_question:
                state.error_occurred = True
                return state
            
            # Create evaluation prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a supportive {subject} tutor for grade {grade} students.
                Evaluate this student's answer with encouraging feedback.
                
                Question: {question}
                Correct Solution: {solution}
                Student Answer: {student_answer}
                Topic: {topic} - {subtopic}
                
                Guidelines:
                1. Be encouraging and supportive
                2. Start with "✨" if completely correct
                3. Start with "👍" if partially correct  
                4. Start with "💡" if incorrect but show understanding
                5. Provide specific, constructive feedback
                6. Use age-appropriate language
                7. Include helpful suggestions
                8. End with an encouraging emoji
                
                Focus on learning, not just correctness."""),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            parser = PydanticOutputParser(pydantic_object=EvaluationResult)
            chain = prompt | self.llm | parser
            
            evaluation = chain.invoke({
                "grade": state.current_grade,
                "subject": state.current_subject,
                "topic": state.current_topic,
                "subtopic": state.current_subtopic,
                "question": current_question.question,
                "solution": current_question.solution,
                "student_answer": student_answer,
                "messages": state.messages
            })
            
            # Update state
            state.evaluation_result = evaluation
            
            # Track performance
            if evaluation.is_correct:
                state.correct_answers += 1
            state.total_questions += 1
            
            # Store response
            state.student_responses.append({
                "question": current_question.question,
                "student_answer": student_answer,
                "is_correct": evaluation.is_correct,
                "feedback": evaluation.feedback,
                "score": evaluation.score
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            state.error_occurred = True
            return state
    
    def _create_explanation(self, state: TutorState) -> TutorState:
        """Create topic explanations"""
        try:
            # Get curriculum context
            curriculum = self._get_curriculum_context(
                state.current_subject,
                state.current_grade, 
                state.current_topic
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a friendly and engaging {subject} teacher for grade {grade} students.
                Create a fun, easy-to-understand explanation for: {topic} - {subtopic}
                
                Curriculum Context: {curriculum}
                
                Make your explanation:
                1. Fun and engaging with emojis
                2. Age-appropriate for grade {grade}
                3. Use simple examples and analogies
                4. Include a short story or scenario
                5. Break complex ideas into small steps
                6. Interactive where possible
                7. Focus ONLY on {subtopic}
                8. End with encouragement to practice
                
                Create an explanation that makes learning enjoyable!"""),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            
            explanation = chain.invoke({
                "grade": state.current_grade,
                "subject": state.current_subject,
                "topic": state.current_topic,
                "subtopic": state.current_subtopic,
                "curriculum": curriculum,
                "messages": state.messages
            })
            
            state.explanation_content = explanation
            return state
            
        except Exception as e:
            logger.error(f"Explanation error: {e}")
            state.error_occurred = True
            return state
    
    def _generate_learning_plan(self, state: TutorState) -> TutorState:
        """Generate personalized learning plans"""
        try:
            # Analyze student performance
            performance_data = {
                "total_questions": state.total_questions,
                "correct_answers": state.correct_answers,
                "accuracy": (state.correct_answers / state.total_questions * 100) if state.total_questions > 0 else 0,
                "responses": state.student_responses
            }
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert educational advisor creating a personalized learning plan.
                
                Student Performance:
                - Subject: {subject}
                - Grade: {grade}
                - Topic: {topic} - {subtopic}
                - Questions Attempted: {total_questions}
                - Correct Answers: {correct_answers}
                - Accuracy: {accuracy}%
                
                Response Details: {responses}
                
                Create a comprehensive learning plan that includes:
                1. Specific strengths demonstrated
                2. Areas needing improvement
                3. Recommended daily activities
                4. Practice suggestions
                5. Next learning milestones
                6. Motivational encouragement
                
                Make it actionable and encouraging for a grade {grade} student."""),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            parser = PydanticOutputParser(pydantic_object=LearningPlan)
            chain = prompt | self.llm | parser
            
            plan = chain.invoke({
                "grade": state.current_grade,
                "subject": state.current_subject,
                "topic": state.current_topic,
                "subtopic": state.current_subtopic,
                "total_questions": performance_data["total_questions"],
                "correct_answers": performance_data["correct_answers"],
                "accuracy": performance_data["accuracy"],
                "responses": json.dumps(performance_data["responses"]),
                "messages": state.messages
            })
            
            state.learning_plan = plan
            return state
            
        except Exception as e:
            logger.error(f"Learning plan error: {e}")
            state.error_occurred = True
            return state
    
    def _handle_error(self, state: TutorState) -> TutorState:
        """Handle errors gracefully"""
        error_message = "I'm having trouble right now. Let's try again! 🌟"
        
        if state.session_type == "practice":
            error_message = "Oops! Let's try a different practice problem! 🎲"
        elif state.session_type == "assessment":
            error_message = "Let's continue with your assessment! 📝"
        elif state.session_type == "explanation":
            error_message = "Let me try explaining that again! 🎈"
        
        state.messages.append(AIMessage(content=error_message))
        state.error_occurred = False
        return state
    
    # Condition functions for routing
    def _routing_condition(self, state: TutorState) -> str:
        """Determine which node to route to"""
        if state.error_occurred:
            return "error"
        
        if not state.messages:
            return "error"
        
        last_message = state.messages[-1].content.lower()
        
        if "evaluate:" in last_message:
            return "evaluate_answer"
        elif state.session_type == "explanation":
            return "create_explanation" 
        elif "learning_plan" in last_message or state.session_type == "learning_plan":
            return "generate_plan"
        elif state.session_type in ["practice", "assessment"]:
            return "generate_question"
        else:
            return "error"
    
    def _question_condition(self, state: TutorState) -> str:
        """Determine next step after question generation"""
        if state.error_occurred:
            return "error"
        elif state.needs_validation:
            return "validate"
        else:
            return "complete"
    
    def _validation_condition(self, state: TutorState) -> str:
        """Determine next step after validation"""
        if state.error_occurred:
            return "error"
        elif state.retry_count > 0 and state.retry_count < 3:
            return "retry"
        else:
            return "approved"
    
    def _get_curriculum_context(self, subject: str, grade: str, topic: str) -> str:
        """Get relevant curriculum context"""
        try:
            if subject.lower() == "mathematics":
                curriculum = MATH_CURRICULUM.get(grade, {})
            else:
                curriculum = ENGLISH_CURRICULUM.get(grade, {})
            
            topic_info = curriculum.get(topic, {})
            
            return f"""
            Grade {grade} {subject} - {topic}
            Topics: {', '.join(topic_info.get('topics', []))}
            Description: {topic_info.get('description', '')}
            """
        except Exception:
            return f"Grade {grade} {subject} curriculum"
    
    # Public interface methods
    def generate_question(self, subject: str, grade: str, topic: str, subtopic: str, difficulty: int = 1) -> Optional[QuestionContent]:
        """Generate a question for practice or assessment"""
        try:
            initial_state = TutorState(
                messages=[HumanMessage(content=f"Generate question for {subtopic}")],
                current_subject=subject,
                current_grade=grade,
                current_topic=topic,
                current_subtopic=subtopic,
                session_type="practice",
                difficulty_level=difficulty
            )
            
            result = self.graph.invoke(initial_state)
            return result.current_question
            
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            return None
    
    def evaluate_answer(self, subject: str, grade: str, topic: str, subtopic: str, 
                       question: QuestionContent, student_answer: str) -> Optional[EvaluationResult]:
        """Evaluate a student's answer"""
        try:
            initial_state = TutorState(
                messages=[HumanMessage(content=f"evaluate:{student_answer}")],
                current_subject=subject,
                current_grade=grade,
                current_topic=topic,
                current_subtopic=subtopic,
                current_question=question,
                session_type="evaluation"
            )
            
            result = self.graph.invoke(initial_state)
            return result.evaluation_result
            
        except Exception as e:
            logger.error(f"Answer evaluation failed: {e}")
            return None
    
    def create_explanation(self, subject: str, grade: str, topic: str, subtopic: str) -> str:
        """Create topic explanation"""
        try:
            initial_state = TutorState(
                messages=[HumanMessage(content=f"Explain {subtopic}")],
                current_subject=subject,
                current_grade=grade,
                current_topic=topic,
                current_subtopic=subtopic,
                session_type="explanation"
            )
            
            logger.debug(f"Initial state: {initial_state}")
            result = self.graph.invoke(initial_state)
            logger.debug(f"Graph result type: {type(result)}")
            logger.debug(f"Graph result: {result}")
            
            if hasattr(result, 'explanation_content'):
                return result.explanation_content
            else:
                logger.error(f"Result does not have explanation_content attribute. Available attributes: {dir(result)}")
                return "I'm having trouble creating the explanation. Let's try again! 🎈"
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return "I'm having trouble creating the explanation. Let's try again! 🎈"
    
    def generate_learning_plan(self, subject: str, grade: str, topic: str, subtopic: str, 
                             responses: List[Dict]) -> Optional[LearningPlan]:
        """Generate personalized learning plan"""
        try:
            initial_state = TutorState(
                messages=[HumanMessage(content="Generate learning_plan")],
                current_subject=subject,
                current_grade=grade,
                current_topic=topic,
                current_subtopic=subtopic,
                student_responses=responses,
                total_questions=len(responses),
                correct_answers=sum(1 for r in responses if r.get('is_correct', False)),
                session_type="learning_plan"
            )
            
            result = self.graph.invoke(initial_state)
            return result.learning_plan
            
        except Exception as e:
            logger.error(f"Learning plan generation failed: {e}")
            return None