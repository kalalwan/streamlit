import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('survey_responses.db')
cursor = conn.cursor()

try:
    # Drop the responses table if it exists
    cursor.execute("DROP TABLE IF EXISTS responses")
    
    # Recreate the responses table
    cursor.execute('''CREATE TABLE responses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT, 
                  q1_problem TEXT,
                  q2_behavior_change TEXT,
                  q3_whose_behavior TEXT,
                  q4_beneficiary TEXT,
                  q5_current_behavior TEXT,
                  q6_desired_behavior TEXT,
                  q7_frictions TEXT,
                  q7_explain TEXT,
                  q8_address_problem TEXT,
                  q9_patient_journey TEXT,
                  q10_settings TEXT)''')
    
    # Commit the changes
    conn.commit()
    
    print("The responses table has been dropped and recreated.")

except sqlite3.Error as e:
    print(f"An error occurred: {e}")

finally:
    # Close the connection
    conn.close()