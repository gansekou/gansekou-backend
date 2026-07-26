import mimetypes
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    Query,
    Request,
)

from fastapi.responses import (
    StreamingResponse,
)

from sqlalchemy.orm import Session

from jose import jwt
from datetime import datetime, timedelta


from app.database.session import get_db

from app.core.config import settings
from app.core.security import (
    get_current_user,
    require_roles,
)

from app.core.premium import (
    require_premium_access
)

from app.models.content import Content
from app.models.user import User

from app.services.r2_storage import (
    r2_storage
)


router = APIRouter()



# ======================================================
# ROLES
# ======================================================


CONTENT_ROLES = [
    "ADMIN",
    "PROMOTEUR",
    "ADMINISTRATEUR",
    "ENSEIGNANT",
    "ENSEIGNANT_EN_ATTENTE",
]


ANSWER_ATTACHMENT_ROLES = [
    "ADMIN",
    "PROMOTEUR",
    "ADMINISTRATEUR",
    "ENSEIGNANT",
]



# ======================================================
# LIMITES FICHIERS
# ======================================================


MAX_IMAGE_SIZE = 5 * 1024 * 1024

MAX_PDF_SIZE = 25 * 1024 * 1024

MAX_AUDIO_SIZE = 50 * 1024 * 1024

MAX_VIDEO_SIZE = 200 * 1024 * 1024

MAX_DOCUMENT_SIZE = 30 * 1024 * 1024



# ======================================================
# EXTENSIONS AUTORISEES
# ======================================================


IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}


PDF_EXTENSIONS = {
    "pdf"
}


AUDIO_EXTENSIONS = {
    "mp3",
    "wav",
    "m4a",
    "aac",
    "ogg",
}


VIDEO_EXTENSIONS = {
    "mp4",
    "mov",
    "webm",
    "mkv",
}


DOCUMENT_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "ppt",
    "pptx",
    "xls",
    "xlsx",
}



# ======================================================
# MIME
# ======================================================


ALLOWED_MIME_PREFIXES = {

    "image": [
        "image/"
    ],

    "audio": [
        "audio/"
    ],

    "video": [
        "video/"
    ],

}



ALLOWED_MIME_TYPES = {

    "pdf": [
        "application/pdf"
    ],


    "document": [

        "application/pdf",

        "application/msword",

        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",

        "application/vnd.ms-powerpoint",

        "application/vnd.openxmlformats-officedocument.presentationml.presentation",

        "application/vnd.ms-excel",

        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

    ],

}



# ======================================================
# VALIDATIONS
# ======================================================


def get_extension(filename: str) -> str:

    if not filename or "." not in filename:

        raise HTTPException(
            status_code=400,
            detail="Fichier sans extension"
        )


    return filename.split(".")[-1].lower()




def validate_extension(
    extension: str,
    allowed_extensions: set[str]
):

    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=f"Extension non autorisée: .{extension}"
        )




def validate_mime(
    file: UploadFile,
    file_type: str
):

    content_type = (
        file.content_type
        or mimetypes.guess_type(file.filename)[0]
    )


    if not content_type:

        raise HTTPException(
            status_code=400,
            detail="Type MIME impossible à détecter"
        )


    if file_type in ALLOWED_MIME_PREFIXES:

        prefixes = ALLOWED_MIME_PREFIXES[file_type]


        if not any(
            content_type.startswith(prefix)
            for prefix in prefixes
        ):

            raise HTTPException(
                status_code=400,
                detail=f"Type MIME invalide: {content_type}"
            )



    if file_type in ALLOWED_MIME_TYPES:

        allowed = ALLOWED_MIME_TYPES[file_type]


        if content_type not in allowed:

            raise HTTPException(
                status_code=400,
                detail=f"Type MIME invalide: {content_type}"
            )




# ======================================================
# NOUVEAU SAVE FILE R2
# ======================================================


