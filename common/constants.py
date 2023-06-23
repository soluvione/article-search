# Hidden variables
__endpoint = "https://article-search-recognizer-endpoint.cognitiveservices.azure.com/"
__form_recognizer_model_ID = "AllDataExtractor2_v02"  # This is the model ID
__tk_form_recognizer_model_ID = "TK_Extractor_V01"  # This is the model ID

# Twilio
account_sid = 'AC06727c5dbae8364b9b6bdcb296b91c53'
auth_token = 'ed9a7d7a8377541a23cdf9df260e8385'

# Azure Public
subscription_key = "5255bbd274a341a1b8f1bf85c8f3f999"  # Endpoint KEY 1
azure_analyse_pdf_url = f"{__endpoint}formrecognizer/documentModels/{__form_recognizer_model_ID}:analyze"
azure_tk_analyse_pdf_url = f"{__endpoint}formrecognizer/documentModels/{__tk_form_recognizer_model_ID}:analyze"
