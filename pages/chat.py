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


def _configure_genai(api_key: Optional[str]) -> Tuple[bool, Optional[str]]:
    if genai is None:
        return False, "google-generativeai yüklenmemiş."
    if not api_key:
        return False, "GEMINI_API_KEY yok."
    try:
        # bazı SDK sürümlerinde configure, bazılarında farklı olabilir
        if hasattr(genai, "configure"):
            genai.configure(api_key=api_key)
        elif hasattr(genai, "Client"):
            # örnek alternatif yapı
            genai.Client(api_key=api_key)
        return True, None
    except Exception as e:
        LOGGER.exception("genai configure hata: %s", e)
        return False, str(e)


def list_available_models(api_key: Optional[str]) -> List[str]:
    if not api_key or genai is None:
        return []
    ok, err = _configure_genai(api_key)
    if not ok:
        LOGGER.info("list_available_models configure failed: %s", err)
        return []

    names: List[str] = []
    try:
        # Denenecek olası listeleme fonksiyonları
        if hasattr(genai, "list_models"):
            raw = genai.list_models()
        elif hasattr(genai, "models") and hasattr(genai.models, "list"):
            raw = genai.models.list()
        elif hasattr(genai, "Model") and hasattr(genai.Model, "list"):
            raw = genai.Model.list()
        else:
            raw = []

        if not raw:
            return []

        for m in raw:
            if isinstance(m, dict) and "name" in m:
                names.append(m["name"])
            elif hasattr(m, "name"):
                names.append(getattr(m, "name"))
            elif isinstance(m, str):
                names.append(m)
    except Exception as e:
        LOGGER.exception("list_available_models hata: %s", e)

    gemini = [n for n in names if "gemini" in n.lower()]
    return gemini + [n for n in names if n not in gemini]


class DirectModelWrapper:
    """Wrap farklı genai SDK entrypoints behind a .generate(text) method."""
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str) -> Any:
        # assume genai.configure already called by caller
        # Try common call patterns
        try:
            if hasattr(genai, "generate_content"):
                return genai.generate_content(model=self.model_name, prompt=prompt)
            if hasattr(genai, "generate") and callable(genai.generate):
                return genai.generate(model=self.model_name, input=prompt)
            # older style
            if hasattr(genai, "completion") and hasattr(genai.completion, "create"):
                return genai.completion.create(model=self.model_name, prompt=prompt)
            # fallback: attempt class-based
            if hasattr(genai, "GenerativeModel"):
                m = genai.GenerativeModel(self.model_name)
                if hasattr(m, "generate_content"):
                    return m.generate_content(prompt)
                if hasattr(m, "generate"):
                    return m.generate(prompt)
        except Exception as e:
            LOGGER.exception("DirectModelWrapper.generate hata: %s", e)
            raise
        raise RuntimeError("Uygun generative çağrısı bulunamadı SDK içinde.")


def initialize_direct_model(api_key: Optional[str], model_name: Optional[str]) -> Tuple[Optional[DirectModelWrapper], Optional[str]]:
    if genai is None:
        return None, "google-generativeai yüklenmemiş."
    if not api_key:
        return None, "GEMINI_API_KEY bulunamadı."

    ok, err = _configure_genai(api_key)
    if not ok:
        return None, f"genai yapılandırılamadı: {err}"

    available = list_available_models(api_key)
    if model_name and available and model_name not in available:
        fallback = next((m for m in available if m.startswith("gemini-")), None)
        if fallback:
            model_name = fallback
        else:
            return None, f"Seçilen model ({model_name}) bulunamadı. Kullanılabilir: {', '.join(available[:MODEL_LOOKUP_LIMIT])}"

    if not model_name:
        model_name = DEFAULT_MODEL

    # Return wrapper that exposes .generate(prompt)
    try:
        wrapper = DirectModelWrapper(api_key=api_key, model_name=model_name)
        # quick smoke call is optional; skip to avoid extra billing — rely on later calls and error handling
        return wrapper, None
    except Exception as e:
        return None, f"Model başlatılamadı ({model_name}): {e}"


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
        # Always save & show the user's message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Basit selamlaşma tespiti (kısa ve tek kelime/ifade)
        greetings = {
            "merhaba", "selam", "selamlar", "hi", "hello", "sa", "hey",
            "günaydın", "iyi akşamlar", "iyi günler"
        }
        first_word = prompt.strip().split()[0].lower() if prompt.strip() else ""
        is_greeting = first_word in greetings and len(prompt.strip()) <= 30

        if is_greeting:
            # Kısa, deterministik cevap: agent/model çağrısı yapmadan dön
            reply = "Merhaba, sorunuz nedir?"
            with st.chat_message("assistant"):
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        else:
            # Normal pipeline: agent veya doğrudan model
            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.markdown("✍️ Yazıyor...")

                try:
                    if agent_instance:
                        result = agent_instance.process_student_action(student_id="web_user_1", raw_action=prompt)
                        full_text = result.get("final_feedback") or result.get("llm_interpretation", {}).get("explanatory_feedback", "")
                        if not full_text:
                            full_text = "(Agent yanıt üretmedi. Lütfen API anahtarını veya modeli kontrol edin.)"
                        placeholder.markdown(full_text)
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                    else:
                        # Direct model fallback: oluşturulmuş wrapper'ın .generate veya SDK'nın yöntemlerini kullan
                        recent = st.session_state.messages[-6:]
                        conversation_text = "\n".join(
                            f"{'Kullanıcı' if m['role']=='user' else 'Asistan'}: {m['content']}" for m in recent
                        )
                        instruction = (
                            f"Önceki konuşma:\n{conversation_text}\n\n"
                            f"Kullanıcı sorusu: {prompt}\n\n"
                            "Kısa, profesyonel ve kaynaklı cevap verin. Eğer emin değilseniz konservatif bir yanıt verin."
                        )

                        # Esnek çağrı: wrapper (generate) veya SDK (generate_content) desteklenir
                        resp = None
                        if hasattr(direct_model, "generate"):
                            resp = direct_model.generate(instruction)
                        elif hasattr(direct_model, "generate_content"):
                            resp = direct_model.generate_content(instruction)
                        elif genai is not None and hasattr(genai, "generate_content"):
                            resp = genai.generate_content(model=st.session_state.selected_model, prompt=instruction)

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