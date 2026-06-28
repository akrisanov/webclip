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
        output_dir = self.resolve_output_dir(
            document=document,
            directory_template=directory_template,
        )
        return self.write_to_directory(output_dir=output_dir, artifacts=artifacts)

    def resolve_output_dir(self, document: Document, directory_template: str) -> Path:
        relative_or_absolute = Path(
            directory_template.format(site=document.metadata.site, slug=document.slug)
        )
        return (
            relative_or_absolute
            if relative_or_absolute.is_absolute()
            else self._base_dir / relative_or_absolute
        )

    def write_to_directory(
        self,
        output_dir: Path,
        artifacts: dict[str, str | bytes],
    ) -> WriteResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        written_files: list[Path] = []
        for filename, content in artifacts.items():
            target = output_dir / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
            written_files.append(target)
        return WriteResult(output_dir=output_dir, written_files=written_files)
