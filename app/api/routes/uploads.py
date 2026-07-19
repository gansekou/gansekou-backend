import uuid
import mimetypes
from pathlib import Path
from fastapi import HTTPException


import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.core.premium import require_premium_access
from app.models.content import Content

from fastapi import Request
from fastapi.responses import StreamingResponse

router = APIRouter()

BASE_UPLOAD_DIR = settings.UPLOAD_DIR
BASE_UPLOAD_PATH = Path(BASE_UPLOAD_DIR).resolve()

CONTENT_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR", "ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"]
ANSWER_ATTACHMENT_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR", "ENSEIGNANT"]

MAX_IMAGE_SIZE = 5 * 1024 * 1024        # 5 MB
MAX_PDF_SIZE = 25 * 1024 * 1024         # 25 MB
MAX_AUDIO_SIZE = 50 * 1024 * 1024       # 50 MB
MAX_VIDEO_SIZE = 200 * 1024 * 1024      # 200 MB
MAX_DOCUMENT_SIZE = 30 * 1024 * 1024    # 30 MB

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
PDF_EXTENSIONS = {"pdf"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "aac", "ogg"}
VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "mkv"}
DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"}

ALLOWED_MIME_PREFIXES = {
    "image": ["image/"],
    "audio": ["audio/"],
    "video": ["video/"],
}

ALLOWED_MIME_TYPES = {
    "pdf": ["application/pdf"],
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


def get_extension(filename: str) -> str:
    if not filename or "." not in filename:
        raise HTTPException(status_code=400, detail="Fichier sans extension")

    return filename.split(".")[-1].lower()


def validate_extension(extension: str, allowed_extensions: set[str]):
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Extension non autorisée: .{extension}"
        )


def validate_mime(file: UploadFile, file_type: str):
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0]

    if not content_type:
        raise HTTPException(
            status_code=400,
            detail="Type MIME impossible à détecter"
        )

    if file_type in ALLOWED_MIME_PREFIXES:
        prefixes = ALLOWED_MIME_PREFIXES[file_type]

        if not any(content_type.startswith(prefix) for prefix in prefixes):
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


async def save_file(
    file: UploadFile,
    folder: str,
    allowed_extensions: set[str],
    max_size: int,
    file_type: str,
):
    extension = get_extension(file.filename)

    validate_extension(extension, allowed_extensions)
    validate_mime(file, file_type)

    folder_path = Path(BASE_UPLOAD_DIR) / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}.{extension}"
    file_path = folder_path / filename

    size = 0

    async with aiofiles.open(file_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)

            if size > max_size:
                await out_file.close()

                if file_path.exists():
                    file_path.unlink()

                raise HTTPException(
                    status_code=413,
                    detail="Fichier trop volumineux"
                )

            await out_file.write(chunk)

    return {
        "file_url": str(file_path).replace("\\", "/"),
        "filename": filename,
        "original_filename": file.filename,
        "extension": extension,
        "content_type": file.content_type,
        "size_bytes": size,
    }


def delete_local_file(file_url: str):
    path = safe_file_path(file_url)

    path.unlink()
    return True


def safe_file_path(file_url: str) -> Path:
    """
    Construit un chemin sécurisé à partir d'un chemin relatif
    stocké en base de données.

    Exemple :
        contents/files/d9850fef-c0b6-4e33-99a9-2af370c88aad.pdf
        contents/videos/video.mp4
        contents/audios/audio.mp3
    """

    if not file_url:
        raise HTTPException(
            status_code=400,
            detail="Chemin fichier vide"
        )

    try:
        relative_path = Path(file_url.replace("\\", "/"))

        # Interdit les chemins absolus
        if relative_path.is_absolute():
            raise HTTPException(
                status_code=400,
                detail="Chemin absolu interdit"
            )

        path = (BASE_UPLOAD_PATH / relative_path).resolve()

        # Empêche toute sortie du dossier uploads
        path.relative_to(BASE_UPLOAD_PATH)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Accès interdit au fichier"
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Chemin fichier invalide"
        )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Fichier introuvable"
        )

    if not path.is_file():
        raise HTTPException(
            status_code=400,
            detail="Le chemin ne correspond pas à un fichier"
        )

    return path


def iter_file_range(path: Path, start: int, end: int, chunk_size: int = 1024 * 1024):
    with open(path, "rb") as file:
        file.seek(start)
        remaining = end - start + 1

        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = file.read(read_size)

            if not data:
                break

            remaining -= len(data)
            yield data


def require_upload_access(db: Session, current_user, file_url: str):
    normalized_url = file_url.replace("\\", "/")
    db_content = (
        db.query(Content)
        .filter(
            (Content.file_url == normalized_url)
            | (Content.video_url == normalized_url)
            | (Content.audio_url == normalized_url)
            | (Content.thumbnail_url == normalized_url)
        )
        .first()
    )

    if db_content and db_content.is_premium and current_user.role == "ELEVE":
        require_premium_access(db, current_user.id)


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
    result = await save_file(
        file=file,
        folder="teacher_answers",
        allowed_extensions=DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS,
        max_size=MAX_DOCUMENT_SIZE,
        file_type="document" if get_extension(file.filename) in DOCUMENT_EXTENSIONS else "image",
    )

    return {
        "message": "Pièce jointe de réponse uploadée",
        **result,
    }


@router.get("/file")
def get_uploaded_file(
    file_url: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    path = safe_file_path(file_url)
    require_upload_access(db, current_user, file_url)

    return FileResponse(str(path))


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
    path = safe_file_path(file_url)
    require_upload_access(db, current_user, file_url)

    file_size = path.stat().st_size
    content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

    range_header = request.headers.get("range")

    if range_header:
        range_value = range_header.replace("bytes=", "")
        start_str, end_str = range_value.split("-")

        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

        if start >= file_size:
            raise HTTPException(status_code=416, detail="Range invalide")

        end = min(end, file_size - 1)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": content_type,
        }

        return StreamingResponse(
            iter_file_range(path, start, end),
            status_code=206,
            headers=headers,
            media_type=content_type,
        )

    headers = {
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Content-Type": content_type,
    }

    return StreamingResponse(
        iter_file_range(path, 0, file_size - 1),
        headers=headers,
        media_type=content_type,
    )


@router.get("/download")
def download_uploaded_file(
    file_url: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    path = safe_file_path(file_url)
    require_upload_access(db, current_user, file_url)

    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/octet-stream"
    )
