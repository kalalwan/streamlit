import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from reportlab.lib.pagesizes import A6, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import json
import csv
import re

def safe_json_loads(json_str):
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return []  # Return an empty list if JSON decoding fails

# Initialize SQLite database
conn = sqlite3.connect('survey_responses.db', check_same_thread=False)
c = conn.cursor()

# Create the table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS responses
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              approved INTEGER DEFAULT 0,
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
conn.commit()

def main():
    st.set_page_config(page_title="BEAR's North Star", page_icon="🐻", layout="wide")
    
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    
    if 'csv_data' not in st.session_state:
        st.session_state.csv_data = None

    show_sidebar()

    if st.session_state.page == 'home':
        show_home()
    elif st.session_state.page == 'problem':
        show_problem_survey()
    elif st.session_state.page == 'scientist':
        show_scientist_dashboard()
    elif st.session_state.page == 'project_manager':
        show_project_manager_view()

def show_project_manager_view():
    st.title("Project Manager Dashboard")

    if 'pm_logged_in' not in st.session_state:
        st.session_state.pm_logged_in = False

    if not st.session_state.pm_logged_in:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            if username == "bear@rotman.utoronto.ca" and password == "mentalaccounting":
                st.session_state.pm_logged_in = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    if st.session_state.pm_logged_in:
        show_project_manager_dashboard()

    if st.button("Back to Home", key="pm_view_back"):
        st.session_state.page = 'home'
        st.session_state.pm_logged_in = False
        st.rerun()

def show_project_manager_dashboard():
    st.subheader("Project Manager Dashboard")

    col1, col2 = st.columns(2)

     # Debug section
    st.subheader("Debug Information")
    total_responses = pd.read_sql_query("SELECT COUNT(*) FROM responses", conn).iloc[0, 0]
    approved_responses = pd.read_sql_query("SELECT COUNT(*) FROM responses WHERE approved = 1", conn).iloc[0, 0]
    unapproved_responses = pd.read_sql_query("SELECT COUNT(*) FROM responses WHERE approved = 0", conn).iloc[0, 0]
    
    st.write(f"Total responses in database: {total_responses}")
    st.write(f"Approved responses: {approved_responses}")
    st.write(f"Unapproved responses: {unapproved_responses}")

    with col1:
        # CSV Upload
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv", key="csv_uploader")
        
        if uploaded_file is not None:
            if st.button("Process CSV"):
                df = pd.read_csv(uploaded_file)
                st.session_state.csv_data = df
                num_records = process_csv_upload(df)
                st.success(f"Successfully processed {num_records} records.")

        if st.session_state.csv_data is not None:
            st.write("Uploaded CSV data:")
            st.write(st.session_state.csv_data)

    with col2:
        # Show unapproved responses
        show_unapproved_responses()

def show_unapproved_responses():
    st.subheader("Unapproved Responses")
    
    # Load unapproved responses
    df = pd.read_sql_query("SELECT * FROM responses WHERE approved = 0", conn)
    
    if df.empty:
        st.write("No unapproved responses to review.")
    else:
        st.write(f"Number of unapproved responses: {len(df)}")
        
        # Select a response to review
        response_id = st.selectbox("Select a response to review:", df['id'].tolist())
        
        if response_id:
            review_response(response_id)

def review_response(response_id):
    # Fetch the selected response
    query = f"SELECT * FROM responses WHERE id = {response_id}"
    df = pd.read_sql_query(query, conn)
    row = df.iloc[0]

    st.subheader(f"Response {row['id']}")
    
    # Display all fields without allowing edits
    for column in df.columns:
        if column != 'id' and column != 'approved':
            st.write(f"{column}: {row[column]}")

    if st.button("Approve", key=f'approve_button_{response_id}'):
        approve_response(response_id)
        st.success("Response approved successfully!")
        st.rerun()

def approve_response(response_id):
    c.execute("UPDATE responses SET approved = 1 WHERE id = ?", (response_id,))
    conn.commit()
    
    # Verify the update
    c.execute("SELECT approved FROM responses WHERE id = ?", (response_id,))
    result = c.fetchone()
    if result and result[0] == 1:
        st.success(f"Response {response_id} approved successfully!")
    else:
        st.error(f"Failed to approve response {response_id}. Please try again.")

