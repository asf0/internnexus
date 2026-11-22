"""Rotate stored resume ciphertexts to the dedicated encryption key."""

from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.db import get_sync_engine
from app.models import UserResume
from app.services.users.resume import (
    decrypt_resume_text,
    decrypt_resume_text_dedicated,
    encrypt_resume_text,
)


def rotate_resumes(*, apply: bool, batch_size: int = 100) -> tuple[int, int]:
    """Rotate all resume ciphertexts, committing in bounded batches when applying."""
    scanned = 0
    rotated = 0
    with Session(get_sync_engine()) as session:
        resume_ids = session.scalars(
            select(UserResume.id)
            .where(UserResume.encrypted_resume_text.is_not(None))
            .order_by(UserResume.id)
        ).all()
        for resume_id in resume_ids:
            resume = session.get(UserResume, resume_id)
            if resume is None or not resume.encrypted_resume_text:
                continue
            scanned += 1
            plaintext = decrypt_resume_text(resume.encrypted_resume_text)
            rotated_ciphertext = encrypt_resume_text(plaintext)
            decrypt_resume_text_dedicated(rotated_ciphertext)
            rotated += 1
            if apply:
                resume.encrypted_resume_text = rotated_ciphertext
                if rotated % batch_size == 0:
                    session.commit()
        if apply:
            session.commit()
        else:
            session.rollback()
    return scanned, rotated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rotate resume encryption to RESUME_ENCRYPTION_KEY (dry-run by default)."
    )
    parser.add_argument("--apply", action="store_true", help="Persist the rotated ciphertexts")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    scanned, rotated = rotate_resumes(apply=args.apply, batch_size=args.batch_size)
    mode = "applied" if args.apply else "dry-run"
    print(f"Resume rotation {mode}: scanned={scanned} verified={rotated}")


if __name__ == "__main__":
    main()