async def save_file(
    file: UploadFile,
    folder: str,
    allowed_extensions: set[str],
    max_size: int,
    file_type: str,
):


    extension = get_extension(
        file.filename
    )


    validate_extension(
        extension,
        allowed_extensions
    )


    validate_mime(
        file,
        file_type
    )



    # Lecture taille + contrôle avant upload

    size = 0

    chunks = []


    while True:

        chunk = await file.read(
            1024 * 1024
        )


        if not chunk:

            break


        size += len(chunk)


        if size > max_size:

            raise HTTPException(
                status_code=413,
                detail="Fichier trop volumineux"
            )


        chunks.append(chunk)



    file_bytes = b"".join(chunks)



    # Upload Cloudflare R2

    result = r2_storage.upload_bytes(
        data=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
        folder=folder,
    )



    # IMPORTANT :
    # On conserve le même format
    # utilisé par la base et frontend


    return {

        "file_url": result["key"],

        "filename": Path(
            result["key"]
        ).name,

        "original_filename":
            file.filename,

        "extension":
            extension,

        "content_type":
            file.content_type,

        "size_bytes":
            size,

        "r2_key":
            result["key"],

    }




# ======================================================
# SUPPRESSION R2
# ======================================================


def delete_local_file(
    file_url: str
):

    """
    Ancien nom conservé
    pour compatibilité.

    Maintenant supprime dans R2.
    """


    if not file_url:

        return False



    try:

        r2_storage.delete_file(
            file_url
        )

        return True


    except Exception:

        return False





# ======================================================
# ACCES PREMIUM
# ======================================================


def require_upload_access(
    db: Session,
    current_user,
    file_url: str
):


    normalized_url = (
        file_url
        .replace("\\", "/")
    )


    db_content = (

        db.query(Content)

        .filter(

            (Content.file_url == normalized_url)

            |

            (Content.video_url == normalized_url)

            |

            (Content.audio_url == normalized_url)

            |

            (Content.thumbnail_url == normalized_url)

        )

        .first()

    )


    if (

        db_content

        and db_content.is_premium

        and current_user.role == "ELEVE"

    ):

        require_premium_access(
            db,
            current_user.id
        )


def get_r2_file_info(file_url: str):
    """
    Récupère un fichier depuis Cloudflare R2
    """

    if not file_url:
        raise HTTPException(
            status_code=400,
            detail="Fichier non spécifié"
        )


    try:

        response = r2_storage.download_file(
            file_url
        )


        return {

            "body": response["Body"],

            "content_type":
                response.get(
                    "ContentType",
                    "application/octet-stream"
                ),

            "size":
                response.get(
                    "ContentLength"
                ),

            "etag":
                response.get(
                    "ETag"
                )

        }


    except Exception as e:

        raise HTTPException(
            status_code=404,
            detail=f"Fichier R2 introuvable : {str(e)}"
        )

def stream_r2_range(
    file_url: str,
    start: int,
    end: int,
    chunk_size: int = 1024 * 1024
):

    """
    Streaming par morceaux depuis Cloudflare R2
    """

    response = r2_storage.download_file(
        file_url,
        range_start=start,
        range_end=end
    )


    body = response["Body"]


    while True:

        chunk = body.read(chunk_size)

        if not chunk:
            break

        yield chunk

@router.post("/profile")
async def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await save_file(
        file=file,
        folder="profiles",
        allowed_extensions=IMAGE_EXTENSIONS,
        max_size=MAX_IMAGE_SIZE,
        file_type="image",
    )

    current_user.profile_url = result["file_url"]

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Photo de profil uploadée",
        **result,
    }


@router.post("/proof")
async def upload_proof_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await save_file(
        file=file,
        folder="proofs",
        allowed_extensions=DOCUMENT_EXTENSIONS,
        max_size=MAX_DOCUMENT_SIZE,
        file_type="document",
    )

    current_user.proof_url = result["file_url"]

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Preuve uploadée",
        **result,
    }


@router.post("/content/file")
async def upload_content_file(
    file: UploadFile = File(...),
    current_user=Depends(require_roles(CONTENT_ROLES)),
):

    result = await save_file(
        file=file,
        folder="contents/files",
        allowed_extensions=DOCUMENT_EXTENSIONS,
        max_size=MAX_DOCUMENT_SIZE,
        file_type="document",
    )


    return {
        "message": "Fichier de contenu uploadé",
        **result,
    }


