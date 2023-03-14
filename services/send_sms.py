"""This module will be used to send the message to user in any way in the future."""
import errno


def send_sms(error: BaseException):
    # Do stuff depending on the error type here.
    print("sent message is: ", error.args)
    print("Sent the sms")
