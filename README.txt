PyMaster Arena — Python Quiz Application
========================================

FEATURES
- Registration and login (passwords are hashed)
- Dashboard with recent quiz scores
- 10 randomized MCQ questions per quiz
- Question bank of 20 Python basics questions
- Correctly answered questions are not repeated until the bank is exhausted
- Score/result page
- SQLite database (created automatically)

RUN ON A COMPUTER
1. Install Python 3.10+ from https://python.org
2. Open a terminal inside this project folder.
3. Run: python -m pip install -r requirements.txt
4. Run: python app.py
5. Open: http://127.0.0.1:5000

NOTE
This is a student project/demo. Change app.secret_key before deploying publicly.
Add your own questions inside the QUESTIONS list in app.py.
