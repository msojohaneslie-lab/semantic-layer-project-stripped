import json
from pathlib import Path

def load_json_file(file_path: Path):
    try:
        with open(file_path,"r",encoding="utf-8",) as f:
            return json.load(f)

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Index file does not exist: {file_path}"
        )

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in {file_path}: {str(e)}"
        )

    except Exception as e:
        raise RuntimeError(
            f"Failed to read {file_path}: {str(e)}"
        )
