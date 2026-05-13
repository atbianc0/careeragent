from pathlib import Path
import json
from shutil import copy2
import shutil
import subprocess

from app.core.config import settings

RESUME_GITHUB_SAFETY_NOTE = (
    "Your real resume should live in data/resume/base_resume.tex, which is ignored by Git. "
    "Generated PDFs under outputs/resume/ are also ignored."
)
LATEX_TIMEOUT_SECONDS = 30


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(settings.project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _resume_missing_message() -> str:
    return (
        "No resume file was found. Expected data/resume/base_resume.tex or "
        "data/resume/base_resume.example.tex."
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _validate_compile_paths(input_path: Path, output_dir: Path) -> None:
    allowed_input_roots = [settings.data_dir / "resume", settings.application_packets_dir]
    allowed_output_root = settings.application_packets_dir
    allowed_resume_output_root = settings.outputs_dir / "resume"

    if not any(_is_within(input_path, root) for root in allowed_input_roots):
        raise ValueError("LaTeX compilation only supports files inside data/resume or outputs/application_packets.")
    if not (_is_within(output_dir, allowed_output_root) or _is_within(output_dir, allowed_resume_output_root)):
        raise ValueError("LaTeX output must stay inside outputs/application_packets or outputs/resume.")


def resolve_resume_source_and_path() -> tuple[str, Path]:
    if settings.resume_path.exists():
        return "private", settings.resume_path

    if settings.resume_example_path.exists():
        return "example", settings.resume_example_path

    raise FileNotFoundError(_resume_missing_message())


def resolve_resume_template_path() -> Path | None:
    try:
        _, path = resolve_resume_source_and_path()
        return path
    except FileNotFoundError:
        return None


def load_resume_document() -> dict[str, str]:
    source, path = resolve_resume_source_and_path()
    content = path.read_text(encoding="utf-8")
    return {
        "source": source,
        "path": _relative_path(path),
        "content": content,
    }


def save_resume_content(content: str) -> dict[str, str]:
    settings.resume_path.parent.mkdir(parents=True, exist_ok=True)
    settings.resume_path.write_text(content, encoding="utf-8")
    return {
        "source": "private",
        "path": _relative_path(settings.resume_path),
        "content": content,
        "message": "Saved resume content to the private local file.",
    }


def create_private_resume_from_example() -> dict[str, str]:
    if settings.resume_path.exists():
        document = load_resume_document()
        document["message"] = "Private resume already exists."
        return document

    if not settings.resume_example_path.exists():
        raise FileNotFoundError(_resume_missing_message())

    settings.resume_path.parent.mkdir(parents=True, exist_ok=True)
    copy2(settings.resume_example_path, settings.resume_path)

    document = load_resume_document()
    document["message"] = "Created data/resume/base_resume.tex from the safe public example template."
    return document


def find_latex_compiler() -> str | None:
    for compiler_name in _available_latex_compilers():
        return compiler_name
    return None


def _available_latex_compilers() -> list[str]:
    compilers: list[str] = []
    for compiler_name in ("xelatex", "pdflatex"):
        if shutil.which(compiler_name):
            compilers.append(compiler_name)
    return compilers


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def _resume_output_dir() -> Path:
    return settings.outputs_dir / "resume"


def get_last_compile_output_path() -> str | None:
    output_dir = _resume_output_dir()
    if not output_dir.exists():
        return None

    candidates = [output_dir / "base_resume.pdf", output_dir / "base_resume_example.pdf"]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None

    latest = max(existing, key=lambda path: path.stat().st_mtime)
    return _relative_path(latest)


def get_resume_status() -> dict[str, str | bool | None]:
    private_exists = settings.resume_path.exists()
    example_exists = settings.resume_example_path.exists()

    if private_exists:
        active_source = "private"
    elif example_exists:
        active_source = "example"
    else:
        active_source = "missing"

    compiler_name = find_latex_compiler()

    return {
        "private_resume_exists": private_exists,
        "example_resume_exists": example_exists,
        "active_source": active_source,
        "private_resume_path": _relative_path(settings.resume_path),
        "example_resume_path": _relative_path(settings.resume_example_path),
        "latex_compiler_available": compiler_name is not None,
        "compiler_name": compiler_name,
        "last_compile_output_path": get_last_compile_output_path(),
        "github_safety_note": RESUME_GITHUB_SAFETY_NOTE,
    }


def _compile_latex_once(
    *,
    compiler_name: str,
    input_path: Path,
    output_dir: Path,
    output_name: str,
    output_path: Path,
) -> dict[str, str | bool | None]:
    if output_path.exists():
        output_path.unlink()

    command = [
        compiler_name,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        f"-jobname={output_name}",
        f"-output-directory={output_dir.resolve()}",
        str(input_path.resolve()),
    ]

    try:
        result = subprocess.run(
            command,
            cwd=input_path.parent.resolve(),
            capture_output=True,
            text=True,
            timeout=LATEX_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logs = "\n".join(part for part in [exc.stdout or "", exc.stderr or ""] if part).strip()
        return {
            "success": False,
            "source": "custom",
            "compiler": compiler_name,
            "input_path": _relative_path(input_path),
            "output_path": _relative_path(output_path),
            "message": "LaTeX compilation timed out.",
            "logs": logs,
        }

    logs = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    success = result.returncode == 0 and output_path.exists()
    message = "LaTeX compilation succeeded." if success else "LaTeX compilation failed. Review the compiler logs for details."

    return {
        "success": success,
        "source": "custom",
        "compiler": compiler_name,
        "input_path": _relative_path(input_path),
        "output_path": _relative_path(output_path),
        "message": message,
        "logs": logs,
    }


def _compile_latex_with_docker(input_path: Path, output_dir: Path, output_name: str) -> dict[str, str | bool | None]:
    output_path = output_dir / f"{output_name}.pdf"
    docker_path = shutil.which("docker")
    if not docker_path:
        return {
            "success": False,
            "source": "custom",
            "compiler": None,
            "input_path": _relative_path(input_path),
            "output_path": _relative_path(output_path),
            "message": "No local LaTeX compiler was found, and Docker was not available for fallback compilation.",
            "logs": "",
        }

    try:
        input_arg = input_path.resolve().relative_to(settings.project_root.resolve()).as_posix()
        output_arg = output_dir.resolve().relative_to(settings.project_root.resolve()).as_posix()
    except ValueError:
        return {
            "success": False,
            "source": "custom",
            "compiler": None,
            "input_path": _relative_path(input_path),
            "output_path": _relative_path(output_path),
            "message": "Docker LaTeX fallback only supports files inside the CareerAgent project.",
            "logs": "",
        }

    script = "\n".join(
        [
            "from pathlib import Path",
            "import json",
            "from app.services.resume.latex_resume import compile_latex_file",
            f"result = compile_latex_file(Path({input_arg!r}), Path({output_arg!r}), {output_name!r})",
            "print(json.dumps(result, default=str))",
        ]
    )
    command = [
        docker_path,
        "compose",
        "run",
        "-T",
        "--rm",
        "--no-deps",
        "backend",
        "python",
        "-c",
        script,
    ]

    try:
        result = subprocess.run(
            command,
            cwd=settings.project_root.resolve(),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logs = "\n".join(part for part in [exc.stdout or "", exc.stderr or ""] if part).strip()
        return {
            "success": False,
            "source": "custom",
            "compiler": "docker",
            "input_path": _relative_path(input_path),
            "output_path": _relative_path(output_path),
            "message": "Docker LaTeX fallback timed out.",
            "logs": logs,
        }

    logs = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    parsed: dict[str, str | bool | None] | None = None
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
            break
        except json.JSONDecodeError:
            continue

    if parsed is None:
        return {
            "success": False,
            "source": "custom",
            "compiler": "docker",
            "input_path": _relative_path(input_path),
            "output_path": _relative_path(output_path),
            "message": "Docker LaTeX fallback did not return a parseable compile result.",
            "logs": logs,
        }

    parsed["compiler"] = f"docker:{parsed.get('compiler') or 'unknown'}"
    if result.returncode != 0 and parsed.get("success"):
        parsed["success"] = False
        parsed["message"] = "Docker LaTeX fallback exited with an error after compilation."
    if logs:
        parsed["logs"] = logs
    return parsed


def compile_latex_file(input_path: Path, output_dir: Path, output_name: str) -> dict[str, str | bool | None]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    output_path = output_dir / f"{output_name}.pdf"

    try:
        _validate_compile_paths(input_path, output_dir)
    except ValueError as exc:
        return {
            "success": False,
            "source": "custom",
            "compiler": None,
            "input_path": _relative_path(input_path),
            "output_path": _relative_path(output_path),
            "message": str(exc),
            "logs": "",
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    compilers = _available_latex_compilers()
    if not compilers:
        if not _running_in_docker():
            return _compile_latex_with_docker(input_path, output_dir, output_name)
        return {
            "success": False,
            "source": "custom",
            "compiler": None,
            "input_path": _relative_path(input_path),
            "output_path": _relative_path(output_path),
            "message": "No LaTeX compiler was found. Install xelatex or pdflatex to enable PDF compilation.",
            "logs": "",
        }

    attempts: list[dict[str, str | bool | None]] = []
    for compiler_name in compilers:
        attempt = _compile_latex_once(
            compiler_name=compiler_name,
            input_path=input_path,
            output_dir=output_dir,
            output_name=output_name,
            output_path=output_path,
        )
        attempts.append(attempt)
        if attempt.get("success"):
            if len(attempts) > 1:
                failed_compilers = ", ".join(str(item.get("compiler")) for item in attempts[:-1])
                attempt["message"] = f"LaTeX compilation succeeded with {compiler_name} after trying {failed_compilers}."
            return attempt

    final_attempt = attempts[-1]
    if len(attempts) > 1:
        final_attempt["message"] = "LaTeX compilation failed with all available compilers."
        final_attempt["logs"] = "\n\n".join(
            f"===== {attempt.get('compiler')} =====\n{attempt.get('logs') or attempt.get('message') or ''}"
            for attempt in attempts
        )
    return final_attempt


def compile_latex_resume() -> dict[str, str | bool | None]:
    try:
        source, input_path = resolve_resume_source_and_path()
    except FileNotFoundError as exc:
        return {
            "success": False,
            "source": "missing",
            "compiler": None,
            "input_path": "",
            "output_path": None,
            "message": str(exc),
            "logs": "",
        }

    job_name = "base_resume" if source == "private" else "base_resume_example"
    result = compile_latex_file(input_path, _resume_output_dir(), job_name)
    result["source"] = source
    if result["success"]:
        if source == "private":
            result["message"] = "Compiled the private resume successfully."
        else:
            result["message"] = "Compiled the example resume because no private resume exists yet."
    return result
