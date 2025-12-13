"""
İstatistik Sayfası - Dental Tutor AI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.student_profile import init_student_profile
from app.frontend.components import render_sidebar
from app.analytics_engine import analyze_performance, generate_report_text
from db.database import get_student_detailed_history, init_db
import json

# Initialize systems
init_student_profile()
init_db()

# Page config
st.set_page_config(
    page_title="Dental Tutor AI - İstatistikler",
    page_icon="📊",
    layout="wide"
)

# ==================== SIDEBAR ====================
render_sidebar(
    page_type="stats",
    show_case_selector=False,
    show_model_selector=False
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📊 Performans İstatistikleri")
st.markdown("---")

# ==================== LOAD DATA FROM DATABASE ====================
# Get student ID
profile = st.session_state.get("student_profile") or {}
student_id = profile.get("student_id", "web_user_default")

# Load stats from database using refactored function
stats = get_student_detailed_history(student_id)
action_history = stats["action_history"]
total_score = stats["total_score"]
total_actions = stats["total_actions"]
completed_cases = stats["completed_cases"]

# Overview Metrics
st.markdown("## 🎯 Genel Bakış")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-value">{total_score}</p>
        <p class="metric-label">Toplam Puan</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
        <p class="metric-value">{total_actions}</p>
        <p class="metric-label">Toplam Eylem</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    avg_score = total_score / total_actions if total_actions > 0 else 0
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
        <p class="metric-value">{avg_score:.1f}</p>
        <p class="metric-label">Ortalama Puan/Eylem</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
        <p class="metric-value">{len(completed_cases)}</p>
        <p class="metric-label">Tamamlanan Vaka</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==================== WEAKNESS DETECTION ====================
if action_history:
    # Analyze performance
    df = pd.DataFrame(action_history)
    analysis = analyze_performance(df)
    
    # Display recommendation
    if analysis.get('recommendation'):
        st.markdown("## 💡 Gelişim Önerileri")
        st.warning(analysis['recommendation'])
        st.markdown("---")

# ==================== DOWNLOAD REPORT BUTTON ====================
if action_history:
    col_download1, col_download2 = st.columns([3, 1])
    
    with col_download2:
        # Generate report text
        analysis_for_report = analyze_performance(pd.DataFrame(action_history)) if action_history else {}
        report_text = generate_report_text(stats, analysis_for_report)
        
        st.download_button(
            label="📄 Karneyi İndir",
            data=report_text,
            file_name=f"dental_tutor_karne_{student_id}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            type="primary",
            use_container_width=True
        )
    
    st.markdown("---")

# Action History
if action_history:
    st.markdown("## 📋 Son Eylemler")
    
    # Create DataFrame
    df = pd.DataFrame(action_history)
    
    # Display table
    st.dataframe(
        df[['timestamp', 'case_id', 'action', 'score', 'outcome']].tail(10),
        width='stretch',
        hide_index=True
    )
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Puan Trendi")
        
        if len(df) > 0:
            df['cumulative_score'] = df['score'].cumsum()
            
            fig = px.line(
                df, 
                y='cumulative_score',
                title='Kümülatif Puan',
                labels={'cumulative_score': 'Toplam Puan', 'index': 'Eylem Sırası'}
            )
            fig.update_traces(line_color='#667eea', line_width=3)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("### 🎯 Vaka Dağılımı")
        
        case_counts = df['case_id'].value_counts()
        
        fig = px.pie(
            values=case_counts.values,
            names=case_counts.index,
            title='Vaka Başına Eylem Sayısı'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # Score Distribution
    st.markdown("### 📊 Puan Dağılımı")
    
    fig = px.histogram(
        df, 
        x='score',
        nbins=20,
        title='Eylem Puanları Histogramı',
        labels={'score': 'Puan', 'count': 'Frekans'}
    )
    fig.update_traces(marker_color='#667eea')
    st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # Performance by Action Type
    if 'action' in df.columns:
        st.markdown("### 🔍 Eylem Tipine Göre Performans")
        
        action_stats = df.groupby('action').agg({
            'score': ['count', 'sum', 'mean']
        }).round(2)
        action_stats.columns = ['Kullanım Sayısı', 'Toplam Puan', 'Ortalama Puan']
        action_stats = action_stats.sort_values('Toplam Puan', ascending=False)
        
        st.dataframe(action_stats, width='stretch')

else:
    st.info("📭 Henüz eylem geçmişi bulunmuyor. Vaka çalışmasına başlamak için chat sayfasına gidin!")
    
    if st.button("💬 Vaka Çalışmasına Başla", type="primary"):
        st.switch_page("pages/3_chat.py")

st.markdown("---")

# Back to Home
if st.button("🏠 Ana Sayfaya Dön", width="stretch"):
    st.switch_page("pages/0_home.py")
