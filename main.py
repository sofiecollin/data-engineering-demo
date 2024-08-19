import requests
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import random

def fetch_trivia_questions(amount, category):
    """
    Fetch trivia questions from Open Trivia Database API.

    :param amount: Number of questions to fetch
    :param category: Category of the questions
    :return: JSON response containing trivia questions
    """
    url = f"https://opentdb.com/api.php?amount={amount}&category={category}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json().get('results')
        if not data:
            st.error("No data received from API.")
            return None
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching trivia questions: {e}")
        return None
    
def transform_trivia_data(raw_data):
    """
    Transform raw trivia data into a structured format and validate the data.

    :param raw_data: JSON response from Open Trivia Database API
    :return: List of dictionaries containing transformed trivia data
    """
    if not raw_data:
        return None

    transformed_data = []
    try:
        for item in raw_data:
            if 'question' in item and 'correct_answer' in item and 'incorrect_answers' in item:
                transformed_data.append({
                    'question': item.get('question'),
                    'correct_answer': item.get('correct_answer'),
                    'incorrect_answers': ', '.join(item.get('incorrect_answers')),
                    'difficulty': item.get('difficulty'),
                    'category': item.get('category'),
                    'type': item.get('type')
                })
        return transformed_data
    except Exception as e:
        st.error(f"Error transforming trivia data: {e}")
        return None

def load_data_to_db(transformed_data):
    """
    Load transformed trivia data into SQLite database.

    :param transformed_data: List of dictionaries containing transformed trivia data
    """
    if not transformed_data:
        return

    try:
        conn = sqlite3.connect('trivia.db')
        cursor = conn.cursor()

        # Create the trivia table if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS trivia
                          (question TEXT, correct_answer TEXT, incorrect_answers TEXT, difficulty TEXT, 
                           category TEXT, type TEXT)''')

        # Insert transformed trivia data into the trivia table
        for data in transformed_data:
            cursor.execute('''INSERT INTO trivia (question, correct_answer, incorrect_answers, difficulty, category, type)
                              VALUES (?, ?, ?, ?, ?, ?)''',
                              (data['question'], data['correct_answer'], data['incorrect_answers'], 
                               data['difficulty'], data['category'], data['type']))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Error loading data into database: {e}")
    finally:
        if conn:
            conn.close()

def visualize_data():
    try:
        conn = sqlite3.connect('trivia.db')
        df = pd.read_sql_query("SELECT * FROM trivia", conn)
        
        # Example visualization: Number of questions by difficulty
        difficulty_counts = df['difficulty'].value_counts()
        difficulty_counts.plot(kind='bar')
        plt.title('Number of Questions by Difficulty')
        plt.xlabel('Difficulty')
        plt.ylabel('Number of Questions')
        plt.show()
    except sqlite3.Error as e:
        st.error(f"Error accessing database: {e}")
    except Exception as e:
        st.error(f"Error visualizing data: {e}")
    finally:
        if conn:
            conn.close()

def etl_pipeline(amount, category):
    raw_data = fetch_trivia_questions(amount, category)
    transformed_data = transform_trivia_data(raw_data)
    load_data_to_db(transformed_data)

def fetch_random_questions(num_questions):
    try:
        conn = sqlite3.connect('trivia.db')
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT * FROM trivia ORDER BY RANDOM() LIMIT ?", (num_questions,))
        questions = cursor.fetchall()
        conn.close()
        return questions
    except sqlite3.Error as e:
        st.error(f"Error fetching random questions from database: {e}")
        return []

def main():
    st.title("Trivia Quiz Game")

    # Initialize session state variables
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'num_questions' not in st.session_state:
        st.session_state.num_questions = 5
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    if 'options' not in st.session_state:
        st.session_state.options = {}
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False

    def start_quiz():
        st.session_state.questions = fetch_random_questions(st.session_state.num_questions)
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.answers = {}
        st.session_state.options = {}
        st.session_state.quiz_started = True
        for i, question in enumerate(st.session_state.questions):
            options = question[2].split(", ") + [question[1]]  # incorrect_answers + correct_answer
            random.shuffle(options)
            st.session_state.options[i] = options

    def submit_answer():
        answer = st.session_state.get(f"q{st.session_state.current_question}_answer", None)
        if answer is not None:
            current_question_data = st.session_state.questions[st.session_state.current_question]
            correct_answer = current_question_data[1]
            if answer == correct_answer:
                st.session_state.score += 1
            st.session_state.answers[st.session_state.current_question] = answer
            st.session_state.current_question += 1

    st.sidebar.header("Quiz Settings")
    st.session_state.num_questions = st.sidebar.slider(
        "Number of Questions", 
        min_value=1, 
        max_value=10, 
        value=st.session_state.num_questions,
        key='num_questions_slider'
    )

    if st.sidebar.button("Start Quiz"):
        start_quiz()
    
    if st.session_state.quiz_started:
        if st.session_state.current_question < len(st.session_state.questions):
            current_question_data = st.session_state.questions[st.session_state.current_question]

            st.subheader(f"Question {st.session_state.current_question + 1}")
            st.write(current_question_data[0])  # question text
            options = st.session_state.options[st.session_state.current_question]
            
            answer = st.radio(
                "Select an answer:", 
                options, 
                key=f"q{st.session_state.current_question}_answer"
            )

            if st.button("Submit", key=f"submit{st.session_state.current_question}"):
                submit_answer()
                st.rerun()

        if st.session_state.current_question >= len(st.session_state.questions):
            st.subheader(f"Your Score: {st.session_state.score}/{st.session_state.num_questions}")
            st.write("Quiz finished! You can restart the quiz by selecting the number of questions and clicking on 'Start Quiz'.")

if __name__ == "__main__":
    main()



