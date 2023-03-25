"""
This module will be used to send a message or a notification to the user in any way in the future
There is a need to implement a wait time to ensure the notification is indeed sent to the user.
May halt the code execution for a limited time, eg: 10 seconds.
"""


def send_notification(error: BaseException):
    """

    :param error: An error object, could be unique errors or generic errors
    :return: Does not return anything
    """
    # Do stuff depending on the error type here.
    print("sent message is: ", error.args)
    print("Sent the sms")


def send_notification(message: str):
    """

    :param message: Message to be send to the supervisor.
    :return: Does not return anything.
    """
    pass
