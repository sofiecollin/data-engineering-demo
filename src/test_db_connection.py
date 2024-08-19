import pandas as pd
import sqlite3

conn = sqlite3.connect('trivia.db')
df = pd.read_sql_query("SELECT question, correct_answer FROM trivia", conn)
print(df)
conn.close()