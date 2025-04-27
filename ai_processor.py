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
    extraction_complete = Signal(dict)

class AIProcessor:
    """Handles all AI-related processing"""
    
    def __init__(self, api_key, base_url, smarter_model_api_base=None, smarter_model="gpt-4"):
        """Initialize the AI processor with API configuration"""
        self.api_key = api_key
        self.base_url = base_url
        self.smarter_model = smarter_model
        
        # Create client for the smarter model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # Create a separate client for the smarter model if a different API base is specified
        if smarter_model_api_base and smarter_model_api_base != base_url:
            print("Using separate client for smarter model with different API base")
            self.smarter_client = OpenAI(
                api_key=api_key,
                base_url=smarter_model_api_base
            )
        else:
            self.smarter_client = self.client
            
        self.emitter = SignalEmitter()
        
    def process_question(self, extracted_data):
        """Process a question using the AI model"""
        if not extracted_data.get("question_found"):
            print("No question found. Skipping answering step.")
            self.emitter.response_chunk_received.emit("Didn't find any questions.")
            self.emitter.response_finished.emit()
            return
            
        if not extracted_data.get("question") or not extracted_data.get("choices"):
            print("Question found but question/choices missing. Skipping answering step.")
            self.emitter.response_chunk_received.emit("Found question but couldn't extract details.")
            self.emitter.response_finished.emit()
            return

        question = extracted_data["question"]
        choices = extracted_data["choices"]

        print(f"\n--- Answering MCQ using {self.smarter_model} ---")
        print(f"Question: {question}")
        print(f"Choices: {choices}")

        try:
            # --- Get Answer and Explanation ---
            answering_prompt = f"""
            You are an expert AI assistant. Answer the following multiple-choice question and provide a brief explanation for your choice.
            Limit your total response (answer + explanation) to approximately 700 characters.
            Be concise and clear. State the correct choice first, then the explanation.

            Question:
            {question}

            Choices:
            {chr(10).join(f'- {choice}' for choice in choices)}

            Your Answer (Correct Choice + Brief Explanation):
            """

            context_content = f"Context from extraction:\nQuestion: {question}\nChoices:\n" + "\n".join(f"- {choice}" for choice in choices)

            stream = self.smarter_client.chat.completions.create(
                model=self.smarter_model,
                messages=[
                    {"role": "system", "content": context_content},
                    {"role": "system", "content": "You are a helpful AI assistant specializing in answering MCQs concisely."},
                    {"role": "user", "content": answering_prompt}
                ],
                stream=True,
                max_tokens=200
            )

            full_response_content = ""
            for chunk in stream:
                content_chunk = chunk.choices[0].delta.content
                if content_chunk is not None:
                    full_response_content += content_chunk
                    self.emitter.response_chunk_received.emit(content_chunk)

            self.emitter.response_finished.emit()

            with open('openai_logs.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n\n=== {datetime.datetime.now().isoformat()} ===\n")
                f.write(f"Extracted Question:\n{question}\n")
                f.write(f"Extracted Choices:\n{choices}\n\n")
                f.write(f"Answering Prompt (User):\n{answering_prompt}\n\n")
                f.write(f"Response (Smarter Model):\n{full_response_content}\n")

            print(f"Full OpenAI response logged. Length: {len(full_response_content)}")

        except Exception as e:
            error_message = f"Error during answering: {str(e)}"
            print(error_message)
            self.emitter.response_chunk_received.emit(error_message)
            self.emitter.response_finished.emit() 