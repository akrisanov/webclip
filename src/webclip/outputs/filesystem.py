from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from webclip.models import Document


@dataclass(frozen=True)
class WriteResult:
    output_dir: Path
    written_files: list[Path]


class FilesystemOutput:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def write(
        self,
        document: Document,
        directory_template: str,
        artifacts: dict[str, str | bytes],
    ) -> WriteResult:
        relative_or_absolute = Path(
            directory_template.format(site=document.metadata.site, slug=document.slug)
        )
        output_dir = (
            relative_or_absolute
            if relative_or_absolute.is_absolute()
            else self._base_dir / relative_or_absolute
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files: list[Path] = []
        for filename, content in artifacts.items():
            target = output_dir / filename
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
            written_files.append(target)
        return WriteResult(output_dir=output_dir, written_files=written_files)

    def write_to_directory(
        self,
        output_dir: Path,
        artifacts: dict[str, str | bytes],
    ) -> WriteResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        written_files: list[Path] = []
        for filename, content in artifacts.items():
            target = output_dir / filename
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
            written_files.append(target)
        return WriteResult(output_dir=output_dir, written_files=written_files)