@router.post("/content/thumbnail")
async def upload_content_thumbnail(
    file: UploadFile = File(...),
    current_user=Depends(require_roles(CONTENT_ROLES)),
):

    result = await save_file(
        file=file,
        folder="contents/thumbnails",
        allowed_extensions=IMAGE_EXTENSIONS,
        max_size=MAX_IMAGE_SIZE,
        file_type="image",
    )


    return {
        "message": "Miniature uploadée",
        **result,
    }


@router.post("/content/video")
async def upload_content_video(
    file: UploadFile = File(...),
    current_user=Depends(require_roles(CONTENT_ROLES)),
):

    result = await save_file(
        file=file,
        folder="contents/videos",
        allowed_extensions=VIDEO_EXTENSIONS,
        max_size=MAX_VIDEO_SIZE,
        file_type="video",
    )


    return {
        "message": "Vidéo uploadée",
        **result,
    }


@router.post("/content/audio")
async def upload_content_audio(
    file: UploadFile = File(...),
    current_user=Depends(require_roles(CONTENT_ROLES)),
):

    result = await save_file(
        file=file,
        folder="contents/audios",
        allowed_extensions=AUDIO_EXTENSIONS,
        max_size=MAX_AUDIO_SIZE,
        file_type="audio",
    )


    return {
        "message": "Audio uploadé",
        **result,
    }


@router.post("/question-image")
async def upload_question_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):

    result = await save_file(
        file=file,
        folder="questions/images",
        allowed_extensions=IMAGE_EXTENSIONS,
        max_size=MAX_IMAGE_SIZE,
        file_type="image",
    )


    return {
        "message": "Image de question uploadée",
        **result,
    }


@router.post("/teacher-answer")
async def upload_teacher_answer_attachment(
    file: UploadFile = File(...),
    current_user=Depends(require_roles(ANSWER_ATTACHMENT_ROLES)),
):
    extension = get_extension(file.filename)

    if extension in DOCUMENT_EXTENSIONS:
        file_type = "document"
    elif extension in IMAGE_EXTENSIONS:
        file_type = "image"
    elif extension in AUDIO_EXTENSIONS:
        file_type = "audio"
    else:
        raise HTTPException(
            status_code=400,
            detail="Type de fichier non supporté"
        )
    
    result = await save_file(
        file=file,
        folder="teacher_answers",
        allowed_extensions=DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS,
        max_size=MAX_DOCUMENT_SIZE,
        file_type=file_type,
    )

    return {
        "message": "Pièce jointe de réponse uploadée",
        **result,
    }


@router.get("/access-url")
def create_file_access_url(
    file_url: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    # Vérifie que le fichier existe
    get_r2_file_info(file_url)


    # Vérifie les droits premium
    require_upload_access(
        db,
        current_user,
        file_url
    )


    payload = {
        "file_url": file_url,
        "user_id": current_user.id,
        "created_at": datetime.utcnow().timestamp(),
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }


    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )


    return {
        "url":
        f"{settings.BACKEND_URL}/api/v1/uploads/stream-secure?token={token}"
    }


@router.get("/public-file")
def get_public_uploaded_file(
    file_url: str = Query(...),
):

    file = get_r2_file_info(
        file_url
    )


    return StreamingResponse(
        file["body"],
        media_type=file["content_type"],
        headers={
            "Cache-Control":
                "public, max-age=86400"
        },
    )

@router.get("/file")
def get_uploaded_file(
    file_url: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    require_upload_access(
        db,
        current_user,
        file_url
    )


    file = get_r2_file_info(
        file_url
    )


    return StreamingResponse(
        file["body"],
        media_type=file["content_type"],
        headers={
            "Content-Disposition":
                "inline",

            "Cache-Control":
                "private, max-age=3600",
        },
    )


@router.delete("/file")
def delete_uploaded_file(
    file_url: str = Query(...),
    current_user=Depends(require_roles(["PROMOTEUR", "ADMINISTRATEUR", "ADMIN"])),
):
    deleted = delete_local_file(file_url)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Fichier introuvable"
        )

    return {
        "message": "Fichier supprimé avec succès",
        "file_url": file_url,
    }


