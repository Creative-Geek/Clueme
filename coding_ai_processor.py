"""
AI processor module for coding questions.
Handles direct coding question processing with markdown output.
"""
import datetime
from openai import OpenAI
from PySide6.QtCore import QObject, Signal, Slot


class SignalEmitter(QObject):
    """Signal emitter for AI processing events"""
    quit_signal = Signal()
    response_chunk_received = Signal(str)
    response_finished = Signal()
    error_occurred = Signal(str)
    processing_started = Signal()
    text_extracted = Signal(str)  # Emitted when OCR text is extracted


class CodingAIProcessor:
    """Handles AI processing for coding questions"""
    
    def __init__(self, api_key: str, base_url: str | None, model: str = "gpt-4"):
        """
        Initialize the AI processor with API configuration.
        
        Args:
            api_key: API key for the LLM service
            base_url: Base URL for the API endpoint (optional)
            model: Model name to use
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
        # Create OpenAI client
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        self.emitter = SignalEmitter()
    
    def process_coding_question(self, text: str):
        """
        Process a coding question/assignment and generate a solution.
        
        Args:
            text: The extracted text from OCR containing the coding question
        """
        if not text or not text.strip():
            print("No text provided. Skipping processing.")
            self.emitter.response_chunk_received.emit("No text was extracted from the screen.")
            self.emitter.response_finished.emit()
            return
        
        print(f"\n--- Processing coding question using {self.model} ---")
        print(f"Input text (first 200 chars): {text[:200]}...")
        
        try:
            # Create the prompt for coding assistance
            system_prompt = """You are an expert programming assistant. You help solve coding questions, assignments, and assessments.

Your response guidelines:
- Be brief and concise - focus on the solution
- Format your response in Markdown
- Use proper code blocks with language specification for syntax highlighting (e.g., ```python, ```java, ```cpp)
- Include only essential explanations
- If the question has multiple parts, address each briefly
- Prioritize working code over lengthy explanations"""

            user_prompt = f"""Solve the following coding question/assignment. Provide a brief, working solution in Markdown format with properly formatted code blocks.

Question/Assignment:
{text}

Solution:"""

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True,
                max_tokens=1000
            )
            
            full_response = ""
            for chunk in stream:
                content_chunk = chunk.choices[0].delta.content
                if content_chunk is not None:
                    full_response += content_chunk
                    self.emitter.response_chunk_received.emit(content_chunk)
            
            self.emitter.response_finished.emit()
            
            # Log the interaction
            try:
                with open('coding_logs.txt', 'a', encoding='utf-8') as f:
                    f.write(f"\n\n=== {datetime.datetime.now().isoformat()} ===\n")
                    f.write(f"Input Text:\n{text}\n\n")
                    f.write(f"Model: {self.model}\n")
                    f.write(f"Response:\n{full_response}\n")
            except Exception as log_error:
                print(f"Warning: Could not write to log file: {log_error}")
            
            print(f"Response logged. Length: {len(full_response)}")
            
        except Exception as e:
            error_message = f"Error during processing: {str(e)}"
            print(error_message)
            self.emitter.error_occurred.emit(error_message)
            self.emitter.response_finished.emit()
