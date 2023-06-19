"""
This module will be used to send a message or a notification to the user in any way in the future
There is a need to implement a wait time to ensure the notification is indeed sent to the user.
May halt the code execution for a limited time, eg: 10 seconds.
"""
from common.erorrs import GeneralError
from common.constants import account_sid, auth_token
import json
def send_notification(error, real=False):
    """

    :param error: An error object, could be unique errors or generic errors
    :return: Does not return anything
    """
    # Do stuff depending on the error type here.
    if real:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            from_='whatsapp:+14155238886',
            body=error.message,
            to='whatsapp:+905074997463'
        )
    print("sent message is: ", error.message)


def send_example_log(data):
    try:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=json.dumps(data, ensure_ascii=False, indent=4),
            from_='whatsapp:+14155238886',
            to='whatsapp:+905074997463'
        )
        print(message.error_message)
    except Exception as e:
        print(e)

def send_notifications(message: str):
    """

    :param message: Message to be send to the supervisor.
    :return: Does not return anything.
    """
    pass
from twilio.rest import Client



if __name__ == "__main__":
    send_example_log({'dict': 'value', 'key2':'value2', 'key3': "t is a long established fact that a reader will be distracted by the readable content of a page when looking at its layout. The point of using Lorem Ipsum is that it has a more-or-less normal distribution of letters, as opposed to using 'Content here, content here', making it look like readable English. Many desktop publishing packages and web page editors now use Lorem Ipsum as their default model text, and a search for 'lorem ipsum' will uncover many web sites still in their infancy. Various versions have evolved over the years, sometimes by accident, sometimes on purpose (injected humour and the like)."})