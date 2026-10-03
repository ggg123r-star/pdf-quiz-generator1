@echo off
chcp 65001 >nul
echo ==========================================
echo PDF AI 문제 생성기 - 필요한 프로그램 설치
echo ==========================================
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo 설치가 끝났습니다.
pause
