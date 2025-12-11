"""
Reusable Sidebar Component
==========================
Centralized sidebar logic for all pages with profile, case selection, and navigation.
"""

import streamlit as st
from typing import Optional, Dict, Callable
import os


# Case options configuration
CASE_OPTIONS = {
    "Oral Liken Planus (Orta)": "olp_001",
    "Kronik Periodontitis (Zor)": "perio_001",
    "Primer Herpes (Orta)": "herpes_primary_01",
    "Behçet Hastalığı (Zor)": "behcet_01",
    "Sekonder Sifiliz (Zor)": "syphilis_02"
}

DEFAULT_MODEL = "models/gemini-2.5-flash-lite"
MODEL_OPTIONS = [
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.0-flash-exp",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro"
]


def render_sidebar(
    page_type: str = "default",
    show_case_selector: bool = True,
    show_model_selector: bool = False,
    custom_actions: Optional[Dict[str, Callable]] = None
) -> Dict[str, any]:
    """
    Render reusable sidebar with common elements.
    
    Args:
        page_type: Type of page ('chat', 'stats', 'home', 'default')
        show_case_selector: Whether to show case selection dropdown
        show_model_selector: Whether to show model selection dropdown
        custom_actions: Dictionary of {button_label: callback_function}
    
    Returns:
        Dictionary containing:
        - selected_case_id: Currently selected case ID
        - selected_case_name: Currently selected case name
        - selected_model: Currently selected model (if show_model_selector=True)
    """
    
    result = {}
    
    with st.sidebar:
        
        # Import and show profile card
        try:
            from app.student_profile import show_profile_card
            show_profile_card()
        except Exception as e:
            st.error(f"Profile yüklenemedi: {e}")
        
        
        # ==================== CASE SELECTOR ====================
        if show_case_selector:
            st.subheader("📂 Vaka Seçimi")
            
            selected_case_name = st.selectbox(
                "Aktif Vaka:",
                list(CASE_OPTIONS.keys()),
                key="case_selector"
            )
            selected_case_id = CASE_OPTIONS[selected_case_name]
            
            # Initialize or update current case
            if "current_case_id" not in st.session_state:
                st.session_state.current_case_id = selected_case_id
            
            # Handle case change
            if st.session_state.current_case_id != selected_case_id:
                st.session_state.current_case_id = selected_case_id
                
                # Clear page-specific state on case change
                if page_type == "chat":
                    st.session_state.messages = []
                    st.session_state.db_session_id = None
                
                st.success(f"✅ Vaka değiştirildi: {selected_case_name}")
                st.rerun()
            
            result["selected_case_id"] = selected_case_id
            result["selected_case_name"] = selected_case_name
            
            st.divider()
        
        # ==================== MODEL SELECTOR ====================
        if show_model_selector:
            st.subheader("🤖 Model Ayarları")
            
            # Initialize selected_model if not exists
            if "selected_model" not in st.session_state:
                st.session_state.selected_model = DEFAULT_MODEL
            
            # Get current index
            try:
                idx = MODEL_OPTIONS.index(st.session_state.selected_model)
            except Exception:
                idx = 0
            
            selected_model = st.selectbox(
                "Model Seçin:",
                MODEL_OPTIONS,
                index=idx,
                key="selected_model"
            )
            
            result["selected_model"] = selected_model
            
            st.divider()
        
        # ==================== CUSTOM ACTIONS ====================
        if custom_actions:
            for label, callback in custom_actions.items():
                if st.button(label, width="stretch"):
                    callback()
        
        # ==================== NAVIGATION ====================
        st.subheader("🧭 Navigasyon")
        
        nav_col1, nav_col2 = st.columns(2)
        
        with nav_col1:
            if st.button("🏠 Ana Sayfa", width="stretch", type="secondary"):
                st.switch_page("pages/0_home.py")
        
        with nav_col2:
            if st.button("📊 İstatistikler", width="stretch", type="secondary"):
                st.switch_page("pages/5_stats.py")
        
        if page_type != "chat":
            if st.button("💬 Vaka Çalışması", width="stretch", type="primary"):
                st.switch_page("pages/3_chat.py")
        
        # Account link
        if page_type != "account":
            if st.button("👤 Hesabım", width="stretch", type="secondary"):
                st.switch_page("pages/2_account.py")
        
        st.divider()
        
        # ==================== SYSTEM INFO ====================
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        with st.expander("ℹ️ Sistem Bilgisi", expanded=False):
            st.caption(f"**API:** {'✅ Aktif' if GEMINI_API_KEY else '❌ Eksik'}")
            
            if show_case_selector:
                st.caption(f"**Vaka:** {result.get('selected_case_name', 'N/A')}")
            
            if show_model_selector:
                st.caption(f"**Model:** {result.get('selected_model', 'N/A')}")
            
            # Session stats
            if "messages" in st.session_state:
                st.caption(f"**Mesaj Sayısı:** {len(st.session_state.messages)}")
        
        
        # ==================== LOGOUT ====================
        st.markdown("---")
        
        def logout():
            """Clear session state and redirect to login"""
            st.session_state.clear()
            st.switch_page("pages/1_login.py")
        
        if st.button("🚪 Çıkış Yap", width="stretch", type="secondary", key="sidebar_logout_btn", on_click=logout):
            pass  # Logic handled by on_click callback
    
    return result
