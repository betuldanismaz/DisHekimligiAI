import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="DisHekimligiAI - Ana Sayfa", layout="wide")
st.title("🦷 DisHekimligiAI")

st.markdown(
    """
hoş geldiniz
    """
)

# Kısa durum bilgisi (isteğe bağlı)
api_key = os.getenv("GEMINI_API_KEY") or (st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets else None)
st.info(f"API durumu: {'✅ ayarlı' if api_key else '❌ GEMINI_API_KEY eksik'}")

st.markdown("---")
st.header("Nasıl ilerlemeli")
st.write(
    "- Sol menüden `Chat` seçeneğini seçin ve oradaki arayüzü kullanın.\n"
)
