import base64
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage


class GmailClient:
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    TOKEN_PATH = 'token.json'
    CREDENTIALS_PATH = 'credentials.json'

    def __init__(self):
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        if os.path.exists(self.TOKEN_PATH):
            self.creds = Credentials.from_authorized_user_file(
                filename=self.TOKEN_PATH, scopes=self.SCOPES
            )
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file=self.CREDENTIALS_PATH, scopes=self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            with open(self.TOKEN_PATH, "w") as token:
                token.write(self.creds.to_json())

        self.service = build(serviceName="gmail", version="v1", credentials=self.creds)

    def send_email(self, to_email, subject, content):
        try:
            message = EmailMessage()
            message.set_content(content)
            message["To"] = to_email
            message["Subject"] = subject

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            send_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            return send_message["id"]

        except HttpError as error:
            return f"An error occurred: {error}"


    def list_labels(self):
        try:
            labels = self.service.users().labels().list(userId="me").execute()
            labels_list = labels.get('labels', [])
            if not labels_list:
                print("No labels found.")
            else:
                print("Labels:")
                for label in labels_list:
                    print(f"- {label['name']} (ID: {label['id']})")
            return labels_list
        except HttpError as error:
            print(f"An error occurred while listing labels: {error}")
            return []

    def list_messages(self, label_id=None, query=None, max_results=10):
        try:
            messages = []
            # If a label is provided, use it to filter the messages
            if label_id:
                results = self.service.users().messages().list(userId="me", labelIds=[label_id], q=query, maxResults=max_results).execute()
            else:
                results = self.service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()

            if "messages" in results:
                messages.extend(results["messages"])
            
            if not messages:
                print("No messages found.")
            else:
                print(f"Found {len(messages)} message(s).")
            
            return messages
        
        except HttpError as error:
            print(f"An error occurred while listing messages: {error}")
            return []

    def get_message(self, message_id):
        try:
            message = self.service.users().messages().get(userId="me", id=message_id).execute()
            print(f"Message snippet: {message['snippet']}")
            return message
        except HttpError as error:
            print(f"An error occurred while getting the message: {error}")
            return None