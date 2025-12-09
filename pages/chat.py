# ...existing code...
import os
import json
import logging
from typing import Optional, List, Tuple, Any, Dict

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Try optional imports (agent and genai). Failures handled at runtime.
try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    from app.agent import DentalEducationAgent
except Exception:
    DentalEducationAgent = None

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_LOOKUP_LIMIT = 20


def list_available_models(api_key: Optional[str]) -> List[str]:
    if not api_key or genai is None:
        return []
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models() or []
        names: List[str] = []
        for m in models:
            if isinstance(m, dict) and "name" in m:
                names.append(m["name"])
            elif isinstance(m, str):
                names.append(m)
        # prefer gemini names first
        gemini = [n for n in names if "gemini" in n]
        return gemini + [n for n in names if n not in gemini]
    except Exception as e:
        LOGGER.exception("list_available_models failed: %s", e)
        return []


def initialize_direct_model(api_key: Optional[str], model_name: Optional[str]) -> Tuple[Optional[Any], Optional[str]]:
    """Initialize a direct genai model instance (fallback if agent not used)."""
    if genai is None:
        return None, "google-generativeai kütüphanesi yüklenmemiş."
    if not api_key:
        return None, "GEMINI_API_KEY bulunamadı. .env dosyanızı kontrol edin."
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        return None, f"API anahtarı ile yapılandırma başarısız: {e}"

    available = list_available_models(api_key)
    if model_name and available and model_name not in available:
        fallback = next((m for m in available if m.startswith("gemini-")), None)
        if fallback:
            model_name = fallback
        else:
            return None, f"Seçilen model ({model_name}) bulunamadı. Kullanılabilir: {', '.join(available[:MODEL_LOOKUP_LIMIT])}"

    if not model_name:
        model_name = DEFAULT_MODEL

    try:
        model = genai.GenerativeModel(model_name)
        return model, None
    except Exception as e:
        avail_msg = f" Kullanılabilir modeller: {', '.join(available[:MODEL_LOOKUP_LIMIT])}" if available else ""
        return None, f"Model başlatılamadı ({model_name}): {e}.{avail_msg}"


def _safe_extract_text(response: Any) -> str:
    """Try multiple common shapes to extract text from genai responses."""
    try:
        # attribute-based
        for attr in ("text", "content", "output", "results", "candidates", "response", "result"):
            if hasattr(response, attr):
                v = getattr(response, attr)
                if isinstance(v, str) and v.strip():
                    return v.strip()
                if isinstance(v, list) and v:
                    first = v[0]
                    if isinstance(first, dict):
                        for k in ("content", "text"):
                            if first.get(k):
                                return str(first.get(k)).strip()
                    if isinstance(first, str) and first.strip():
                        return first.strip()
                if isinstance(v, dict):
                    for k in ("content", "text"):
                        if v.get(k):
                            return str(v.get(k)).strip()

        # dict-like
        if isinstance(response, dict):
            for k in ("text", "content", "message"):
                if response.get(k):
                    return str(response.get(k)).strip()

        # fallback: stringify
        s = str(response).strip()
        return s
    except Exception:
        return ""


def main() -> None:
    st.set_page_config(page_title="AI Chat - Oral Pathology", page_icon="💬", layout="centered")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Sidebar
    with st.sidebar:
        st.title("💬 Sohbet Ayarları")
        st.markdown("---")
        available_models = list_available_models(GEMINI_API_KEY)
        model_options = available_models[:MODEL_LOOKUP_LIMIT] or [DEFAULT_MODEL]
        if DEFAULT_MODEL in model_options:
            model_options = [DEFAULT_MODEL] + [m for m in model_options if m != DEFAULT_MODEL]
        # önce varsayılan session değeri ayarla (sadece yoksa)
        if "selected_model" not in st.session_state:
            st.session_state.selected_model = model_options[0]

        # selectbox widget'ını oluştur; session_state otomatik güncellenecek
        # index'i önceden ayarlanmış değere göre belirle (varsayılan 0)
        try:
            idx = model_options.index(st.session_state.selected_model)
        except Exception:
            idx = 0
        st.selectbox("🤖 Model Seçin", model_options, index=idx, key="selected_model")
        if st.button("🔄 Yeni Sohbet Başlat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.markdown("---")
        st.info(f"**API Durumu:** {'✅ Aktif' if GEMINI_API_KEY else '❌ Eksik'}")
        st.info(f"**Agent entegre:** {'✅' if DentalEducationAgent else '❌ (agent yok)'}")
        st.info(f"**Model:** {st.session_state.selected_model}")
        st.info(f"**Mesaj Sayısı:** {len(st.session_state.get('messages', []))}")

    st.title("💬 AI Oral Pathology Sohbeti")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Merhaba! Ben Oral Patoloji Asistanı. Oral patoloji konusunda sorularınızı yanıtlamak için buradayım. Size nasıl yardımcı olabilirim?"}
        ]

    # Try to instantiate agent (preferred). If fails, fallback to direct model use.
    agent_instance = None
    agent_err = None
    if DentalEducationAgent:
        try:
            agent_instance = DentalEducationAgent(api_key=GEMINI_API_KEY, model_name=st.session_state.selected_model)
        except Exception as e:
            agent_err = str(e)
            LOGGER.info("Agent başlatılamadı, fallback ile devam edilecek: %s", e)
            agent_instance = None

    direct_model, direct_err = initialize_direct_model(GEMINI_API_KEY, st.session_state.selected_model)
    # If neither agent nor direct model available, show error and stop.
    if not agent_instance and not direct_model:
        st.error("❌ Ajan veya model başlatılamadı.")
        if agent_err:
            st.error(f"Ajan hatası: {agent_err}")
        if direct_err:
            st.error(f"Model hatası: {direct_err}")
        st.stop()

    # render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # input handling
    if prompt := st.chat_input("Oral patoloji hakkında soru sorun..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("✍️ Yazıyor...")

            try:
                # Prefer agent pipeline if available
                if agent_instance:
                    result = agent_instance.process_student_action(student_id="web_user_1", raw_action=prompt)
                    full_text = result.get("final_feedback") or result.get("llm_interpretation", {}).get("explanatory_feedback", "")
                    if not full_text:
                        full_text = "(Agent yanıt üretmedi. Lütfen API anahtarını veya modeli kontrol edin.)"
                    placeholder.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                else:
                    # Direct model fallback: build simple instruction
                    recent = st.session_state.messages[-6:]
                    conversation_text = "\n".join(
                        f"{'Kullanıcı' if m['role']=='user' else 'Asistan'}: {m['content']}" for m in recent
                    )
                    instruction = (
                        f"Önceki konuşma:\n{conversation_text}\n\n"
                        f"Kullanıcı sorusu: {prompt}\n\n"
                        "Kısa, profesyonel ve kaynaklı cevap verin. Eğer emin değilseniz konservatif bir yanıt verin."
                    )

                    resp = direct_model.generate_content(instruction)
                    text = _safe_extract_text(resp) or ""
                    if not text:
                        text = "(Cevap alınamadı. Lütfen API anahtarını veya model erişimini kontrol edin.)"
                    placeholder.markdown(text)
                    st.session_state.messages.append({"role": "assistant", "content": text})

            except Exception as e:
                LOGGER.exception("chat handling failed: %s", e)
                err_text = f"⚠️ Bir hata oluştu: {e}"
                placeholder.markdown(err_text)
                st.session_state.messages.append({"role": "assistant", "content": err_text})


if __name__ == "__main__":
    main()
