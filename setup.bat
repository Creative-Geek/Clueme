@echo off
echo Installing uv...
pip install uv

echo Creating virtual environment...
uv venv

echo Activating virtual environment...
call .venv\Scripts\activate

echo Installing dependencies...
uv pip install -r requirements.txt

echo Creating .env file...
echo OPENAI_API_KEY=your_api_key_here > .env
echo OPENAI_API_BASE=your_custom_endpoint_url >> .env
echo OPENAI_MODEL=your_model_name >> .env

echo Setup complete! Please edit the .env file with your actual values.
echo To run the application, use: python stealth_assistant.py 