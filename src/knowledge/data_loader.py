from __future__ import annotations

import re
from pathlib import Path

from src.utils.logger import get_logger


logger = get_logger(__name__)


class HistoricalTextLoader:
    """Load historical Chinese texts with encoding detection."""

    ENCODINGS = ["utf-8", "gb18030", "big5"]

    FORMAT_KEYWORDS = {
        "weishu": ["魏书", "三国志", "曹魏", "司马懿"],
        "zizhitongjian": ["资治通鉴", "宋纪", "元纪", "明纪"],
        "luoyang": ["洛阳", "东汉", "洛阳伽蓝记"],
    }

    def __init__(self, raw_dir: str) -> None:
        """Initialize the loader with raw directory path.

        Args:
            raw_dir: Directory containing raw text files.
        """
        self.raw_dir = Path(raw_dir)
        if not self.raw_dir.exists():
            logger.warning(f"Directory does not exist: {self.raw_dir}")

    def _detect_encoding(self, file_path: Path) -> str:
        """Detect encoding by trying common encodings.

        Args:
            file_path: Path to the text file.

        Returns:
            Detected encoding name.
        """
        for encoding in self.ENCODINGS:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.read()
                logger.debug(f"Detected encoding {encoding} for {file_path.name}")
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        logger.warning(f"Could not detect encoding for {file_path.name}, defaulting to utf-8")
        return "utf-8"

    def _detect_format(self, content: str) -> str:
        """Detect the format/type of historical text.

        Args:
            content: Text content to analyze.

        Returns:
            Detected format: weishu, zizhitongjian, luoyang, or unknown.
        """
        for format_name, keywords in self.FORMAT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content[:5000]:
                    logger.debug(f"Detected format: {format_name}")
                    return format_name

        return "unknown"

    def load_text(self, filename: str) -> tuple[str, dict]:
        """Load a single text file with encoding detection.

        Args:
            filename: Name of the file to load (relative to raw_dir).

        Returns:
            Tuple of (text_content, metadata_dict).
        """
        file_path = self.raw_dir / filename
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        encoding = self._detect_encoding(file_path)
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        format_type = self._detect_format(content)

        metadata = {
            "filename": filename,
            "encoding": encoding,
            "detected_format": format_type,
        }

        logger.info(f"Loaded {filename} with encoding {encoding}, format {format_type}")
        return content, metadata

    def load_all(self) -> list[tuple[str, dict]]:
        """Load all .txt files in the raw directory.

        Returns:
            List of tuples (text_content, metadata_dict).
        """
        if not self.raw_dir.exists():
            logger.error(f"Directory does not exist: {self.raw_dir}")
            return []

        txt_files = sorted(self.raw_dir.glob("*.txt"))
        logger.info(f"Found {len(txt_files)} .txt files in {self.raw_dir}")

        results = []
        for file_path in txt_files:
            try:
                content, metadata = self.load_text(file_path.name)
                results.append((content, metadata))
            except Exception as e:
                logger.error(f"Failed to load {file_path.name}: {e}")

        return results

    def preprocess(self, text: str) -> str:
        """Preprocess historical text.

        - Normalize punctuation
        - Remove annotations like [注] patterns
        - Clean whitespace
        - Remove page markers

        Args:
            text: Raw text content.

        Returns:
            Preprocessed text.
        """
        result = text

        result = re.sub(r"\[注\d*\]", "", result)
        result = re.sub(r"\[注释\d*\]", "", result)
        result = re.sub(r"\[注\]", "", result)

        result = re.sub(r"第\s*\d+\s*页", "", result)
        result = re.sub(r"页\d+", "", result)
        result = re.sub(r"□+", "", result)

        result = re.sub(r"[，。！？；：、""''【】（）]", lambda m: self._normalize_punctuation(m.group()), result)

        result = re.sub(r"[ \t]+", " ", result)
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = re.sub(r"^\s+|\s+$", "", result, flags=re.MULTILINE)

        return result

    def _normalize_punctuation(self, char: str) -> str:
        """Normalize Chinese punctuation variants.

        Args:
            char: Punctuation character.

        Returns:
            Normalized punctuation.
        """
        punctuation_map = {
            "，": "，",
            "。": "。",
            "！": "！",
            "？": "？",
            "；": "；",
            "：": "：",
            "、": "、",
            '"': '"',
            '"': '"',
            "'": "'",
            "'": "'",
            "【": "【",
            "】": "】",
            "（": "（",
            "）": "）",
        }
        return punctuation_map.get(char, char)
