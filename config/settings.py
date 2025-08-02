# config/settings.py
import os
from pathlib import Path
from typing import Dict, List
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./tutor.db", env="DATABASE_URL")
    
    # Application Configuration
    app_name: str = "AI Tutor Agent"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Gradio Configuration
    server_host: str = Field(default="127.0.0.1", env="SERVER_HOST")
    server_port: int = Field(default=7860, env="SERVER_PORT")
    share: bool = Field(default=False, env="SHARE")
    
    # TTS Configuration
    tts_enabled: bool = Field(default=True, env="TTS_ENABLED")
    tts_language: str = Field(default="en", env="TTS_LANGUAGE")
    tts_speed: float = Field(default=1.0, env="TTS_SPEED")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

# Subject definitions
SUBJECTS = {
    "Mathematics": "Let's Learn Math! 🔢",
    "English": "Let's Learn English! 📚"
}

# Grade levels
GRADES = {
    "1": "Grade 1 - Foundation 🌱",
    "2": "Grade 2 - Building Up 🏗️", 
    "3": "Grade 3 - Growing Strong 🌳"
}

# Mathematics Curriculum (CBSE Aligned)
MATH_CURRICULUM = {
    "1": {
        "Numbers": {
            "topics": [
                "Numbers up to 20",
                "Addition and Subtraction up to 20", 
                "Numbers up to 99",
                "Simple patterns"
            ],
            "description": "Basic number recognition and simple operations"
        },
        "Shapes and Space": {
            "topics": [
                "Basic 2D shapes",
                "Position and direction"
            ],
            "description": "Introduction to shapes and spatial concepts"
        },
        "Measurement": {
            "topics": [
                "Length - Non standard units",
                "Weight - Non standard units"
            ],
            "description": "Basic measurement concepts"
        }
    },
    "2": {
        "Numbers": {
            "topics": [
                "Numbers up to 999",
                "Addition and Subtraction up to 99",
                "Mental Mathematics", 
                "Multiplication - Tables 2,3,4,5"
            ],
            "description": "Extended number operations and mental math"
        },
        "Patterns": {
            "topics": [
                "Number patterns",
                "Shape patterns"
            ],
            "description": "Recognition and creation of patterns"
        },
        "Measurement": {
            "topics": [
                "Length - cm and m",
                "Weight - kg",
                "Capacity - L"
            ],
            "description": "Standard units of measurement"
        },
        "Data Handling": {
            "topics": [
                "Simple data collection",
                "Pictographs"
            ],
            "description": "Basic data representation"
        }
    },
    "3": {
        "Numbers": {
            "topics": [
                "Numbers up to 9999",
                "Addition and Subtraction up to 999",
                "Multiplication",
                "Division",
                "Fractions"
            ],
            "description": "Advanced number operations and fractions"
        },
        "Patterns": {
            "topics": [
                "Number patterns",
                "Shape patterns"
            ],
            "description": "Complex pattern recognition"
        },
        "Measurement": {
            "topics": [
                "Length - km",
                "Weight - g", 
                "Time",
                "Money"
            ],
            "description": "Advanced measurement and practical applications"
        },
        "Data Handling": {
            "topics": [
                "Pictographs",
                "Tables and bar graphs"
            ],
            "description": "Data analysis and representation"
        }
    }
}

