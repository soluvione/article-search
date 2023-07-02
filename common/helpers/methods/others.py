import random
import string
from common.erorrs import GeneralError
from common.services.send_sms import send_notification
from fuzzywuzzy import fuzz

def generate_random_string(length):
    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def similarity(name, correspondence_name):
    """
    Function for calculating the similarity between two strings using fuzzywuzzy library
    :param name: String
    :param correspondence_name: String
    :return: Integer
    """
    try:
        return fuzz.ratio(name.lower(), correspondence_name.lower())
    except Exception as e:
        send_notification(GeneralError(f"Error encountered while calculating similarity between two strings ("
                                       f"similarity, others). Error encountered was: {e, type(e).__name__}"))
        return 0
