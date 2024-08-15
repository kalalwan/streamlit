import streamlit as st
import sqlite3
import pandas as pd
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import re
import os

st.set_page_config(page_title="BEAR's North Star", page_icon="🐻", layout="wide")

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Connect to the SQLite database in the same directory as the script
db_path = os.path.join(script_dir, 'survey_responses.db')

# Initialize SQLite database
@st.cache_resource
def get_database_connection():
    return sqlite3.connect(db_path, check_same_thread=False)

conn = get_database_connection()
c = conn.cursor()

# Create the table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS responses
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
conn.commit()

def main():
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    show_sidebar()

    if st.session_state.page == 'home':
        show_home()
    elif st.session_state.page == 'problem':
        show_problem_survey()
    elif st.session_state.page == 'scientist':
        show_scientist_dashboard()
    elif st.session_state.page == 'project_manager':
        if st.session_state.logged_in:
            show_project_manager_view()
        else:
            show_login()

def show_login():
    st.sidebar.title("Project Manager Login")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if email == "bear@rotman.utoronto.ca" and password == "mentalaccounting":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.sidebar.error("Incorrect email or password")

def show_project_manager_view():
    st.title("Project Manager Dashboard")

    # Load all submissions
    df = pd.read_sql_query("SELECT id, title, q1_problem FROM responses", conn)

    # Function to safely get the title or use a fallback
    def get_title(row):
        if pd.notna(row['title']) and row['title']:
            return row['title'][:50]
        elif pd.notna(row['q1_problem']) and row['q1_problem']:
            return row['q1_problem'][:50]
        else:
            return "No title or problem description available"

    # Create a selection box for choosing which submission to edit
    selected_id = st.selectbox(
        "Select a submission to edit:", 
        options=df['id'].tolist(),
        format_func=lambda x: f"ID {x}: {get_title(df[df['id']==x].iloc[0])}..."
    )

    if selected_id:
        edit_submission(selected_id)

    # Add new submission button
    if st.button("Add New Submission", key="add_new_submission"):
        new_id = add_new_submission()
        st.success(f"New submission added successfully! ID: {new_id}")
        st.rerun()

