import os
import subprocess
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.discord import send_discord_message
from app.core.models import ScanResult, ScanTarget, Setting


def _get_setting(session: Session, key: str, default: str = "") -> str:
    value = session.query(Setting).filter(Setting.key == key).first()
    return value.value if value else default


def get_video_extensions(session: Session) -> tuple[str, ...]:
    raw = _get_setting(session, "video_extensions", ".mp4,.mkv,.avi,.mov,.flv,.wmv")
    extensions = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    return extensions or (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")


def get_file_list(scan_path: str, video_extensions: tuple[str, ...]) -> list[dict[str, float | str]]:
    video_files: list[dict[str, float | str]] = []
    for root, _, files in os.walk(scan_path):
        for file_name in files:
            if file_name.lower().endswith(video_extensions):
                file_path = os.path.join(root, file_name)
                last_modified = os.path.getmtime(file_path)
                video_files.append({"file_path": file_path, "last_modified": last_modified})
    return video_files


def run_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return result.stderr.strip()
    except Exception as exc:
        return f"Error running command: {exc}"


def check_video_file(file_path: str) -> dict[str, str]:
    corruption_check = run_command(["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"])
    if corruption_check:
        return {"status": "Corruption Detected", "details": corruption_check}

    stream_check = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate",
            "-of",
            "csv=p=0",
            file_path,
        ]
    )
    if not stream_check:
        return {"status": "Stream Issues", "details": "No valid video stream detected"}

    return {"status": "OK", "details": stream_check}


def _upsert_result(
    session: Session,
    target_id: int,
    file_path: str,
    last_modified: float,
    status: str,
    details: str,
    duration: float,
) -> None:
    existing = (
        session.query(ScanResult)
        .filter(ScanResult.target_id == target_id, ScanResult.file_path == file_path)
        .first()
    )
    if existing:
        existing.last_modified = last_modified
        existing.status = status
        existing.details = details
        existing.scan_duration_seconds = duration
        existing.scanned_at = datetime.utcnow()
        return

    session.add(
        ScanResult(
            target_id=target_id,
            file_path=file_path,
            last_modified=last_modified,
            status=status,
            details=details,
            scan_duration_seconds=duration,
            scanned_at=datetime.utcnow(),
        )
    )


def scan_target(session: Session, target: ScanTarget) -> int:
    if not os.path.isdir(target.path):
        return 0

    video_extensions = get_video_extensions(session)
    files = get_file_list(target.path, video_extensions)

    general_webhook = _get_setting(session, "general_discord_webhook", "")
    failed_webhook = _get_setting(session, "failed_discord_webhook", "")

    scanned_count = 0
    for file_info in files:
        file_path = str(file_info["file_path"])
        last_modified = float(file_info["last_modified"])

        existing = (
            session.query(ScanResult)
            .filter(ScanResult.target_id == target.id, ScanResult.file_path == file_path)
            .first()
        )
        existing_modified = existing.last_modified if existing else 0.0
        if last_modified <= existing_modified:
            continue

        started = datetime.utcnow()
        check = check_video_file(file_path)
        duration = (datetime.utcnow() - started).total_seconds()

        _upsert_result(
            session=session,
            target_id=target.id,
            file_path=file_path,
            last_modified=last_modified,
            status=check["status"],
            details=check["details"],
            duration=duration,
        )
        scanned_count += 1

        if check["status"] == "OK":
            send_discord_message(
                (
                    f"✅ [{target.label}] Video check completed successfully:\n"
                    f"File: {file_path}\n"
                    f"Details: {check['details']}\n"
                    f"Time Taken: {duration:.2f} seconds"
                ),
                general_webhook,
            )
        else:
            send_discord_message(
                (
                    f"⚠️ [{target.label}] Video check failed:\n"
                    f"File: {file_path}\n"
                    f"Status: {check['status']}\n"
                    f"Details: {check['details']}\n"
                    f"Time Taken: {duration:.2f} seconds"
                ),
                failed_webhook,
            )

    session.commit()
    send_discord_message(
        f"✅ [{target.label}] Video scan completed. {scanned_count} files checked.",
        general_webhook,
    )
    return scanned_count


def run_full_scan(session: Session) -> dict[str, int]:
    targets = session.query(ScanTarget).filter(ScanTarget.enabled.is_(True)).all()
    summary: dict[str, int] = {}
    for target in targets:
        summary[target.label] = scan_target(session, target)
    return summary
