import os
import uuid
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings
import requests

# Load configuration from environment
translator_key = os.environ["TRANSLATOR_KEY"]
translator_endpoint = os.environ["TRANSLATOR_ENDPOINT"]
storage_account = os.environ["STORAGE_ACCOUNT_NAME"]
storage_key = os.environ["STORAGE_ACCOUNT_KEY"]

# Initialize blob service
blob_service = BlobServiceClient(
    account_url=f"https://{storage_account}.blob.core.windows.net",
    credential=storage_key
)

def translate_text(text, from_lang="en", to_lang="fr"):
    url = f"{translator_endpoint}/translate?api-version=3.0&from={from_lang}&to={to_lang}"
    headers = {
        "Ocp-Apim-Subscription-Key": translator_key,
        "Ocp-Apim-Subscription-Region": "eastus",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=[{"text": text}])
    response.raise_for_status()
    return response.json()[0]["translations"][0]["text"]

def upload_blob(container, blob_name, content, content_type="text/plain"):
    blob_client = blob_service.get_blob_client(container, blob_name)
    blob_client.upload_blob(content, overwrite=True, content_settings=ContentSettings(content_type=content_type))
    return blob_client.url

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        form = req.files
        uploaded_file = form.get("file")

        if uploaded_file is None:
            return func.HttpResponse("No file uploaded", status_code=400)

        from_lang = req.params.get("from", "en")
        to_lang = req.params.get("to", "fr")

        file_text = uploaded_file.read().decode("utf-8")
        file_id = str(uuid.uuid4())

        # Upload original file
        request_blob_name = f"{file_id}.txt"
        upload_blob("requests", request_blob_name, file_text)

        # Translate the text
        translated_text = translate_text(file_text, from_lang, to_lang)

        # Upload translated file
        response_blob_name = f"{file_id}-translated.txt"
        translated_url = upload_blob("responses", response_blob_name, translated_text)

        # Return download link
        return func.HttpResponse(f"Translated file: {translated_url}", status_code=200)

    except Exception as e:
        logging.exception("Translation failed")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
