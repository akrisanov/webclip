from __future__ import annotations

from pathlib import Path

from webclip.models import Document
from webclip.outputs.filesystem import FilesystemOutput, WriteResult


class ObsidianOutput(FilesystemOutput):
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

    def write_to_directory(
        self,
        output_dir: Path,
        artifacts: dict[str, str | bytes],
    ) -> WriteResult:
        result = super().write_to_directory(
            output_dir=output_dir,
            artifacts=artifacts,
        )
        notes_path = result.output_dir / "notes.md"
        if not notes_path.exists():
            notes_path.write_text("## My notes\n\n", encoding="utf-8")
            return WriteResult(
                output_dir=result.output_dir,
                written_files=[*result.written_files, notes_path],
            )
        return result