# English Curriculum (CBSE Aligned)
ENGLISH_CURRICULUM = {
    "1": {
        "Grammar": {
            "topics": [
                "Nouns - Naming Words",
                "Articles - a, an, the",
                "Pronouns - I, you, he, she, it",
                "Action Words - Simple Verbs",
                "Describing Words - Basic Adjectives"
            ],
            "description": "Foundation grammar concepts"
        },
        "Writing Skills": {
            "topics": [
                "Capital Letters and Full Stops",
                "Simple Sentences",
                "Picture Description",
                "Story Completion",
                "Thank You Note"
            ],
            "description": "Basic writing and sentence construction"
        },
        "Reading Comprehension": {
            "topics": [
                "Short Stories",
                "Simple Poems",
                "Picture Stories", 
                "Simple Instructions",
                "Basic Signs and Labels"
            ],
            "description": "Reading understanding and comprehension"
        }
    },
    "2": {
        "Grammar": {
            "topics": [
                "Nouns - Common and Special Names",
                "Verbs - Present and Past",
                "Adjectives - Comparing Things",
                "Prepositions - Position Words",
                "Conjunctions - Joining Words"
            ],
            "description": "Extended grammar concepts"
        },
        "Writing Skills": {
            "topics": [
                "Paragraph Writing",
                "Story Writing with Pictures",
                "Informal Letters",
                "Diary Entry",
                "Message Writing"
            ],
            "description": "Structured writing skills"
        },
        "Reading Comprehension": {
            "topics": [
                "Longer Stories",
                "Poems with Rhymes",
                "Instructions and Directions",
                "Simple Advertisements", 
                "Short Dialogues"
            ],
            "description": "Advanced reading comprehension"
        }
    },
    "3": {
        "Grammar": {
            "topics": [
                "Nouns - Gender and Number",
                "Verbs - Present, Past, Future",
                "Adjectives - Degrees of Comparison",
                "Adverbs - How, When, Where",
                "Punctuation - Complex Usage"
            ],
            "description": "Advanced grammar and punctuation"
        },
        "Writing Skills": {
            "topics": [
                "Creative Story Writing",
                "Formal Letters",
                "Essay Writing",
                "Invitation Writing",
                "Descriptive Writing"
            ],
            "description": "Creative and formal writing"
        },
        "Reading Comprehension": {
            "topics": [
                "Complex Stories",
                "Poems with Themes",
                "Newspaper Articles",
                "Informational Texts",
                "Play Scripts"
            ],
            "description": "Complex text analysis"
        }
    }
}

# Friendly topic labels
TOPIC_LABELS = {
    # Math
    "Numbers": "Number Adventures",
    "Shapes and Space": "Shape Explorer",
    "Measurement": "Measuring Magic",
    "Patterns": "Pattern Detective", 
    "Data Handling": "Data Explorer",
    
    # English
    "Grammar": "Grammar Adventures",
    "Writing Skills": "Writing Workshop",
    "Reading Comprehension": "Reading Quests"
}

# Assessment configuration
ASSESSMENT_CONFIG = {
    "questions_per_assessment": 5,
    "time_limit_minutes": 15,
    "passing_score": 0.7,
    "difficulty_levels": 5,
    "max_retries": 3
}

# Practice configuration  
PRACTICE_CONFIG = {
    "session_duration_minutes": 20,
    "questions_per_session": 10,
    "difficulty_progression": {
        "initial_level": 1,
        "increment_threshold": 0.8,
        "decrement_threshold": 0.4
    }
}

# Gamification system
REWARD_SYSTEM = {
    "points": {
        "correct_answer": 10,
        "practice_completion": 50,
        "assessment_completion": 100,
        "difficulty_bonus": 20,
        "streak_bonus": 15
    },
    "badges": {
        "math_explorer": "Complete all math topics in a grade",
        "grammar_master": "Perfect score in grammar assessment", 
        "creative_writer": "Complete 10 writing assignments",
        "eager_reader": "Complete 15 reading comprehensions",
        "persistent_learner": "7-day learning streak"
    }
}

# Error messages
ERROR_MESSAGES = {
    "grade_selection": "Please select your grade first! 📚",
    "subject_selection": "Please choose a subject to begin! 🎯",
    "topic_selection": "Please pick a topic to continue! ⭐",
    "invalid_input": "Oops! That doesn't look right. Let's try again! 🎈",
    "server_error": "Something went wrong! Let's take a short break and try again! 🌟",
    "session_expired": "Your session has expired. Please start again! 🔑"
}

# TTS Configuration
TTS_CONFIG = {
    "excluded_chars": ["🌱", "🏗️", "🌳", "🌟", "📚", "🔢", "🎯", "⭐", "📐", "📏", "🎨", "📊", "📝", "✍️", "🎉", "✨", "➡️", "🔍", "🎲"],
    "cleanup_patterns": [
        (r'\*\*(.*?)\*\*', r'\1'),  # Bold
        (r'\*(.*?)\*', r'\1'),      # Italic  
        (r'#+ ', ''),               # Headers
        (r'`.*?`', ''),             # Code
    ]
}