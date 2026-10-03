@echo off
chcp 65001 >nul
echo PDF AI 문제 생성기를 시작합니다...
python -m streamlit run app.py
pause
