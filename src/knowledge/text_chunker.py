from __future__ import annotations
import dataclasses
import re
import uuid
from typing import Dict, List


@dataclasses.dataclass
class TextChunk:
    """A chunk of text from a Classical Chinese historical text."""
    id: str
    text: str
    metadata: Dict
    start_pos: int
    end_pos: int


class ClassicalChineseChunker:
    """Chunker for Classical Chinese historical texts with different strategies."""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def normalize_punctuation(self, text: str) -> str:
        """Clean up inconsistent punctuation in Classical Chinese texts."""
        # Normalize different types of periods
        text = re.sub(r'[．。]', '。', text)
        # Normalize different types of commas
        text = re.sub(r'[，、﹐]', '，', text)
        # Normalize quotation marks
        text = re.sub(r'[「『]', '「', text)
        text = re.sub(r'[』」]', '」', text)
        # Normalize question marks
        text = re.sub(r'[？]', '？', text)
        # Normalize exclamation marks
        text = re.sub(r'[！]', '！', text)
        # Normalize semicolons
        text = re.sub(r'[；]', '；', text)
        # Remove extra whitespace while preserving some structure
        text = re.sub(r'[ \t]+', '', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()

    def chunk_by_biography(self, text: str, meta: Dict) -> List[TextChunk]:
        """Split 纪传体 texts (e.g., 魏书) by 卷/列传 patterns."""
        text = self.normalize_punctuation(text)
        chunks = []

        # Pattern for 卷 (volume) and 列传 (biography) headers
        # Examples: "卷一", "卷二十", "列传第一", "武帝纪"
        biography_pattern = r'(卷[一二三四五六七八九十百千]+|列传第[一二三四五六七八九十]+|[^。]*纪|[^。]*传)'

        # Find all biography section headers
        matches = list(re.finditer(biography_pattern, text))

        if not matches:
            # Fallback to generic chunking if no biography headers found
            return self.chunk_text(text, meta)

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end]
            section_title = match.group(0)

            # Further split long sections
            if len(section_text) > self.chunk_size:
                sub_chunks = self._split_by_sentences(section_text, start)
                for sub_text, sub_start, sub_end in sub_chunks:
                    chunk_meta = dict(meta)
                    chunk_meta['section'] = section_title
                    chunk_meta['chunk_type'] = 'biography'
                    chunks.append(TextChunk(
                        id=str(uuid.uuid4()),
                        text=sub_text,
                        metadata=chunk_meta,
                        start_pos=sub_start,
                        end_pos=sub_end
                    ))
            else:
                chunk_meta = dict(meta)
                chunk_meta['section'] = section_title
                chunk_meta['chunk_type'] = 'biography'
                chunks.append(TextChunk(
                    id=str(uuid.uuid4()),
                    text=section_text,
                    metadata=chunk_meta,
                    start_pos=start,
                    end_pos=end
                ))

        return chunks

    def chunk_by_year(self, text: str, meta: Dict) -> List[TextChunk]:
        """Split 编年体 texts (e.g., 资治通鉴) by year patterns."""
        text = self.normalize_punctuation(text)
        chunks = []

        # Year patterns for Northern Wei and related periods
        # Matches reign titles followed by year numbers
        year_pattern = r'((?:太延|太平真君|正平|兴安|兴光|太安|和平|天安|皇兴|延兴|承明|太和|景明|正始|永平|延昌|熙平|神龟|正光|孝昌|武泰|建义|永安|普泰|中兴|太昌|永兴|神瑞|泰常|始光|神䴥|延和|太延|真君|承平|文成|献文|孝文|宣武|孝明|孝庄|节闵|后废帝|出帝|太武帝|文成帝|献文帝|孝文帝|宣武帝|孝明帝|孝庄帝|节闵帝|(?:永初|元嘉|孝建|大明|泰始|泰豫|升明|建元|永明|隆昌|延兴|建武|永泰|永元|中兴|天监|普通|大通|中大通|大同|中大同|太清|大宝|天正|承圣|天成|绍泰|太平|永定|天嘉|天康|光大|太建|至德|祯明|(?:太兴|麟嘉|光初|太和|建平|太宁|咸和|咸康|建元|永和|升平|隆和|兴宁|太和|咸安|宁康|太元|隆安|元兴|义熙|元熙)))[元一二三四五六七八九十百千]+年)'

        matches = list(re.finditer(year_pattern, text))

        if not matches:
            # Try simpler pattern with common reign titles
            simple_year_pattern = r'([太延|太平真君|正平|兴安|兴光|太安|和平|天安|皇兴|延兴|承明|太和|景明|正始|永平|延昌|熙平|神龟|正光|孝昌|武泰|建义|永安|永兴|神瑞|泰常|始光|神䴥|延和|太武帝|文成帝|献文帝|孝文帝|宣武帝|孝明帝|孝庄帝|节闵帝][元一二三四五六七八九十百千]+年)'
            matches = list(re.finditer(simple_year_pattern, text))

        if not matches:
            return self.chunk_text(text, meta)

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            year_text = text[start:end]
            year_title = match.group(0)

            if len(year_text) > self.chunk_size:
                sub_chunks = self._split_by_sentences(year_text, start)
                for sub_text, sub_start, sub_end in sub_chunks:
                    chunk_meta = dict(meta)
                    chunk_meta['year'] = year_title
                    chunk_meta['chunk_type'] = 'chronological'
                    chunks.append(TextChunk(
                        id=str(uuid.uuid4()),
                        text=sub_text,
                        metadata=chunk_meta,
                        start_pos=sub_start,
                        end_pos=sub_end
                    ))
            else:
                chunk_meta = dict(meta)
                chunk_meta['year'] = year_title
                chunk_meta['chunk_type'] = 'chronological'
                chunks.append(TextChunk(
                    id=str(uuid.uuid4()),
                    text=year_text,
                    metadata=chunk_meta,
                    start_pos=start,
                    end_pos=end
                ))

        return chunks

    def chunk_by_entry(self, text: str, meta: Dict) -> List[TextChunk]:
        """Split 地理志 (e.g., 洛阳伽蓝记) by entry headers."""
        text = self.normalize_punctuation(text)
        chunks = []

        # Pattern for entry headers in geographical/chronicle texts
        # Examples: "永宁寺", "建中寺", "长秋寺" (temple names)
        # Or numbered entries like "第一", "卷一"
        entry_pattern = r'([内城外城]{0,2}[东西南北]{0,2}(?:永宁寺|建中寺|长秋寺|瑶光寺|景乐寺|昭仪尼寺|胡统寺|修梵寺|景林寺|建春门|东阳门|青阳门|开阳门|平昌门|宣阳门|寿丘里|闻义里|金陵馆|燕然馆|归正里|归德里|慕义里|慕化里)[^。]{0,10}|卷[一二三四五六七八九十百千]+)'

        matches = list(re.finditer(entry_pattern, text))

        if not matches:
            # Fallback: try to find temple/building names
            temple_pattern = r'([^。，]{2,6}(?:寺|观|院|堂|阁|楼|门|里|馆)[^。]{0,5})'
            matches = list(re.finditer(temple_pattern, text))

        if not matches:
            return self.chunk_text(text, meta)

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            entry_text = text[start:end]
            entry_title = match.group(0)

            if len(entry_text) > self.chunk_size:
                sub_chunks = self._split_by_sentences(entry_text, start)
                for sub_text, sub_start, sub_end in sub_chunks:
                    chunk_meta = dict(meta)
                    chunk_meta['entry'] = entry_title
                    chunk_meta['chunk_type'] = 'geographical'
                    chunks.append(TextChunk(
                        id=str(uuid.uuid4()),
                        text=sub_text,
                        metadata=chunk_meta,
                        start_pos=sub_start,
                        end_pos=sub_end
                    ))
            else:
                chunk_meta = dict(meta)
                chunk_meta['entry'] = entry_title
                chunk_meta['chunk_type'] = 'geographical'
                chunks.append(TextChunk(
                    id=str(uuid.uuid4()),
                    text=entry_text,
                    metadata=chunk_meta,
                    start_pos=start,
                    end_pos=end
                ))

        return chunks

    def chunk_text(self, text: str, meta: Dict) -> List[TextChunk]:
        """Generic fallback using sentence boundaries (。！？；)."""
        text = self.normalize_punctuation(text)
        return self._create_chunks_from_sentences(text, meta)

    def _split_by_sentences(self, text: str, base_pos: int) -> List[tuple]:
        """Split text into chunks respecting sentence boundaries."""
        # Sentence delimiters: 。！？；
        sentence_pattern = r'([。！？；])'
        sentences = re.split(sentence_pattern, text)

        # Recombine sentences with their delimiters
        full_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                full_sentences.append(sentences[i] + sentences[i + 1])
            else:
                full_sentences.append(sentences[i])
        if len(sentences) % 2 == 1:
            full_sentences.append(sentences[-1])

        result = []
        current_chunk = ""
        chunk_start = base_pos
        current_pos = base_pos

        for sentence in full_sentences:
            if not sentence.strip():
                current_pos += len(sentence)
                continue

            # If adding this sentence exceeds chunk size, finalize current chunk
            if len(current_chunk) + len(sentence) > self.chunk_size and len(current_chunk) >= 200:
                result.append((current_chunk, chunk_start, current_pos))
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + sentence
                chunk_start = current_pos - len(overlap_text)
            else:
                current_chunk += sentence

            current_pos += len(sentence)

        # Add remaining text
        if current_chunk.strip():
            result.append((current_chunk, chunk_start, current_pos))

        return result

    def _create_chunks_from_sentences(self, text: str, meta: Dict) -> List[TextChunk]:
        """Create TextChunk objects from sentence-based splitting."""
        splits = self._split_by_sentences(text, 0)
        chunks = []

        for chunk_text, start_pos, end_pos in splits:
            chunk_meta = dict(meta)
            chunk_meta['chunk_type'] = 'generic'
            chunks.append(TextChunk(
                id=str(uuid.uuid4()),
                text=chunk_text,
                metadata=chunk_meta,
                start_pos=start_pos,
                end_pos=end_pos
            ))

        return chunks
