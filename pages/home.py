import streamlit as st

def main():
    # Sayfa yapılandırması
    st.set_page_config(
        page_title="AI Oral Pathology Assistant",
        page_icon="🦷",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Ana içerik
    st.title("🦷 AI Oral Pathology Assistant")
    st.markdown("---")
    
    # Hoş geldiniz mesajı
    st.header("Hoş Geldiniz!")
    st.write("Bu uygulama, oral patoloji alanında AI destekli asistanlık sağlamaktadır.")
    
    # Gelecek özellikler hakkında bilgi
    st.subheader("📋 Gelecek Özellikler")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**💬 AI Sohbet**\n\nGemini AI ile interaktif sohbet")
        st.info("**📊 Değerlendirme**\n\nOtomatik değerlendirme ve skorlama")
    
    with col2:
        st.info("**🎯 Senaryolar**\n\nVaka senaryoları ve analizler")
        st.info("**📈 İlerleme Takibi**\n\nÖğrenci ilerleme takibi")
    
    # Gezinme talimatları
    st.markdown("---")
    st.subheader("🚀 Başlarken")
    st.write("Sohbet özelliğini kullanmak için sol taraftaki navigasyon menüsünden **Chat** sayfasını seçin.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Powered by Google Gemini | Streamlit UI"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()