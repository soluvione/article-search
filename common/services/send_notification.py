"""
This module will be used to send a mail to the user in case of an error
There is a need to implement a wait time to ensure the notification is indeed sent to the user.
May halt the code execution for a limited time, eg: 10 seconds.
"""
import sys
from ...common.errors import GeneralError
from ...common.services.gmail.gmail_api import send_mail
sys.path.append("/home/ubuntu/article-search")


def send_notification(error, is_real=True):
    """

    :param is_real: bool - Will the function work on test mode or production mode?
    :param error: An error object, could be unique errors or generic errors
    :return: Does not return anything
    """
    # Do stuff depending on the error type here.
    if is_real:
        send_mail(error.message)
    else:
        print("sent message is: ", error.message)


def send_notifications(message: str):
    """

    :param message: Message to be send to the supervisor.
    :return: Does not return anything.
    """
    pass


if __name__ == "__main__":
    send_notification(GeneralError("Hello!"))