def update_response(response_id, title, q1_problem, q2_behavior_change, q3_whose_behavior, q4_beneficiary,
                    q5_current_behavior, q6_desired_behavior, q7_frictions, q7_explain,
                    q8_address_problem, q9_patient_journey, q10_settings):
    c.execute("""
        UPDATE responses
        SET title=?, q1_problem=?, q2_behavior_change=?, q3_whose_behavior=?, q4_beneficiary=?,
            q5_current_behavior=?, q6_desired_behavior=?, q7_frictions=?, q7_explain=?,
            q8_address_problem=?, q9_patient_journey=?, q10_settings=?
        WHERE id=?
    """, (title, q1_problem, q2_behavior_change, 
          json.dumps(q3_whose_behavior), 
          json.dumps(q4_beneficiary),
          q5_current_behavior, q6_desired_behavior, 
          json.dumps(q7_frictions), 
          q7_explain,
          q8_address_problem, 
          json.dumps(q9_patient_journey), 
          json.dumps(q10_settings), 
          response_id))
    conn.commit()

def show_home():
    st.title("BEAR's North Star")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("I have a behavioural problem"):
            st.session_state.page = 'problem'
            st.rerun()
    
    with col2:
        if st.button("I am a behavioural scientist"):
            st.session_state.page = 'scientist'
            st.rerun()

