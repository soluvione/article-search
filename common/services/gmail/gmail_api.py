import datetime
import os
import pathlib

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    path_of_folder = os.path.dirname(os.path.abspath(__file__))

    if os.path.exists(pathlib.Path.joinpath(path_of_folder, 'token.json')):
        creds = Credentials.from_authorized_user_file(pathlib.Path.joinpath(path_of_folder, 'token.json'), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                pathlib.Path.joinpath(path_of_folder, 'credentials.json'), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(pathlib.Path.joinpath(path_of_folder, 'token.json'), 'w') as token:
            token.write(creds.to_json())

    # Build the Gmail API service
    return build('gmail', 'v1', credentials=creds)


def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    message_text = message_text.replace('\n', '<br>')
    msg = MIMEText(message_text, 'html')
    message.attach(msg)

    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


def send_message(service, user_id, message):
    """Send an email message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        message: Message to be sent.

    Returns:
        Sent Message.
    """
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        return message
    except Exception as error:
        with open('mail_errors.txt', 'a') as file:
            file.write(error.__str__() + '\n')


def send_mail(text_body):
    """Send email to the user notifying the error"""
    # Build a Gmail service
    service = get_service()
    unique_identifier = datetime.datetime.now().strftime("%Y%m%d%H%M%S")[4:]

    # Create an email message
    message = create_message("noreply@soluvione.com", "esoyvural@soluvione.com",
                             f"ARSER HATASI - {datetime.datetime.now().date()} [{unique_identifier}]", text_body)

    # Send the email
    send_message(service, "me", message)

if __name__ == "__main__":
    send_mail("Merhaba")