"""Install npm locally when the host only supplies node.exe."""
from pathlib import Path
import tarfile
import urllib.request

destination = Path(__file__).resolve().parents[1] / ".tools"
destination.mkdir(exist_ok=True)
archive = destination / "npm.tgz"
urllib.request.urlretrieve("https://registry.npmjs.org/npm/-/npm-11.6.2.tgz", archive)
with tarfile.open(archive) as tar:
    tar.extractall(destination, filter="data")
archive.unlink()
print(destination / "package" / "bin" / "npm-cli.js")
