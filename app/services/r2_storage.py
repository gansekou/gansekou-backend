"""
Cloudflare R2 Storage Service
GANSEKOU Backend

Gestion centralisée :
- Upload fichiers
- Suppression
- Lecture
- URLs publiques
- URLs signées

Compatible :
FastAPI + Railway + Cloudflare R2
"""

import uuid
import mimetypes
from pathlib import Path
from datetime import datetime

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class R2StorageService:
    """
    Service de stockage Cloudflare R2
    """

    def __init__(self):

        if not all(
            [
                settings.R2_ACCOUNT_ID,
                settings.R2_BUCKET_NAME,
                settings.R2_ACCESS_KEY_ID,
                settings.R2_SECRET_ACCESS_KEY,
                settings.R2_ENDPOINT,
            ]
        ):
            raise RuntimeError(
                "Configuration Cloudflare R2 incomplète"
            )

        self.bucket = settings.R2_BUCKET_NAME

        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(
                signature_version="s3v4"
            ),
            region_name="auto",
        )


    def generate_filename(
        self,
        original_filename: str,
        folder: str = "uploads"
    ) -> str:
        """
        Génère un nom unique pour éviter les collisions

        Exemple:

        uploads/cours/2026/abc123.pdf
        """

        extension = Path(
            original_filename
        ).suffix.lower()


        date_path = datetime.utcnow().strftime(
            "%Y/%m"
        )


        filename = (
            f"{folder}/"
            f"{date_path}/"
            f"{uuid.uuid4().hex}"
            f"{extension}"
        )


        return filename



    async def upload_file(
        self,
        file,
        folder: str = "uploads"
    ):
        """
        Upload un fichier FastAPI UploadFile vers R2

        Retourne :

        {
            key,
            url,
            filename,
            content_type
        }

        """

        key = self.generate_filename(
            file.filename,
            folder
        )


        content_type = (
            file.content_type
            or mimetypes.guess_type(
                file.filename
            )[0]
            or "application/octet-stream"
        )


        try:

            self.client.upload_fileobj(
                file.file,
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type
                }
            )


        except Exception as e:

            raise RuntimeError(
                f"Erreur upload R2 : {str(e)}"
            )


        return {

            "key": key,

            "url": self.public_url(key),

            "filename": file.filename,

            "content_type": content_type
        }




    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        content_type: str = None,
        folder: str = "uploads"
    ):

        """
        Upload fichier depuis bytes
        utile pour thumbnails
        """

        key = self.generate_filename(
            filename,
            folder
        )


        if not content_type:
            content_type = (
                mimetypes.guess_type(
                    filename
                )[0]
                or "application/octet-stream"
            )


        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type
        )


        return {
            "key": key,
            "url": self.public_url(key)
        }



    def delete_file(
        self,
        key: str
    ):

        """
        Supprime un fichier R2
        """

        try:

            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )

            return True


        except ClientError:

            return False




    def exists(
        self,
        key: str
    ) -> bool:

        """
        Vérifie si fichier existe
        """

        try:

            self.client.head_object(
                Bucket=self.bucket,
                Key=key
            )

            return True


        except ClientError:

            return False




    def download_file(
        self,
        key: str,
        range_start=None,
        range_end=None,
    ):
        """
        Lecture streaming depuis Cloudflare R2
    
        Supporte :
        - gros fichiers
        - vidéos
        - audio
        - HTTP Range
        """
    
        params = {
            "Bucket": self.bucket,
            "Key": key,
        }
    
    
        if range_start is not None:
    
            if range_end is not None:
    
                params["Range"] = (
                    f"bytes={range_start}-{range_end}"
                )
    
            else:
    
                params["Range"] = (
                    f"bytes={range_start}-"
                )
    
    
        try:
    
            return self.client.get_object(
                **params
            )
    
    
        except ClientError as e:
    
            raise RuntimeError(
                f"Erreur lecture R2 : {str(e)}"
            )




    def generate_signed_url(
        self,
        key: str,
        expires: int = 3600
    ):

        """
        URL temporaire sécurisée

        durée par défaut :
        1 heure
        """

        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key
            },
            ExpiresIn=expires
        )



    def public_url(
        self,
        key: str
    ):

        """
        URL publique R2

        Pour utiliser un domaine custom plus tard,
        on changera seulement cette fonction.
        """

        return (
            f"{settings.R2_ENDPOINT}/"
            f"{self.bucket}/"
            f"{key}"
        )



# Instance globale utilisable partout

r2_storage = R2StorageService()
