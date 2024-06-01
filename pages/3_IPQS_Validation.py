import streamlit as st
import pandas as pd
import json
import requests
import os
from pathlib import Path
import time
import gspread
from google.oauth2 import service_account
from datetime import datetime  # Import datetime module correctly
import base64

st.set_page_config(
    page_title="IPQS Validation",
    page_icon="ipqs.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

# Using "with" notation
#with st.sidebar:           
#    st.markdown("### 1. Person Source")
#    st.markdown(
#        """
#        - ContentSyndication
#        - CRM
#        - GatedContent
#        - InPersonEvent
#        - PaidLinkedIn
#        - PreferenceCenterForm
#        - VirtualEvent
#        - ZoomInfo
#        - Other
#        """
#    )

# Define the login page
def login_page():
    st.title("Login Page")
    account_name = st.text_input("Enter your account name")
    if st.button("Enter") and account_name:
        st.session_state.account_name = account_name.upper()
        st.rerun()

# Define the main content
def main_content():
    #st.write(f"Welcome to the main content, {st.session_state.account_name}!")

    # Retrieve the API key from the environment
    api_key = os.getenv('IPQS_API_KEY')
    google_json = os.getenv('GOOGLE_JSON')

    if api_key is None:
        raise ValueError("API key not found in the environment.")

    class Validate(object):
        key = None
        format = None
        base_url = None

        def __init__(self, key, format="json") -> None:
            self.key = key
            self.format = format
            self.base_url = f"https://www.ipqualityscore.com/api/{self.format}/"

        def upload_csv(self, file_name: str, input_data: list) -> dict:
                url = f"{self.base_url}csv/upload"
                headers = {
                    "Content-Type": "application/json"
                }
                data = {
                    "type": "email",
                    "file_name": file_name,
                    "key": self.key,
                    "input": input_data
                }
                response = requests.post(url, headers=headers, json=data)
                return response.json()

        def check_status(self, csv_id: str) -> dict:
            url = f"{self.base_url}csv/{self.key}/status/{csv_id}"
            response = requests.get(url)
            return response.json()
        
        def get_list(self) -> dict:
            url = f"{self.base_url}csv/{self.key}/list"
            response = requests.get(url)
            return response.json()
    
    if __name__ == "__main__":

        # Initialize the Validate class with your API key
        v = Validate(api_key)

        # Helper function for caching the upload_csv method without 'self'
        @st.cache_data
        def cached_upload_csv(file_name: str, input_data: list) -> dict:
            return v.upload_csv(file_name, input_data)

    # Define a function to set all checkbox states to True
    def set_initial_state():
        state.csv_id = None
        st.session_state["ipqs_toggle"] = False
        st.session_state["ipqs_run"] = False

    title_container = st.container()
    col1, col2 = st.columns([1, 25])
    with title_container:
        with col1:
            st.image('ipqs.png', width=64)
        with col2:
            st.markdown('<h1 style="color: black;">IPQS Validation</h1>',
                        unsafe_allow_html=True)
    st.markdown("###")

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0
        
    with st.container(border=True):
        # Add a text input for the company name
        account_name = st.session_state.account_name
        uploaded_file = st.file_uploader("Upload a file with email column:", type=['csv', 'xlsx'], key=st.session_state["file_uploader_key"], accept_multiple_files=False)

   # Initialize session state if not already done
    if 'csv_data' not in st.session_state:
        st.session_state.csv_data = []

    # Define a function to fetch CSV data if it's not already in session state
    def fetch_csv_data(account_name):
        response = v.get_list()

        # Collect relevant CSV information
        csv_data = []
        csv_df = {}
        for csv in response['csvs']:
            if csv['file_name'].lower().startswith(account_name.lower()):
                status_url = csv['status_url']
                csv_id = status_url.split('/status/')[-1]
                status = csv['status']
                status_response = v.check_status(csv_id)

                download_link = None
                if status == "FINISHED":
                    downloads = status_response.get("downloads")
                    if downloads and downloads.get("all"):
                        download_link = downloads['all']
                        csv_df[csv_id] = pd.read_csv(download_link)

                csv_data.append({
                    "CSV ID": csv_id,
                    "File Name": csv['file_name'],
                    "Status": status
                })

        return csv_data, csv_df

    # Check if user has entered an account name
    if account_name:
        # Fetch CSV data only if it's not already in session state
        if not st.session_state.csv_data:
            st.session_state.csv_data, st.session_state.csv_df = fetch_csv_data(account_name)

        # Display CSV data in a table
        if st.session_state.csv_data and st.session_state.csv_df:
            st.dataframe(st.session_state.csv_data, column_config={
                "CSV ID": st.column_config.TextColumn(width="medium"),
                "File Name": st.column_config.TextColumn(width="large"),
                "Status": st.column_config.TextColumn(width="medium")
            })

            st.write(st.session_state.csv_df.keys())
            # output dict_keys(['994454', '991895', '989960', '985196'])

                # Generate download links for each CSV file
            for csv_info in st.session_state.csv_data:
                csv_id = csv_info["CSV ID"]
                if csv_id in st.session_state.csv_df:
                    csv_df = st.session_state.csv_df[csv_id]
                    csv_file = csv_df.to_csv(index=False)
                    b64 = base64.b64encode(csv_file.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="{csv_id}.csv">Download CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)

        else:
            st.warning(f"No CSVs found with {account_name} prefix.")

    # Get the session state
    state = st.session_state

    if 'key' not in st.session_state:
        state.key = 0

    if 'button_clicked' not in state:
        state.button_clicked = False

    if 'run_button' in state and state.run_button == True:
        state.running = True
    else:
        state.running = False

    if 'ipqs_button_clicked' not in state:
        state.ipqs_button_clicked = False

    if 'ipqs_run_button' not in state:
        state.ipqs_disabled = False

    if "csv_id" not in st.session_state:
        state.csv_id = None

    if 'submit_button_clicked' not in state:
        state.submit_button_clicked = False

    if not uploaded_file:
        state.button_clicked = False

    # Initialize session_state variables if not already initialized
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None

    # Check if the file is uploaded
    if state.uploaded_file is not None and uploaded_file is not None:
        # Check if the uploaded file has changed
        if state.uploaded_file != uploaded_file.name:
            state.button_clicked = False  # Set button_clicked to False if file changed

    email_column = ''

    if uploaded_file and account_name != "":

        state.uploaded_file = uploaded_file.name

        file_extension = uploaded_file.name.split('.')[-1]  # Get the file extension
        filename = uploaded_file.name.rsplit('.', 1)[0]
        filename = f"{account_name}_{filename}"

        st.write(filename)

        def load_file():
            def get_email_column(columns):
                for col in ['Work Email', 'Email', 'Email Address']:
                    if col in columns:
                        return col
                return None

            if file_extension.lower() == 'csv':
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)
                df.columns = [str(col).strip() for col in df.columns]
                email_column = get_email_column(df.columns)
                return df, df.copy(), email_column

            df = pd.read_excel(uploaded_file, skiprows=1)
            df.columns = [str(col).strip() for col in df.columns]
            email_column = get_email_column(df.columns)

            if not email_column:
                df = pd.read_excel(uploaded_file)
                df.columns = [str(col).strip() for col in df.columns]
                email_column = get_email_column(df.columns)
                if not email_column:
                    st.warning("Please check that the uploaded file is correct. The file must have an email column to proceed.")

            return df, df.copy(), email_column
        
        # Call the load_file function to get the DataFrames
        df, df1, email_column = load_file()

        # Drop rows with all NaN values from df and df1
        df.dropna(how='all', inplace=True)
        df1.dropna(how='all', inplace=True)

        # Adjust the index to start from 1
        df.index += 1

        if email_column: 
            # Initialize an empty list to store duplicate values
            duplicate_values = []

            # Define a function to highlight duplicate rows and store duplicate values
            def highlight_duplicates(row):
                # Check if the email in the current row is duplicated in the DataFrame
                email = row[email_column]
                is_duplicate = df[email_column].duplicated(keep=False) & (df[email_column] == email)
                
                # If it's a duplicate, store its values in a list
                if is_duplicate.any():
                    duplicate_values.append(email)

                # Return the background color for the email column based on whether it's a duplicate or not
                return ['background-color: #FFC7CE' if (col == email_column and is_duplicate.any()) else '' for col in row.index]

            # Apply the custom style function to the DataFrame
            styled_df = df.style.apply(highlight_duplicates, axis=1)

            # Set custom table styles for autofitting the table to the data
            table_styles = [
                dict(selector="table", props=[("width", "100%"), ("table-layout", "auto")]),
                dict(selector="th, td", props=[("white-space", "nowrap"), ("overflow", "hidden"), ("text-overflow", "ellipsis")])
            ]
            
            # Apply custom table styles to the styled DataFrame
            styled_df = styled_df.set_table_styles(table_styles)

            # Render the styled DataFrame with custom styling
            st.markdown('###')
            st.subheader("Raw Data Preview", divider='grey')
            st.write("Total Contacts: ", len(df.index))
            st.dataframe(styled_df, use_container_width=True)

            def resetbutton():
                state.button_clicked = False

            # Show running status
            if st.button('Process', disabled=state.running, key='run_button'):
                st.cache_data.clear()
                st.write("Checking in progress...")  # Display a message indicating that the process is running
                state.button_clicked = True
                st.session_state.key += 1
                status = st.progress(0)
                for t in range(10):
                    time.sleep(.2)
                    status.progress(10 * t + 10)
                set_initial_state()
                st.rerun()
    

    # Perform the checks only if the process button is clicked
    if uploaded_file and email_column and state.button_clicked:

        if duplicate_values:

            with st.container(border=True):
                st.markdown("##### Email Address Duplication")

                duplicate_emails = []

                for index, row in df.iterrows():
                    email = str(row[email_column]).strip()  # Convert to string to handle float values
                    if email in duplicate_values:
                        duplicate_emails.append((index, email))
            
                # Convert the list of tuples to a DataFrame
                df_duplicate_indices = pd.DataFrame(duplicate_emails, columns=['Index', 'Duplicate Email Address'])
                st.warning(f"Total {len(duplicate_emails)} duplicate email addresses found.")

                st.dataframe(df_duplicate_indices, hide_index=True)

        with st.container(border=False):
            # N. Email Validation
            st.markdown("##")
            # st.markdown("##### Email Validation")
            st.write("Select the required validations: ")

            with st.container(border=True):
                ipqs = st.toggle('IPQS Validation', disabled=state.ipqs_disabled, key=f"ipqs_toggle")

                if ipqs:

                    st.info("📥 Are you sure to proceed?")
                    st.write('⚠️ Please note:')
                    st.markdown(
                        '''
                        1. Only unique email addresses will be checked during this validation. (Duplicate emails have been removed to avoid multiple checks)
                        2. Each email address validation will consume one credit under the 2X IPQS account.
                        3. Expect a longer processing time if there are many email addresses to validate.
                        4. Please ensure that the file you are working on is correct before proceeding.
                        '''
                    )

                    def ipqs_disable():
                        #st.cache_data.clear()
                        state.ipqs_disabled = True

                    @st.cache_data(experimental_allow_widgets=True)
                    def ipqs_validation():

                        # Function to update progress and status
                        def update_progress(status_message, progress_percent):
                            my_bar.progress(progress_percent, text=status_message)

                        def log_entry_to_google_sheets(timestamp, request_id, filename, csv_id, upload_success, upload_message, status_success, status, status_message):
                            
                            service_account_info = json.loads(google_json)

                            # Create credentials object from service account credentials json
                            credentials = service_account.Credentials.from_service_account_info(service_account_info)

                            # Assign API scope to credentials
                            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                            creds_with_scope = credentials.with_scopes(scope)

                            # Create a new client with scoped credentials
                            client = gspread.authorize(creds_with_scope)

                            # Read spreadsheets data into a DataFrame
                            spreadsheet = client.open_by_url('https://docs.google.com/spreadsheets/d/11CZgEFDvJP7RzlD736WWiOaky7_VL1r3omX2lihNYAw/edit#gid=0')

                            # Get the first worksheet using index 0
                            worksheet = spreadsheet.get_worksheet(0)

                            # Log the entry
                            log_entry = [timestamp, request_id, filename, csv_id, upload_success, upload_message, status_success, status, status_message]
                            worksheet.append_row(log_entry)

                        filename = uploaded_file.name.rsplit('.', 1)[0]
                        filename = f"{account_name}_{filename}"

                        filtered_df = df1.dropna(subset=[email_column])
                        filtered_df[email_column] = filtered_df[email_column].str.strip()
                        filtered_df = filtered_df.drop_duplicates(subset=[email_column])

                        # Define status messages and progress percentages
                        progress = {
                            "NEW": ("CSV is waiting to begin processing.", 0),
                            "PROCESSING": ("CSV is currently processing through records.", 50),
                            "UNIQUE_RESULTS": ("CSV is currently being uniqued to remove duplicate records.", 70),
                            "FINALIZING": ("CSV is currently undergoing final checks before processing completes.", 80),
                            "FINISHED": ("CSV processing is finished.", 100),
                            "ERROR": ("CSV processing encountered an error. Please check again later.", 0)
                        }

                        # Initialize progress bar
                        progress_text = "Operation in progress. Please wait."
                        my_bar = st.progress(0, text=progress_text)

                        # Step 1: Upload CSV
                        csv_upload_response = cached_upload_csv(f"{filename}.csv", filtered_df[[email_column]].values.tolist())

                        if csv_upload_response["success"]:
                            csv_id = csv_upload_response["id"]
                            state.csv_id = csv_upload_response["id"]

                            # Continuously check status until processing is finished
                            while True:
                                status_response = v.check_status(csv_id)
                                status = status_response.get("status")

                                status_message, progress_percent = progress.get(status, ("Unknown status", 0))
                                update_progress(status_message, progress_percent)
                                # Log entry to Google Sheets
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                                if status == "FINISHED":
                                    st.success("CSV processing is finished.")
                                    downloads = status_response.get("downloads")
                                    if downloads and downloads.get("all"):
                                        download_link = downloads["all"]
                                        log_entry_to_google_sheets(timestamp, csv_upload_response["request_id"], filename , csv_id, csv_upload_response["success"], csv_upload_response["message"], status_response["success"], status_response["status"], status_response["message"])
                                    else:
                                        st.warning("No download link available yet. Please check again later.")
                                        log_entry_to_google_sheets(timestamp, csv_upload_response["request_id"], filename , csv_id, csv_upload_response["success"], csv_upload_response["message"], status_response["success"], status_response["status"], status_response["message"])
                                
                                    time.sleep(1)  # Wait for 1 second before clearing the progress bar
                                    my_bar.empty()  # Clear the progress bar

                                    break  # Exit the loop once processing is finished
                                elif status == "ERROR":
                                    st.error("CSV processing encountered an error. Please check again later.")
                                    log_entry_to_google_sheets(timestamp, csv_upload_response["request_id"], filename , csv_id, csv_upload_response["success"], csv_upload_response["message"], status_response["success"], status_response["status"], status_response["message"])
                                    break  # Exit the loop if an error occurs
                        else:
                            st.error("CSV upload failed.")
                            st.error(f"Error message: {csv_upload_response['message']}")
                            log_entry_to_google_sheets(timestamp, csv_upload_response["request_id"], filename , "", csv_upload_response["success"], csv_upload_response["message"], "", "", "")
                    
                        if download_link:
                            st.subheader("IPQS Validation Result", divider="grey")
                            # Load the CSV data into a DataFrame
                            ipqs_validation_df = pd.read_csv(download_link)

                            # Save the styled DataFrame to a temporary Excel file
                            temp_file_path = os.path.join(os.getcwd(), "temp.xlsx")
                            ipqs_validation_df.to_excel(temp_file_path, index=False, engine='openpyxl')
                            # Read the temporary file as bytes
                            with open(temp_file_path, "rb") as file:
                                excel_data = file.read()
                            # Remove the temporary file
                            os.remove(temp_file_path)

                            # Get today's date
                            today_date = datetime.today().strftime("[%Y%m%d_Cleansed]")

                            filename = f"[IPQS] {today_date}_{filename}.xlsx"

                            # Check conditions and create a new column
                            ipqs_validation_df["IPQS Validation"] = ipqs_validation_df.apply(
                                lambda row: "Valid" if (row["Recent Abuse"] == False and
                                                        row["Valid"] == True and
                                                        row["Disposable"] == False and
                                                        row["Honeypot"] == False and
                                                        row["Spam Trap Score"] == "none") else "Invalid",
                                axis=1
                            )

                            # Display specific columns along with the new "Validation Status" column
                            columns_to_display = ["Date", "Email Address", "Recent Abuse", "Valid", "Disposable", "Honeypot", "Spam Trap Score", "IPQS Validation"]
                            st.dataframe(ipqs_validation_df[columns_to_display])

                            # Create a download button using Streamlit
                            st.download_button(label="📄 Download IPQS Result", data=excel_data, file_name=filename, mime="application/octet-stream")

                            return ipqs_validation_df

                    if st.button("Yes, I want to proceed", disabled=state.ipqs_disabled, key='ipqs_run_button', on_click=ipqs_disable):
                        state.ipqs_button_clicked = True
                        st.write("IPQS running in progress...")  # Display a message indicating that the process is running
                        status = st.progress(0)
                        for t in range(10):
                            time.sleep(.2)
                            status.progress(10 * t + 10)
                        st.rerun()

                    if state.ipqs_button_clicked:
                        ipqs_validation_df = ipqs_validation()      

                        # Create a dictionary for faster lookup of validation info
                        validation_dict = dict(zip(ipqs_validation_df["Email Address"], ipqs_validation_df["IPQS Validation"]))

                        # Iterate through df and update the "IPQS Validation" column based on the dictionary
                        for index, row in df.iterrows():
                            email = row[email_column]
                            if email in validation_dict:
                                df.at[index, 'IPQS Validation'] = validation_dict[email]   

                        st.markdown("###")
                        st.subheader("Source File", divider="grey")
                        st.caption("IPQS Validation column has been added to the dataframe below.")
                        st.dataframe(df)

                        # Save the styled DataFrame to a temporary Excel file
                        temp_file_path = os.path.join(os.getcwd(), "temp.xlsx")
                        df.to_excel(temp_file_path, index=False, engine='openpyxl')
                        # Read the temporary file as bytes
                        with open(temp_file_path, "rb") as file:
                            excel_data = file.read()
                        # Remove the temporary file
                        os.remove(temp_file_path)

                        # Get today's date
                        today_date = datetime.today().strftime("[%Y%m%d_IPQS]")

                        filename = f"{today_date} {filename}.xlsx"

                        # Create a download button using Streamlit
                        st.download_button(label="📄 Download List with IPQS", data=excel_data, file_name=filename, mime="application/octet-stream")  
                        
                else:
                    state.ipqs_button_clicked = False

# Check if user is logged in
if 'account_name' not in st.session_state:
    login_page()
else:
    main_content()

