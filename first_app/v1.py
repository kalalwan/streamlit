import streamlit as st
import pandas as pd
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import re

# Create the SQL connection to survey_db as specified in your secrets file.
conn = st.connection('survey_db', type='sql')

# Create the table if it doesn't exist
with conn.session as s:
    s.execute('''CREATE TABLE IF NOT EXISTS responses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    s.commit()

def main():
    st.set_page_config(page_title="BEAR's North Star", page_icon="🐻", layout="wide")
    
    if 'page' not in st.session_state:
        st.session_state.page = 'home'

    show_sidebar()

    if st.session_state.page == 'home':
        show_home()
    elif st.session_state.page == 'problem':
        show_problem_survey()
    elif st.session_state.page == 'scientist':
        show_scientist_dashboard()

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
            with conn.session as s:
                s.execute("""
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
                s.commit()
            st.success("Survey submitted successfully!")
    
    if st.button("Back to Home", key="problem_back_survey"):
        st.session_state.page = 'home'
        st.rerun()

def safe_json_loads(x):
    try:
        return json.loads(x)
    except json.JSONDecodeError:
        return []
    except TypeError:
        return []

def show_scientist_dashboard():
    st.title("Behavioural Scientist Dashboard")
    
    # Load data
    df = conn.query("SELECT * FROM responses", ttl=0)
    
    if df.empty:
        st.write("No responses yet.")
        return
    
    # Print current column names for debugging
    st.write("Current columns:", df.columns.tolist())
    
    # Convert JSON strings back to lists, handling potential errors
    json_columns = ['q3_whose_behavior', 'q4_beneficiary', 'q7_frictions', 'q9_patient_journey', 'q10_settings']
    for col in json_columns:
        if col in df.columns:
            df[col] = df[col].apply(safe_json_loads)
    
    # Keyword filter
    keyword = st.text_input("Filter responses by keyword:")
    if keyword:
        df = df[df.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)]
    
    # Display results in a table format
    st.write("Responses:")
    
    # Create a display dataframe without the ID column if it exists
    display_df = df.copy()
    if 'id' in display_df.columns:
        display_df = display_df.drop(columns=['id'])
    display_df = display_df.reset_index(drop=True)
    display_df.index += 1  # Start index from 1 instead of 0
    
    # Rename columns for better readability
    new_column_names = {
        'q1_problem': 'Problem',
        'q2_behavior_change': 'Behavior Change',
        'q3_whose_behavior': 'Whose Behavior',
        'q4_beneficiary': 'Beneficiary',
        'q5_current_behavior': 'Current Behavior',
        'q6_desired_behavior': 'Desired Behavior',
        'q7_frictions': 'Frictions',
        'q7_explain': 'Friction Explanation',
        'q8_address_problem': 'How It Addresses Problem',
        'q9_patient_journey': 'Patient Journey Stage',
        'q10_settings': 'Settings'
    }
    
    # Only rename columns that exist in the DataFrame
    display_df.rename(columns={col: new_name for col, new_name in new_column_names.items() if col in display_df.columns}, inplace=True)
    
    # Display the table
    st.dataframe(display_df, height=400)
    
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
    
    if st.button("Back to Home", key="scientist_back"):
        st.session_state.page = 'home'
        st.rerun()

def show_sidebar():
    with st.sidebar:
        st.title("Navigation")
        if st.button("Home", key="sidebar_home"):
            st.session_state.page = 'home'
            st.rerun()

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

if __name__ == "__main__":
    main()