@router.get("/limits")
def get_upload_limits(
    current_user=Depends(get_current_user),
):
    return {
        "image_max_mb": MAX_IMAGE_SIZE // (1024 * 1024),
        "pdf_max_mb": MAX_PDF_SIZE // (1024 * 1024),
        "audio_max_mb": MAX_AUDIO_SIZE // (1024 * 1024),
        "video_max_mb": MAX_VIDEO_SIZE // (1024 * 1024),
        "document_max_mb": MAX_DOCUMENT_SIZE // (1024 * 1024),
        "allowed_extensions": {
            "images": sorted(IMAGE_EXTENSIONS),
            "pdf": sorted(PDF_EXTENSIONS),
            "audio": sorted(AUDIO_EXTENSIONS),
            "video": sorted(VIDEO_EXTENSIONS),
            "documents": sorted(DOCUMENT_EXTENSIONS),
        }
    }


@router.get("/stream")
def stream_uploaded_file(
    request: Request,
    file_url: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):


    require_upload_access(
        db,
        current_user,
        file_url
    )


    file = get_r2_file_info(
        file_url
    )


    file_size = file["size"]

    content_type = file["content_type"]


    range_header = request.headers.get(
        "range"
    )


    if range_header:


        value = range_header.replace(
            "bytes=",
            ""
        )


        start_str, end_str = value.split("-")


        start = int(start_str)


        end = (
            int(end_str)
            if end_str
            else file_size - 1
        )


        end = min(
            end,
            file_size - 1
        )


        content_length = (
            end - start + 1
        )


        headers = {

            "Content-Range":
            f"bytes {start}-{end}/{file_size}",

            "Accept-Ranges":
            "bytes",

            "Content-Length":
            str(content_length),

            "Cache-Control":
            "private",

        }


        return StreamingResponse(

            stream_r2_range(
                file_url,
                start,
                end
            ),

            status_code=206,

            headers=headers,

            media_type=content_type

        )



    headers = {


        "Content-Length":
            str(file_size),


        "Accept-Ranges":
            "bytes",


        "Cache-Control":
            "private",

    }



    return StreamingResponse(

        file["body"],

        headers=headers,

        media_type=content_type

    )

@router.get("/stream-secure")
def stream_secure_file(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):


    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )


    except Exception:

        raise HTTPException(
            status_code=403,
            detail="Lien expiré ou invalide"
        )


    file_url = payload.get(
        "file_url"
    )


    user_id = payload.get(
        "user_id"
    )


    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=403,
            detail="Utilisateur inexistant"
        )


    require_upload_access(
        db,
        user,
        file_url
    )


    file = get_r2_file_info(
        file_url
    )


    size = file["size"]

    content_type = file["content_type"]


    range_header = request.headers.get(
        "range"
    )


    if range_header:


        value = range_header.replace(
            "bytes=",
            ""
        )


        start_str,end_str = value.split("-")


        start=int(start_str)


        end = (
            int(end_str)
            if end_str
            else size-1
        )


        headers={

            "Content-Range":
            f"bytes {start}-{end}/{size}",

            "Accept-Ranges":
            "bytes",

            "Content-Length":
            str(end-start+1),

        }



        return StreamingResponse(

            stream_r2_range(
                file_url,
                start,
                end
            ),

            status_code=206,

            headers=headers,

            media_type=content_type

        )


    return StreamingResponse(

        file["body"],

        headers={

            "Content-Length":
            str(size),

            "Accept-Ranges":
            "bytes"

        },

        media_type=content_type

    )


@router.get("/download")
def download_uploaded_file(
    file_url: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    require_upload_access(
        db,
        current_user,
        file_url
    )


    file = get_r2_file_info(
        file_url
    )


    filename = Path(
        file_url
    ).name


    return StreamingResponse(
        file["body"],
        media_type="application/octet-stream",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )

@router.get("/thumbnail/{filename:path}")
def get_thumbnail(
    filename: str
):


    if filename.startswith(
        "contents/thumbnails/"
    ):

        key = filename

    else:

        key = (
            "contents/thumbnails/"
            + filename
        )


    file = get_r2_file_info(
        key
    )


    return StreamingResponse(

        file["body"],

        media_type=file["content_type"],

        headers={
            "Cache-Control":
            "public,max-age=86400"
        }

    )
