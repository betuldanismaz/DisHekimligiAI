import streamlit as st
import json
import sys
import os

# Python path ayarı (Modüllerin bulunabilmesi için)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.med_gemma_service import MedGemmaService

# Initialize the service with caching to avoid re-initializing on every rerun
@st.cache_resource
def get_med_gemma_service():
    return MedGemmaService()

try:
    med_gemma_service = get_med_gemma_service()
except ValueError as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="MedGemma Validator",
    page_icon="🩺",
    layout="wide"
)

st.title("🩺 MedGemma: Klinik Karar Doğrulayıcı")
st.markdown("""
Bu modül, **Google Gemma-2-9b-it** modelini kullanarak klinik kararlarınızı gerçek zamanlı olarak denetler.
Normal bir sohbet botu değildir; verdiğiniz kararları **tıbbi kurallara** göre puanlar.
""")

# --- Yan Menü: Senaryo Simülasyonu ---
with st.sidebar:
    st.header("🧪 Test Senaryosu Seç")
    st.info("Modeli test etmek için bir vaka senaryosu seçin.")
    
    scenario_type = st.radio(
        "Vaka Durumu:",
        ["Mide Ülseri (NSAID Riski)", "Penisilin Alerjisi", "Diyabetik Hasta", "Hamilelik (1. Trimester)", "Oral Liken Planus"]
    )

    # Seçilen senaryoya göre "Mock" (Taklit) Kurallar ve Bağlam
    
    if scenario_type == "Penisilin Alerjisi":
        context_summary = "Hasta 12 yaşında kız çocuğu. Şikayet: Yüzde şişlik (Abse). Özgeçmiş: Penisilin anafilaksisi."
        active_rules = {
            "contraindications": ["Do NOT prescribe Penicillin-group antibiotics (Amoxicillin, Augmentin)."],
            "recommended_action": ["Prescribe Clindamycin or Macrolides if antibiotic is strictly necessary."]
        }

    elif scenario_type == "Diyabetik Hasta":
        context_summary = "Hasta 60 yaşında, Tip 2 Diyabet (HbA1c: 9.5). Şikayet: Çekim sonrası iyileşmeyen yara."
        active_rules = {
            "precautions": ["High risk of infection due to uncontrolled diabetes.", "Avoid invasive surgery until blood sugar is regulated if possible."],
            "required_history": ["Check latest glucose levels"]
        }
    
    elif scenario_type == "Hamilelik (1. Trimester)":
        context_summary = "Hasta 28 yaşında, 10 haftalık hamile. Şikayet: Şiddetli diş eti kanaması."
        active_rules = {
            "contraindications": ["Avoid Tetracyclines (staining risk).", "Avoid prolonged NSAID use."],
            "safe_drugs": ["Paracetamol is category B (Safe).", "Amoxicillin is category B (Safe)."]
        }

    else: # Oral Liken Planus
        context_summary = "Hasta 45 yaşında, ağzında beyaz çizgiler ve acı hissi var."
        active_rules = {
            "contraindications": ["Systemic steroids without BP monitoring", "Surgical excision for generalized lesions"],
            "required_history": ["Medication history (ACE inhibitors)", "History of skin lesions"],
            "required_exam": ["Check for Wickham striae", "Bilateral examination"]
        }

# --- Chat Arayüzü ---

# Mesaj geçmişini başlat
if "med_messages" not in st.session_state:
    st.session_state.med_messages = []

# Geçmiş mesajları ekrana yaz
for message in st.session_state.med_messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            # Asistan mesajı JSON formatındaysa özel gösterim yap
            try:
                content_json = json.loads(message["content"])
                
                # Görselleştirilmiş Feedback Kartı
                if content_json.get("safety_violation"):
                    st.error("🚨 GÜVENLİK İHLALİ TESPİT EDİLDİ")
                elif not content_json.get("is_clinically_accurate"):
                    st.warning("⚠️ Klinik Hata / Eksik")
                else:
                    st.success("✅ Klinik Olarak Doğru")
                
                st.write(f"**Analiz:** {content_json.get('feedback')}")
                
                if content_json.get("missing_critical_info"):
                    st.write("**Eksik Bırakılanlar:**")
                    for item in content_json["missing_critical_info"]:
                        st.markdown(f"- {item}")
                
                with st.expander("Ham JSON Verisi"):
                    st.json(content_json)

            except:
                st.write(message["content"])
        else:
            st.write(message["content"])

# Kullanıcı Girişi
if prompt := st.chat_input("Klinik kararınızı veya reçetenizi yazın..."):
    # 1. Kullanıcı mesajını ekle ve göster
    st.session_state.med_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 2. AI Cevabını Üret
    with st.chat_message("assistant"):
        with st.spinner("MedGemma kuralları denetliyor..."):
            
            # Servisi çağır (Backend Logic)
            try:
                validation_result = med_gemma_service.validate_clinical_action(
                    student_text=prompt,
                    rules=active_rules,
                    context_summary=context_summary
                )
                
                # Sonucu JSON string olarak sakla (geçmişte gösterebilmek için)
                result_str = json.dumps(validation_result)
                st.session_state.med_messages.append({"role": "assistant", "content": result_str})
                
                # Ekrana bas (Yukarıdaki formatlama mantığının aynısı)
                if validation_result.get("safety_violation"):
                    st.error("🚨 GÜVENLİK İHLALİ TESPİT EDİLDİ")
                elif not validation_result.get("is_clinically_accurate"):
                    st.warning("⚠️ Klinik Hata / Eksik")
                else:
                    st.success("✅ Klinik Olarak Doğru")
                
                st.write(f"**Analiz:** {validation_result.get('feedback')}")
                
                if validation_result.get("missing_critical_info"):
                    st.write("**Eksik Bırakılanlar:**")
                    for item in validation_result["missing_critical_info"]:
                        st.markdown(f"- {item}")
            
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")