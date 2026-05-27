import os
import requests
import mimetypes
from core.config import settings

class SupabaseStorageClient:
    def __init__(self):
        self.url = settings.SUPABASE_URL.rstrip('/') if settings.SUPABASE_URL else None
        self.key = settings.SUPABASE_KEY
        
        # Log a warning if the key or url is missing
        if not self.url or not self.key:
            print("WARNING: SUPABASE_URL or SUPABASE_KEY is empty. Supabase Storage integration will fail until configured.")

    def get_headers(self, content_type: str = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.key}"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def init_buckets(self):
        """
        Initialize the required buckets: screening_docs and scoring_docs.
        If they already exist, this method handles the conflict gracefully.
        """
        if not self.key or not self.url:
            print("Skipping bucket initialization: SUPABASE_KEY or SUPABASE_URL is not set.")
            return

        buckets = ["screening_docs", "scoring_docs"]
        for bucket in buckets:
            url = f"{self.url}/storage/v1/bucket"
            data = {
                "id": bucket,
                "name": bucket,
                "public": False  # Keep documents secure (private bucket)
            }
            try:
                response = requests.post(url, headers=self.get_headers("application/json"), json=data)
                if response.status_code == 200:
                    print(f"Bucket '{bucket}' initialized successfully.")
                elif response.status_code in [400, 409]:
                    # Usually means bucket already exists
                    print(f"Bucket '{bucket}' already exists or is already initialized.")
                else:
                    print(f"Failed to initialize bucket '{bucket}': {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error initializing bucket '{bucket}': {e}")

    def upload_file(self, bucket: str, local_file_path: str, destination_name: str) -> str:
        """
        Uploads a local file to the specified Supabase Storage bucket.
        Returns the object name/path if successful, otherwise raises Exception.
        """
        if not self.key or not self.url:
            raise Exception("Cannot upload: SUPABASE_KEY or SUPABASE_URL is not configured.")

        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file not found: {local_file_path}")

        # Guess mime type
        mime_type, _ = mimetypes.guess_type(local_file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        import urllib.parse
        quoted_name = urllib.parse.quote(destination_name)
        # Format URL: /storage/v1/object/bucket/name
        url = f"{self.url}/storage/v1/object/{bucket}/{quoted_name}"
        
        try:
            with open(local_file_path, "rb") as f:
                response = requests.post(url, headers=self.get_headers(mime_type), data=f)
            
            if response.status_code == 200:
                print(f"Uploaded '{destination_name}' to bucket '{bucket}'.")
                return destination_name
            else:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error uploading to Supabase Storage: {e}")
            raise e

    def download_file(self, bucket: str, filename: str) -> bytes:
        """
        Downloads a file from Supabase Storage and returns its bytes.
        """
        if not self.key or not self.url:
            raise Exception("Cannot download: SUPABASE_KEY or SUPABASE_URL is not configured.")

        import urllib.parse
        quoted_filename = urllib.parse.quote(filename)
        url = f"{self.url}/storage/v1/object/authenticated/{bucket}/{quoted_filename}"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"Download failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error downloading from Supabase Storage: {e}")
            raise e

# Global singleton client instance
storage_client = SupabaseStorageClient()
