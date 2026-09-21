from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ABSTRACT_DIR = ROOT / "abstract"
OUTPUT_DIR = ROOT / "output" / "pdf"
BUILD_DIR = ROOT / "tmp" / "pdfs" / "abstract-build"


def build(source_name: str, output_name: str) -> Path:
    source = ABSTRACT_DIR / source_name
    variant_build_dir = BUILD_DIR / source.stem
    variant_build_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "latexmk",
            "-pdfxe",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-outdir={variant_build_dir}",
            str(source),
        ],
        cwd=ABSTRACT_DIR,
        check=True,
    )

    output = OUTPUT_DIR / output_name
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(variant_build_dir / f"{source.stem}.pdf", output)
    return output


def main() -> None:
    indonesia = build("main-indonesia.tex", "abstract-indonesia.pdf")
    english = build("main-english.tex", "abstract-english.pdf")
    print(f"Created {indonesia}")
    print(f"Created {english}")


if __name__ == "__main__":
    main()
