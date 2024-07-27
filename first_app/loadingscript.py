import sqlite3
import csv
import json

# Connect to the SQLite database
conn = sqlite3.connect('survey_responses.db')
cursor = conn.cursor()

def safe_json_dumps(value):
    if value:
        try:
            return json.dumps(value.split(','))
        except:
            return json.dumps([])
    else:
        return json.dumps([])

# Path to your CSV file
csv_file_path = '/Users/kamalalalwan/Desktop/streamlit/streamlit/first_app/Opportunity Map Survey Responses - Sheet1 (1).csv'  # Replace with your actual CSV file path

# Read the CSV and insert into the database
with open(csv_file_path, 'r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        cursor.execute("""
            INSERT INTO responses (
                q1_problem, q2_behavior_change, q3_whose_behavior, q4_beneficiary,
                q5_current_behavior, q6_desired_behavior, q7_frictions, q7_explain,
                q8_address_problem, q9_patient_journey, q10_settings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get('1 what problem from your healthcare setting do you want to tackle', ''),
            row.get('2 will a change in behavior address this problem', ''),
            safe_json_dumps(row.get('3 whose behaviour should primarily be changed', '')),
            safe_json_dumps(row.get('4 who will the primary beneficiary of this behaviour change be', '')),
            row.get('5 current behaviour what are they currently doing', ''),
            row.get('6 desired behaviour what should they be doing that might solve the problem', ''),
            safe_json_dumps(row.get('7 why might they not be doing the desired behavior', '')),
            row.get('please describe your response', ''),
            row.get('8 how will the behaviour change address the problem', ''),
            safe_json_dumps(row.get('9 at which stage of the patient journey map does this problem arise', '')),
            safe_json_dumps(row.get('10 does this problem manifest itself in any of the following settings', ''))
        ))

# Commit the changes and close the connection
conn.commit()
conn.close()

print("CSV data has been successfully inserted into the database.")