def edit_submission(submission_id):
    query = f"SELECT * FROM responses WHERE id = {submission_id}"
    df = pd.read_sql_query(query, conn)
    row = df.iloc[0]

    st.subheader(f"Editing Submission {submission_id}")

    json_columns = ['q3_whose_behavior', 'q4_beneficiary', 'q7_frictions', 'q9_patient_journey', 'q10_settings']
    for col in json_columns:
        if col in df.columns:
            row[col] = safe_json_loads(row[col])

    edited_row = {}

    def simple_match_defaults(stored_values, options):
        default_values = []
        for val in stored_values:
            val = val.upper()
            if val in options:
                default_values.append(val)
            else:
                # Check if any option contains this value as a substring
                matched = False
                for option in options:
                    if val in option:
                        default_values.append(option)
                        matched = True
                        break
                if not matched:
                    default_values.append("OTHER")
        return default_values

    for col in df.columns:
        if col == 'id':
            continue
        if col == 'q2_behavior_change':
            edited_row[col] = st.radio(col, options=['YES', 'NO'], index=0 if row[col] == 'YES' else 1, key=f"{submission_id}_{col}")
        elif col in ['q3_whose_behavior', 'q4_beneficiary']:
            options = ['ALL', 'ADMINISTRATIVE STAFF', 'DIETICIAN', 'EDUCATOR', 'MEDIA', 
                       'NURSE', 'NURSE PRACTITIONER', 'PATIENT', 'PHARMACIST', 
                       'PHYSICIAN', 'PUBLIC HEALTH', 'SOCIAL WORKER', 'STUDENT', 'OTHER']
            default_values = simple_match_defaults(row[col], options)
            edited_row[col] = st.multiselect(col, options=options, default=default_values, key=f"{submission_id}_{col}")
        elif col == 'q7_frictions':
            options = ['ALL', 
                       "AMBIGUITY: UNCLEAR GUIDANCE TO USERS TO ADOPT DESIRED BEHAVIOUR",
                       "LOW MOTIVATION OR AWARENESS: DON'T KNOW, UNDERSTAND OR APPRECIATE THE VALUES OF DESIRED BEHAVIOUR",
                       "SYSTEMIC CORPORATION: THE DESIRED BEHAVIOUR INVOLVES SOME CHANGES TO UPSTREAM/DOWNSTREAM PRACTICE IN THE FIRST PLACE",
                       "COMPLEXITY: NUANCES OR VARIATIONS OF IMPLEMENTING INTERVENTIONS IN REAL LIFE",
                       "RESEARCH LAGGING BEHIND: RESEARCHERS AND/OR HEALTHCARE PRACTITIONERS NEED FURTHER UNDERSTANDING",
                       "TECH/TOOLS CONSTRAINTS: THE DESIRED BEHAVIOUR CHANGE IS RESTRICTED DUE TO UNDEREQUIPPED OR INACCESSIBLE TECHNOLOGY/DEVICE/TOOLS",
                       "OTHER"]
            default_values = simple_match_defaults(row[col], options)
            edited_row[col] = st.multiselect(col, options=options, default=default_values, key=f"{submission_id}_{col}")
        elif col == 'q9_patient_journey':
            options = ['ALL', 
                       "STAGE 1: PREVENTION, TRIGGER EVENT",
                       "STAGE 2: INITIAL VISIT, DIAGNOSIS",
                       "STAGE 3: TREATMENT, CLINICAL CARE",
                       "STAGE 4: FOLLOW-UP, ONGOING CARE",
                       "OTHER"]
            default_values = simple_match_defaults(row[col], options)
            edited_row[col] = st.multiselect(col, options=options, default=default_values, key=f"{submission_id}_{col}")
        elif col == 'q10_settings':
            options = ['ALL', "PRIMARY CARE", "HOSPITAL CARE", "HOME AND LONG-TERM CARE", "COMMUNITY CARE", "OTHER"]
            default_values = simple_match_defaults(row[col], options)
            edited_row[col] = st.multiselect(col, options=options, default=default_values, key=f"{submission_id}_{col}")
        else:
            edited_row[col] = st.text_input(col, value=row[col], key=f"{submission_id}_{col}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(f"Update Submission", key=f"update_{submission_id}"):
            update_submission(submission_id, edited_row)
            st.success(f"Submission {submission_id} updated successfully!")

    with col2:
        if st.button(f"Delete Submission", key=f"delete_{submission_id}"):
            delete_submission(submission_id)
            st.warning(f"Submission {submission_id} deleted successfully!")
            st.rerun()

    with col3:
        if st.button("Back to Submission List", key="back_to_list"):
            st.rerun()

def update_submission(submission_id, data):
    query = """UPDATE responses SET
               title = ?, q1_problem = ?, q2_behavior_change = ?,
               q3_whose_behavior = ?, q4_beneficiary = ?, q5_current_behavior = ?,
               q6_desired_behavior = ?, q7_frictions = ?, q7_explain = ?,
               q8_address_problem = ?, q9_patient_journey = ?, q10_settings = ?
               WHERE id = ?"""
    c.execute(query, (data['title'], data['q1_problem'], data['q2_behavior_change'],
                      json.dumps(data['q3_whose_behavior']), json.dumps(data['q4_beneficiary']),
                      data['q5_current_behavior'], data['q6_desired_behavior'],
                      json.dumps(data['q7_frictions']), data['q7_explain'],
                      data['q8_address_problem'], json.dumps(data['q9_patient_journey']),
                      json.dumps(data['q10_settings']), submission_id))
    conn.commit()

def delete_submission(submission_id):
    c.execute("DELETE FROM responses WHERE id = ?", (submission_id,))
    conn.commit()

def add_new_submission():
    # Get the current maximum ID
    c.execute("SELECT MAX(id) FROM responses")
    max_id = c.fetchone()[0]
    new_id = max_id + 1 if max_id is not None else 1

    # Insert new submission with the new ID
    c.execute("""INSERT INTO responses (id, title, q1_problem, q2_behavior_change, q3_whose_behavior,
                 q4_beneficiary, q5_current_behavior, q6_desired_behavior, q7_frictions,
                 q7_explain, q8_address_problem, q9_patient_journey, q10_settings)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (new_id, 'New Submission', '', 'YES', '[]', '[]', '', '', '[]', '', '', '[]', '[]'))
    conn.commit()
    return new_id

def show_home():
    st.markdown("<h1 style='text-align: center;'>BEAR's North Star</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; font-style: italic;'>An opportunity map for behavioural interventions in healthcare.</h3>", unsafe_allow_html=True)
    
    # Add some vertical space
    st.write("")
    st.write("")
    
    # Create three columns, with the buttons in the middle column
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        # Create two columns within the middle column for the buttons
        button_col1, button_col2 = st.columns(2)
        
        with button_col1:
            if st.button("I have a behavioural problem", key="problem_button", use_container_width=True):
                st.session_state.page = 'problem'
                st.rerun()
        
        with button_col2:
            if st.button("I am a behavioural scientist", key="scientist_button", use_container_width=True):
                st.session_state.page = 'scientist'
                st.rerun()

def show_problem_survey():
    st.title("Have a Behavioural Problem?")
    
    with st.form("survey_form"):
        q1 = st.text_area("Q1. What problem from your healthcare setting do you want to tackle? (required)")
        
        q2 = st.radio("Q2. Will a change in behavior address this problem? (required)", 
                      ["Yes", "No"])
        
        q3 = st.multiselect("Q3. Whose behaviour should primarily be changed?", 
                            ["Administrative Staff", "Dietician", "Educator", "Media", 
                             "Nurse", "Nurse Practitioner", "Patient", "Pharmacist", 
                             "Physician", "Public Health", "Social Worker", "Student", "Other"])
        q3_elaborate = st.text_area("Elaborate on your answer to question 3:", key="q3_elaborate")
        
        q4 = st.multiselect("Q4. Who will the primary beneficiary of this behaviour change be?",
                            ["Administrative Staff", "Dietician", "Educator", "Media", 
                             "Nurse", "Nurse Practitioner", "Patient", "Pharmacist", 
                             "Physician", "Public Health", "Social Worker", "Student", "Other"])
        q4_elaborate = st.text_area("Elaborate on your answer to question 4:", key="q4_elaborate")
        
        q5 = st.text_area("Q5. CURRENT BEHAVIOUR: What are they currently doing?")
        
        q6 = st.text_area("Q6. DESIRED BEHAVIOUR: What should they be doing that might solve the problem?")
        
        q7 = st.multiselect("Q7. Why might they not be doing the desired behavior? What might the frictions be?",
                            ["Ambiguity: unclear guidance to users to adopt desired behaviour",
                             "Low motivation or awareness: don't know, understand or appreciate the values of desired behaviour",
                             "Systemic corporation: the desired behaviour involves some changes to upstream/downstream practice in the first place",
                             "Complexity: nuances or variations of implementing interventions in real life",
                             "Research lagging behind: Researchers and/or healthcare practitioners need further understanding",
                             "Tech/tools constraints: the desired behaviour change is restricted due to underequipped or inaccessible technology/device/tools",
                             "Other"])
        q7_elaborate = st.text_area("Elaborate on your answer to question 7:", key="q7_elaborate")
        
        q8 = st.text_area("Q8. How will the behaviour change address the problem?")
        
        q9 = st.multiselect("Q9. At which stage of the patient journey map does this problem arise?",
                            ["Stage 1: Prevention, Trigger Event",
                             "Stage 2: Initial Visit, Diagnosis",
                             "Stage 3: Treatment, Clinical Care",
                             "Stage 4: Follow-Up, Ongoing Care",
                             "Other"])
        q9_elaborate = st.text_area("Elaborate on your answer to question 9:", key="q9_elaborate")
        
        q10 = st.multiselect("Q10. Does this problem manifest itself in any of the following settings?",
                             ["Primary Care",
                              "Hospital Care",
                              "Home and Long-Term Care",
                              "Community Care",
                              "Other"])
        q10_elaborate = st.text_area("Elaborate on your answer to question 10:", key="q10_elaborate")
        
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            c.execute("""
                INSERT INTO responses (
                    q1_problem, q2_behavior_change, q3_whose_behavior, q4_beneficiary,
                    q5_current_behavior, q6_desired_behavior, q7_frictions, q7_explain,
                    q8_address_problem, q9_patient_journey, q10_settings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q1.upper(),
                q2.upper(),
                json.dumps([x.upper() for x in q3] + [f"Elaboration: {q3_elaborate.upper()}"]),
                json.dumps([x.upper() for x in q4] + [f"Elaboration: {q4_elaborate.upper()}"]),
                q5.upper(),
                q6.upper(),
                json.dumps([x.upper() for x in q7] + [f"Elaboration: {q7_elaborate.upper()}"]),
                q7_elaborate.upper(),  # This is the existing q7_explain field
                q8.upper(),
                json.dumps([x.upper() for x in q9] + [f"Elaboration: {q9_elaborate.upper()}"]),
                json.dumps([x.upper() for x in q10] + [f"Elaboration: {q10_elaborate.upper()}"])
            ))
            conn.commit()
            st.success("Survey submitted successfully!")

    if st.button("Back to Home", key="problem_back_survey_button"):
        st.session_state.page = 'home'
        st.rerun()

def safe_json_loads(x):
    try:
        return json.loads(x)
    except json.JSONDecodeError:
        return x  # Return the original string if it's not valid JSON
    except TypeError:
        return x  # Return the original value if it's not a string

def show_scientist_dashboard():
    st.title("Behavioural Scientist Dashboard")
    
    # Load data
    df = pd.read_sql_query("SELECT * FROM responses", conn)
    
    if df.empty:
        st.write("No responses yet.")
        return
    
    # Convert JSON strings back to lists, handling potential errors
    json_columns = ['q3_whose_behavior', 'q4_beneficiary', 'q7_frictions', 'q9_patient_journey', 'q10_settings']
    for col in json_columns:
        if col in df.columns:
            df[col] = df[col].apply(safe_json_loads)
    
    # Normalize responses by converting to uppercase
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: [item.upper() if isinstance(item, str) else item for item in x] if isinstance(x, list) else x.upper() if isinstance(x, str) else x)
    
    # Keyword filter
    keyword = st.text_input("Filter responses by keyword:")
    if keyword:
        keyword = keyword.upper()
    
    # Multiple choice filters
    st.subheader("Filter by Multiple Choice Questions")
    col1, col2 = st.columns(2)
    
    with col1:
        # Filter for q2_behavior_change
        behavior_change_options = ['ALL', 'YES', 'NO']
        selected_behavior_change = st.selectbox("Behavior Change", behavior_change_options)
        
        # Filter for q3_whose_behavior
        whose_behavior_options = ['ALL', 'ADMINISTRATIVE STAFF', 'DIETICIAN', 'EDUCATOR', 'MEDIA', 
                                  'NURSE', 'NURSE PRACTITIONER', 'PATIENT', 'PHARMACIST', 
                                  'PHYSICIAN', 'PUBLIC HEALTH', 'SOCIAL WORKER', 'STUDENT', 'OTHER']
        selected_whose_behavior = st.multiselect("Whose Behavior", whose_behavior_options)
        
        # Filter for q4_beneficiary
        beneficiary_options = ['ALL', 'ADMINISTRATIVE STAFF', 'DIETICIAN', 'EDUCATOR', 'MEDIA', 
                               'NURSE', 'NURSE PRACTITIONER', 'PATIENT', 'PHARMACIST', 
                               'PHYSICIAN', 'PUBLIC HEALTH', 'SOCIAL WORKER', 'STUDENT', 'OTHER']
        selected_beneficiary = st.multiselect("Beneficiary", beneficiary_options)
    
    with col2:
        # Filter for q7_frictions
        friction_options = ['ALL', 
                            "AMBIGUITY: UNCLEAR GUIDANCE TO USERS TO ADOPT DESIRED BEHAVIOUR",
                            "LOW MOTIVATION OR AWARENESS: DON'T KNOW, UNDERSTAND OR APPRECIATE THE VALUES OF DESIRED BEHAVIOUR",
                            "SYSTEMIC CORPORATION: THE DESIRED BEHAVIOUR INVOLVES SOME CHANGES TO UPSTREAM/DOWNSTREAM PRACTICE IN THE FIRST PLACE",
                            "COMPLEXITY: NUANCES OR VARIATIONS OF IMPLEMENTING INTERVENTIONS IN REAL LIFE",
                            "RESEARCH LAGGING BEHIND: RESEARCHERS AND/OR HEALTHCARE PRACTITIONERS NEED FURTHER UNDERSTANDING",
                            "TECH/TOOLS CONSTRAINTS: THE DESIRED BEHAVIOUR CHANGE IS RESTRICTED DUE TO UNDEREQUIPPED OR INACCESSIBLE TECHNOLOGY/DEVICE/TOOLS",
                            "OTHER"]
        selected_frictions = st.multiselect("Frictions", friction_options)
        
        # Filter for q9_patient_journey
        journey_options = ['ALL', 
                           "STAGE 1: PREVENTION, TRIGGER EVENT",
                           "STAGE 2: INITIAL VISIT, DIAGNOSIS",
                           "STAGE 3: TREATMENT, CLINICAL CARE",
                           "STAGE 4: FOLLOW-UP, ONGOING CARE",
                           "OTHER"]
        selected_journey = st.multiselect("Patient Journey Stage", journey_options)
        
        # Filter for q10_settings
        settings_options = ['ALL', 
                            "PRIMARY CARE",
                            "HOSPITAL CARE",
                            "HOME AND LONG-TERM CARE",
                            "COMMUNITY CARE",
                            "OTHER"]
        selected_settings = st.multiselect("Settings", settings_options)
    
    # Apply filters
    if keyword:
        df = df[df.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)]
    
    if selected_behavior_change and selected_behavior_change != 'ALL':
        df = df[df['q2_behavior_change'] == selected_behavior_change]

    def filter_multiselect(column, selected, options):
        if not selected or 'ALL' in selected:
            return pd.Series([True] * len(df))
        
        predefined_options = set(options[1:-1])  # Exclude 'ALL' and 'OTHER'
        
        def check_row(row):
            if isinstance(row, list):
                if 'OTHER' in selected:
                    return any(item not in predefined_options for item in row)
                return any(item in selected for item in row)
            elif isinstance(row, str):
                if 'OTHER' in selected:
                    return row not in predefined_options
                return row in selected
            return False
        
        return df[column].apply(check_row)

    if selected_whose_behavior:
        df = df[filter_multiselect('q3_whose_behavior', selected_whose_behavior, whose_behavior_options)]
    
    if selected_beneficiary:
        df = df[filter_multiselect('q4_beneficiary', selected_beneficiary, beneficiary_options)]
    
    if selected_frictions:
        df = df[filter_multiselect('q7_frictions', selected_frictions, friction_options)]
    
    if selected_journey:
        df = df[filter_multiselect('q9_patient_journey', selected_journey, journey_options)]
    
    if selected_settings:
        df = df[filter_multiselect('q10_settings', selected_settings, settings_options)]
    
    # Display results in a table format
    st.subheader("Filtered Responses:")
    
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
    response_numbers = st.text_input("Enter response numbers to download index cards in pdf (comma-separated, e.g., 1,3,5):")
    
    # Download selected responses
    if st.button("Submit Selected Responses"):
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
        
        st.markdown("---")
        st.title("Admin Access")
        if not st.session_state.logged_in:
            show_login()
        else:
            if st.button("Project Manager Dashboard"):
                st.session_state.page = 'project_manager'
                st.rerun()
            if st.button("Logout"):
                st.session_state.logged_in = False
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
        if row['title']:
            elements.append(Paragraph(f"<b>Title</b>", styles['SectionTitle']))
            elements.append(Paragraph(f"{row['title']}", styles['Entry']))
            elements.append(Spacer(1, 20))
        
        # Problem Statement Section
        problem_statements = []
        if row['q1_problem']:
            problem_statements.append(f"<b>{strip_question_number('q1_problem')}:</b> {row['q1_problem']}")
        if row['q9_patient_journey']:
            journey = ', '.join(safe_json_loads(row['q9_patient_journey']))
            problem_statements.append(f"<b>{strip_question_number('q9_patient_journey')}:</b> {journey}")
        if row['q10_settings']:
            settings = ', '.join(safe_json_loads(row['q10_settings']))
            problem_statements.append(f"<b>{strip_question_number('q10_settings')}:</b> {settings}")
        
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
            frictions = ', '.join(safe_json_loads(row['q7_frictions']))
            elements.append(Paragraph(f"<b>{strip_question_number('q7_frictions')}:</b> {frictions}", styles['Entry']))
            elements.append(Spacer(1, 20))
        
        # The Desired Outcome Section
        desired_outcomes = []
        if row['q8_address_problem']:
            desired_outcomes.append(f"<b>{strip_question_number('q8_address_problem')}:</b> {row['q8_address_problem']}")
        if row['q4_beneficiary']:
            beneficiary = ', '.join(safe_json_loads(row['q4_beneficiary']))
            desired_outcomes.append(f"<b>{strip_question_number('q4_beneficiary')}:</b> {beneficiary}")
        
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