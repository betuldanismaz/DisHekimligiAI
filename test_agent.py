# python test_agent.py
from dotenv import load_dotenv
load_dotenv()
try:
    from app.agent import DentalEducationAgent
    a = DentalEducationAgent(api_key=None, model_name="gemini-2.5-flash")
    print("Agent oluşturuldu")
except Exception as e:
    print("Agent başlatılamadı:", type(e).__name__, str(e))