def show_problem_survey():
    st.title("Have a Behavioural Problem?")
    
    with st.form("survey_form"):
        q1 = st.text_area("1. What problem from your healthcare setting do you want to tackle? (required)")
        
        q2 = st.radio("2. Will a change in behavior address this problem? (required)", 
                      ["Yes", "No"])
        
        q3 = st.multiselect("3. Whose behaviour should primarily be changed?", 
                            ["Administrative Staff", "Dietician", "Educator", "Media", 
                             "Nurse", "Nurse Practitioner", "Patient", "Pharmacist", 
                             "Physician", "Public Health", "Social Worker", "Student", "Other"])
        
        if "Other" in q3:
            q3_other = st.text_input("If 'Other' was selected for Q3, please expand on your choice below.")
            q3.remove("Other")
            q3.append(q3_other)
        
        q4 = st.multiselect("4. Who will the primary beneficiary of this behaviour change be?",
                            ["Administrative Staff", "Dietician", "Educator", "Media", 
                             "Nurse", "Nurse Practitioner", "Patient", "Pharmacist", 
                             "Physician", "Public Health", "Social Worker", "Student", "Other"])
        
        if "Other" in q4:
            q4_other = st.text_input("If 'Other' was selected for Q4, please expand on your choice below.")
            q4.remove("Other")
            q4.append(q4_other)
        
        q5 = st.text_area("5. CURRENT BEHAVIOUR: What are they currently doing?")
        
        q6 = st.text_area("6. DESIRED BEHAVIOUR: What should they be doing that might solve the problem?")
        
        q7 = st.multiselect("7. Why might they not be doing the desired behavior? What might the frictions be?",
                            ["Ambiguity: unclear guidance to users to adopt desired behaviour",
                             "Low motivation or awareness: don't know, understand or appreciate the values of desired behaviour",
                             "Systemic corporation: the desired behaviour involves some changes to upstream/downstream practice in the first place",
                             "Complexity: nuances or variations of implementing interventions in real life",
                             "Research lagging behind: Researchers and/or healthcare practitioners need further understanding",
                             "Tech/tools constraints: the desired behaviour change is restricted due to underequipped or inaccessible technology/device/tools",
                             "Other"])
        
        if "Other" in q7:
            q7_other = st.text_input("If 'Other' was selected for Q7, please expand on your choice below.")
            q7.remove("Other")
            q7.append(q7_other)
        
        q7_explain = st.text_area("Please briefly explain your thoughts on Q7.")
        
        q8 = st.text_area("8. How will the behaviour change address the problem?")
        
        q9 = st.multiselect("9. At which stage of the patient journey map does this problem arise?",
                            ["Stage 1: Prevention, Trigger Event",
                             "Stage 2: Initial Visit, Diagnosis",
                             "Stage 3: Treatment, Clinical Care",
                             "Stage 4: Follow-Up, Ongoing Care",
                             "Other"])
        
        if "Other" in q9:
            q9_other = st.text_input("If 'Other' was selected for Q9, please expand on your choice below.")
            q9.remove("Other")
            q9.append(q9_other)
        
        q10 = st.multiselect("10. Does this problem manifest itself in any of the following settings?",
                             ["Primary Care",
                              "Hospital Care",
                              "Home and Long-Term Care",
                              "Community Care",
                              "Other"])
        
        if "Other" in q10:
            q10_other = st.text_input("If 'Other' was selected for Q10, please expand on your choice below.")
            q10.remove("Other")
            q10.append(q10_other)
        
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            c.execute("""
                INSERT INTO responses (
                    q1_problem, q2_behavior_change, q3_whose_behavior, q4_beneficiary,
                    q5_current_behavior, q6_desired_behavior, q7_frictions, q7_explain,
                    q8_address_problem, q9_patient_journey, q10_settings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q1, q2, json.dumps(q3), json.dumps(q4),
                q5, q6, json.dumps(q7), q7_explain,
                q8, json.dumps(q9), json.dumps(q10)
            ))
            conn.commit()
            st.success("Survey submitted successfully!")
    
    if st.button("Back to Home", key="problem_back_survey"):
        st.session_state.page = 'home'
        st.rerun()

def show_sidebar():
    with st.sidebar:
        st.title("Navigation")
        if st.button("Home", key="sidebar_home"):
            st.session_state.page = 'home'
            st.rerun()
        
        st.markdown("---")
        st.title("Admin Access")
        if st.button("Project Manager Login", key="sidebar_pm_login"):
            st.session_state.page = 'project_manager'
            st.rerun()

def show_scientist_dashboard():
    st.title("Behavioural Scientist Dashboard")
    
    # Load data
    df = pd.read_sql_query("SELECT * FROM responses WHERE approved = 1", conn)
    
    if df.empty:
        st.write("No approved responses yet.")
        return
    
    # Display results in a table format
    st.write("Approved Responses:")
    
    # Create a display dataframe
    display_df = df.copy()
    display_df = display_df.reset_index(drop=True)
    display_df.index += 1  # Start index from 1 instead of 0
    
    # Rename columns for better readability
    new_column_names = ['ID', 'Approved', 'Title', 'Problem', 'Behavior Change', 'Whose Behavior', 'Beneficiary',
                        'Current Behavior', 'Desired Behavior', 'Frictions', 'Friction Explanation',
                        'How It Addresses Problem', 'Patient Journey Stage', 'Settings']
    
    display_df.columns = new_column_names
    
    # Display the table
    st.dataframe(display_df)
        
    # Input field for response numbers
    response_numbers = st.text_input("Enter response numbers to download (comma-separated, e.g., 1,3,5):")
    
    # Download selected responses
    if st.button("Download Selected Responses"):
        if response_numbers:
            try:
                selected_indices = [int(idx.strip()) for idx in response_numbers.split(',')]
                selected_df = df.iloc[pd.Index(selected_indices) - 1]  # Adjust for 0-based indexing
                if not selected_df.empty:
                    pdf = create_index_cards_pdf(selected_df)
                    st.download_button(
                        label="Download PDF",
                        data=pdf,
                        file_name="selected_responses.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.warning("No valid response numbers found. Please check your input.")
            except (ValueError, IndexError):
                st.warning("Invalid input. Please enter valid comma-separated numbers within the range of responses.")
        else:
            st.warning("No response numbers entered. Please enter at least one response number.")
    
    if st.button("Back to Home", key="problem_back_scientist"):
        st.session_state.page = 'home'
        st.rerun()

def safe_json_loads(x):
    try:
        return json.loads(x)
    except json.JSONDecodeError:
        return []  # Return an empty list if JSON decoding fails

def create_index_cards_pdf(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SectionTitle', 
                              fontSize=18, 
                              textColor=colors.Color(1,0.71,0,1),  # FFB600 in RGB
                              spaceAfter=10))
    styles.add(ParagraphStyle(name='Entry', 
                              fontSize=12, 
                              spaceAfter=5))
    
    def strip_question_number(header):
        return re.sub(r'^\[?\d+\]?\s*', '', header)
    
    for index, row in df.iterrows():
        # Title Section
        if row['q6_desired_behavior'] and row['q1_problem']:
            elements.append(Paragraph(f"<b>Title</b>", styles['SectionTitle']))
            elements.append(Paragraph(f"{row['q6_desired_behavior']} to solve {row['q1_problem']}", styles['Entry']))
            elements.append(Spacer(1, 20))
        
        # Problem Statement Section
        problem_statements = []
        if row['q1_problem']:
            problem_statements.append(f"<b>{strip_question_number('q1_problem')}:</b> {row['q1_problem']}")
        if row['q9_patient_journey']:
            problem_statements.append(f"<b>{strip_question_number('q9_patient_journey')}:</b> {', '.join(row['q9_patient_journey'])}")
        if row['q10_settings']:
            problem_statements.append(f"<b>{strip_question_number('q10_settings')}:</b> {', '.join(row['q10_settings'])}")
        
        if problem_statements:
            elements.append(Paragraph("<b>Problem Statement</b>", styles['SectionTitle']))
            for statement in problem_statements:
                elements.append(Paragraph(statement, styles['Entry']))
            elements.append(Spacer(1, 20))
        
        # The Behaviour Change Section
        behaviour_changes = []
        if row['q2_behavior_change']:
            behaviour_changes.append(f"<b>{strip_question_number('q2_behavior_change')}:</b> {row['q2_behavior_change']}")
        if row['q5_current_behavior']:
            behaviour_changes.append(f"<b>{strip_question_number('q5_current_behavior').replace('CURRENT BEHAVIOUR', '')}:</b> {row['q5_current_behavior']}")
        if row['q6_desired_behavior']:
            behaviour_changes.append(f"<b>{strip_question_number('q6_desired_behavior').replace('DESIRED BEHAVIOUR', '')}:</b> {row['q6_desired_behavior']}")
        
        if behaviour_changes:
            elements.append(Paragraph("<b>The Behaviour Change</b>", styles['SectionTitle']))
            for change in behaviour_changes:
                elements.append(Paragraph(change, styles['Entry']))
            elements.append(Spacer(1, 20))
        
        # Barriers to Change Section
        if row['q7_frictions']:
            elements.append(Paragraph("<b>Barriers to Change</b>", styles['SectionTitle']))
            elements.append(Paragraph(f"<b>{strip_question_number('q7_frictions')}:</b> {', '.join(row['q7_frictions'])}", styles['Entry']))
            elements.append(Spacer(1, 20))
        
        # The Desired Outcome Section
        desired_outcomes = []
        if row['q8_address_problem']:
            desired_outcomes.append(f"<b>{strip_question_number('q8_address_problem')}:</b> {row['q8_address_problem']}")
        if row['q4_beneficiary']:
            desired_outcomes.append(f"<b>{strip_question_number('q4_beneficiary')}:</b> {', '.join(row['q4_beneficiary'])}")
        
        if desired_outcomes:
            elements.append(Paragraph("<b>The Desired Outcome</b>", styles['SectionTitle']))
            for outcome in desired_outcomes:
                elements.append(Paragraph(outcome, styles['Entry']))
        
        elements.append(PageBreak())
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def process_csv_upload(df):
    rows_processed = 0
    for _, row in df.iterrows():
        try:
            c.execute("""
                INSERT INTO responses (
                    approved, title, q1_problem, q2_behavior_change, q3_whose_behavior,
                    q4_beneficiary, q5_current_behavior, q6_desired_behavior,
                    q7_frictions, q7_explain, q8_address_problem, q9_patient_journey,
                    q10_settings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                0,  # approved (set to 0 for unapproved)
                row.get('title (generated by manual input from admin)', ''),
                row.get('1 what problem from your healthcare setting do you want to tackle', ''),
                row.get('2 will a change in behavior address this problem', ''),
                json.dumps(row.get('3 whose behaviour should primarily be changed', '').split(',') if row.get('3 whose behaviour should primarily be changed') else []),
                json.dumps(row.get('4 who will the primary beneficiary of this behaviour change be', '').split(',') if row.get('4 who will the primary beneficiary of this behaviour change be') else []),
                row.get('5 current behaviour what are they currently doing', ''),
                row.get('6 desired behaviour what should they be doing that might solve the problem', ''),
                json.dumps(row.get('7 why might they not be doing the desired behavior', '').split(',') if row.get('7 why might they not be doing the desired behavior') else []),
                row.get('please describe your response', ''),
                row.get('8 how will the behaviour change address the problem', ''),
                json.dumps(row.get('9 at which stage of the patient journey map does this problem arise', '').split(',') if row.get('9 at which stage of the patient journey map does this problem arise') else []),
                json.dumps(row.get('10 does this problem manifest itself in any of the following settings', '').split(',') if row.get('10 does this problem manifest itself in any of the following settings') else [])
            ))
            rows_processed += 1
        except Exception as e:
            st.error(f"Error processing row: {str(e)}")
            st.write(row)  # This will show the problematic row
    
    conn.commit()
    return rows_processed

if __name__ == "__main__":
    main()