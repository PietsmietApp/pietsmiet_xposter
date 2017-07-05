from gcloud import storage
from oauth2client.service_account import ServiceAccountCredentials
import requests
import shutil
import os
from backend.api_keys import cloud_client_id,cloud_client_email,cloud_private_key_id,cloud_private_key,cloud_bucket_name

# Only upload images smaller than ~400kb
max_image_size = 400000

credentials_dict = {
    'type': 'service_account',
    'client_id': cloud_client_id,
    'client_email': cloud_client_email,
    'private_key_id': cloud_private_key_id,
    'private_key': cloud_private_key,
}
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict)
client = storage.Client(credentials=credentials, project=cloud_bucket_name)


def store_image_in_gcloud(url, storage_path):
    try:
        image = None
        # Get image with timeout
        r = requests.get(url, stream=True, timeout=10)
        if r.status_code == 200:
            # Check that the file is not bigger than max size
            content = r.raw.read(max_image_size+1, decode_content=True)
            if len(content) > max_image_size:
                raise ValueError('Too large a response')
            image = content
        else:
            raise ValueError("Wrong status code at download")
        if image is None:
            return None
                
        # Upload the image to the firebase storage
        bucket = client.get_bucket(cloud_bucket_name)
        blob = bucket.blob(storage_path)
        blob.upload_from_string(image, "image/jpeg")
        print("Uploaded image")
        del image
        del content
        # Return the download of the image
        return "https://storage.googleapis.com/" + cloud_bucket_name + "/" + storage_path
    except Exception as e:
        print("Failed to up- / download image because: " + format(e))
    return None
