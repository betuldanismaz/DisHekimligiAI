"""Streamlit entry point for the AI Oral Pathology assistant."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / "DisHekimligiAI"

if APP_DIR.exists() and str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from pages.home import main as render_home  # type: ignore
except Exception as exc:  # pragma: no cover - minimal UI fallback
    st.set_page_config(page_title="AI Oral Pathology Assistant", page_icon="AI")
    st.error("Ana sayfa yuklenemedi. Lutfen uygulama dosyalarini kontrol edin.")
    st.exception(exc)
else:
    render_home()

