import os
import re
import unicodedata
from typing import List

from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document

from modules.settings import CHUNK_OVERLAP, CHUNK_SIZE, FILES
from modules.ingestion.loaders import load_document_text, normalize_document_text

SOURCE_NAMES = {
    "noi_khoa_gs_chau": "Noi Khoa YHCT - GS Hoang Bao Chau",
    "benh_ngu_quan": "Benh Ngu Quan YHCT",
    "nhi_khoa": "Nhi Khoa YHCT",
    "noi_khoa_general": "noi-khoa-y-hoc-co-truyen",
}


def normalize_text_for_match(text: str) -> str:
    """Strip Vietnamese diacritics and convert to ASCII-compatible form for robust regex matching."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "D")


def is_section_heading(paragraph: str) -> bool:
    text = " ".join((paragraph or "").split()).strip()
    if not text or len(text) > 140:
        return False
    if text.endswith((".", ",", ";")) and len(text) > 35:
        return False

    normalized = normalize_text_for_match(text).lower()
    if re.match(r"^(chuong|phan|muc|bai|quyen|[ivxlcdm]+\.|\d+(?:\.\d+)*\.)\s+", normalized):
        return True

    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) >= 4:
        upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
        if upper_ratio >= 0.7:
            return True

    return False


def split_sections(text: str, source_id: str, title: str, splitter: str) -> List[Document]:
    raw_text = normalize_document_text(text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n", raw_text) if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current = []
    current_len = 0
    current_section = title or source_id
    chunk_index = 1
    chunk_size = int(os.getenv("GENERIC_CHUNK_SIZE", str(CHUNK_SIZE)))
    overlap = max(0, int(os.getenv("GENERIC_CHUNK_OVERLAP", str(CHUNK_OVERLAP))))

    def add_chunk(content: str, section: str):
        nonlocal chunk_index
        content = content.strip()
        if not content:
            return
        chunks.append(
            Document(
                page_content=content,
                metadata={
                    "source": source_id,
                    "title": title,
                    "section": section or f"Chunk {chunk_index}",
                    "splitter": splitter,
                    "chunk_index": chunk_index,
                },
            )
        )
        chunk_index += 1

    def flush():
        nonlocal current, current_len
        content = "\n\n".join(current).strip()
        add_chunk(content, current_section)
        if overlap > 0 and content:
            overlap_text = content[-overlap:].strip()
            current = [overlap_text] if overlap_text else []
            current_len = len(overlap_text)
        else:
            current = []
            current_len = 0

    for paragraph in paragraphs:
        if is_section_heading(paragraph):
            if current:
                flush()
            current_section = paragraph.strip()
            current = [paragraph]
            current_len = len(paragraph)
            continue

        if len(paragraph) > chunk_size:
            if current:
                flush()
            start = 0
            step = max(1, chunk_size - overlap)
            while start < len(paragraph):
                add_chunk(paragraph[start : start + chunk_size], current_section)
                start += step
            continue

        projected_len = current_len + len(paragraph) + 2
        if current and projected_len > chunk_size:
            flush()

        current.append(paragraph)
        current_len += len(paragraph) + 2

    if current:
        flush()

    return chunks


def split_docx(file_key: str, source_id: str) -> List[Document]:
    """Fallback splitter used when specific book parser returns no chunks."""
    path = FILES[file_key]
    if not os.path.exists(path):
        print(f"[WARNING] File not found for fallback splitter: {path}")
        return []

    print(f"[INFO] Using generic fallback splitter for {source_id}.")
    raw_text = load_document_text(path)
    return split_sections(
        text=raw_text,
        source_id=source_id,
        title=SOURCE_NAMES.get(file_key, source_id),
        splitter="generic_fallback",
    )


def split_source(file_key: str, source_id: str, splitter) -> List[Document]:
    docs = splitter()
    if docs:
        return docs
    return split_docx(file_key, source_id)


def split_gs_chau() -> List[Document]:
    print("[PROCESS] Processing Noi Khoa YHCT - GS Hoang Bao Chau...")
    path = FILES["noi_khoa_gs_chau"]

    if not os.path.exists(path):
        print(f"[WARNING] File not found: {path}")
        return []

    loader = Docx2txtLoader(path)
    raw_text = loader.load()[0].page_content
    raw_text = re.sub(r"\n*\s*_{8,}\s*\n*", "\n__________\n", raw_text)
    parts = re.split(r"\n__________\n", raw_text)

    docs = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        lines = [line.strip() for line in part.split("\n") if line.strip()]
        title_line = lines[0] if lines else f"Untitled {i}"
        for line in lines:
            clean = normalize_text_for_match(line)
            if clean.isupper() or (len(clean) > 5 and clean == clean.upper()):
                title_line = line
                break
        docs.append(Document(page_content=part, metadata={"title": title_line.strip()}))

    patterns = [r"^[A-Z]\.\s", r"^\d+\.\s", r"^\d+\.\d+\.\s", r"^[a-z]\.\s"]

    def recursive_split_gs(lines, current_title, current_section, pattern_index):
        if pattern_index >= len(patterns):
            content = "\n".join(lines).strip()
            if not content:
                return []
            return [
                Document(
                    page_content=content,
                    metadata={
                        "source": "Noi_Khoa_YHCT_GS_Hoang_Bao_Chau",
                        "title": current_title,
                        "section": current_section,
                    },
                )
            ]

        current_pattern = patterns[pattern_index]
        splits = []
        for i, line in enumerate(lines):
            clean_line = normalize_text_for_match(line.strip())
            if re.match(current_pattern, clean_line):
                splits.append((i, line.strip()))

        if not splits:
            return recursive_split_gs(lines, current_title, current_section, pattern_index + 1)

        results = []
        splits = [(0, None)] + splits + [(len(lines), None)]
        splits.sort(key=lambda x: x[0])

        for j in range(len(splits) - 1):
            start_idx, header = splits[j]
            end_idx = splits[j + 1][0]
            sub_lines = lines[start_idx + 1 : end_idx]

            if header is None:
                if not sub_lines:
                    continue
                suffix = " (Dẫn nhập)"
                new_section_name = f"{current_section}{suffix}"
                results.extend(recursive_split_gs(sub_lines, current_title, new_section_name, pattern_index + 1))
            else:
                new_section_name = f"{current_section} - {header}"
                content_for_next_level = [header] + sub_lines
                results.extend(recursive_split_gs(content_for_next_level, current_title, new_section_name, pattern_index + 1))

        return results

    chunks = []
    main_headers = {
        "DAI CUONG", "NGUYEN NHAN", "TRIEU CHUNG", "DIEU TRI", "PHEP TRI",
        "BENH SINH", "BIEN CHUNG", "PHU PHUONG", "PHONG BENH", "CHAN DOAN",
        "CAN LAM SANG", "TIEN TRIEN", "PHAN LOAI", "THE BENH", "PHUONG PHAP DIEU TRI"
    }

    for doc in docs:
        part = doc.page_content.strip()
        title = doc.metadata.get("title", "")
        if not part:
            continue
        lines = part.split("\n")

        splits = []
        for i, line in enumerate(lines):
            clean_header = normalize_text_for_match(line.strip().rstrip(":"))
            if clean_header in main_headers or (clean_header.isupper() and 3 < len(clean_header) < 50):
                splits.append((i, line.strip().rstrip(":")))

        splits = [(0, None)] + splits + [(len(lines), None)]
        splits.sort(key=lambda x: x[0])

        for j in range(len(splits) - 1):
            start_index, header = splits[j]
            end_index = splits[j + 1][0]
            if header is None:
                continue

            section_lines = lines[start_index + 1 : end_index]
            if not section_lines:
                continue

            sub_docs = recursive_split_gs(section_lines, title, header, pattern_index=0)
            for sub_doc in sub_docs:
                sub_doc.page_content = f"{header}\n\n{sub_doc.page_content}"
                chunks.append(sub_doc)

    return chunks


def split_ngu_quan() -> List[Document]:
    print("[PROCESS] Processing Benh Ngu Quan...")
    file_path = FILES["benh_ngu_quan"]

    if not os.path.exists(file_path):
        print(f"[WARNING] File not found: {file_path}")
        return []

    book_name = "Benh Ngu Quan YHCT"
    marker_start = "CHUONG"
    no_split_titles = {"LOI NOI DAU", "DAN NHAP", "MUC LUC"}

    loader = Docx2txtLoader(file_path)
    raw_text = loader.load()[0].page_content
    raw_text = raw_text.replace("</break>", " ").replace("<break>", " ")
    raw_text = re.sub(r"\n*\s*_{8,}\s*\n*", "\n__________\n", raw_text)
    parts = re.split(r"\n__________\n", raw_text)

    sub_patterns = [
        r"^\s*(?:phan|chuong|bai|muc)\s+",
        r"^\s*\d+\.[\s\t]*",
        r"^\s*\d+\.\d+\.[\s\t]*",
        r"^\s*[a-z]\.\s*",
    ]

    def recursive_split_nq(lines, current_title, current_section_name, pattern_idx):
        def create_doc(content_lines, section_override=None):
            content = "\n".join(content_lines).strip()
            if not content:
                return None
            final_section = section_override if section_override else current_section_name
            full_content = f"{current_title}-{final_section}\nNoi dung: {content}"
            return Document(
                page_content=full_content,
                metadata={"source": book_name, "title": current_title, "section": final_section},
            )

        if pattern_idx >= len(sub_patterns):
            doc = create_doc(lines)
            return [doc] if doc else []

        current_pattern = sub_patterns[pattern_idx]
        splits = []

        for i, line in enumerate(lines):
            line_strip = line.strip()
            clean_strip = normalize_text_for_match(line_strip)
            is_match = bool(re.match(current_pattern, clean_strip))

            if not is_match and pattern_idx == 0:
                if any(clean_strip.upper().startswith(k) for k in ["PHAN ", "CHUONG ", "BAI ", "MUC "]):
                    is_match = True

            if not is_match and pattern_idx == 1:
                if any(clean_strip.startswith(k) for k in ["Phan ", "Chuong ", "Bai ", "Muc "]) and len(clean_strip) < 50:
                    is_match = True

            if is_match:
                splits.append((i, line_strip))

        if not splits:
            if pattern_idx == 0:
                doc = create_doc(lines, section_override="Tong quan")
                return [doc] if doc else []
            else:
                return recursive_split_nq(lines, current_title, current_section_name, pattern_idx + 1)

        results = []
        splits = [(0, None)] + splits + [(len(lines), None)]
        splits.sort(key=lambda x: x[0])

        for j in range(len(splits) - 1):
            start_idx, header = splits[j]
            end_idx = splits[j + 1][0]
            sub_lines = lines[start_idx + 1 : end_idx]
            if not sub_lines:
                continue

            if header is None:
                suffix = " (Dẫn nhập)"
                final_sec = f"{current_section_name}{suffix}" if current_section_name else "Tong quan"
                doc = create_doc(sub_lines, section_override=final_sec)
                if doc:
                    results.append(doc)
            else:
                new_section = header if not current_section_name else f"{current_section_name} > {header}"
                clean_header = normalize_text_for_match(header).upper()
                if any(k in clean_header for k in ["PHAN ", "CHUONG ", "BAI "]):
                    results.extend(recursive_split_nq(sub_lines, current_title, new_section, 0))
                else:
                    content_next = [header] + sub_lines
                    results.extend(recursive_split_nq(content_next, current_title, new_section, pattern_idx + 1))

        return results

    chunks = []

    def process_buffer(lines, title):
        if not lines:
            return
        clean_title = normalize_text_for_match(title).upper()
        if any(k in clean_title for k in no_split_titles):
            full = f"{title}-Tong quan\nNoi dung: " + "\n".join(lines).strip()
            chunks.append(Document(page_content=full, metadata={"source": book_name, "title": title, "section": "Tong quan"}))
            return
        chunks.extend(recursive_split_nq(lines, title, "", pattern_idx=0))

    is_phase_2 = False
    pre_content = []
    active_title = "Tong quan"
    last_processed_title = "Tong quan"
    current_disease_buffer = []

    all_lines = []
    for part in parts:
        all_lines.extend([line.strip() for line in part.split("\n") if line.strip()])

    for i, line in enumerate(all_lines):
        line_strip = line.strip()
        if not line_strip:
            continue
        clean_line = normalize_text_for_match(line_strip)

        if not is_phase_2:
            if marker_start in clean_line.upper() and not re.search(r"\d+$", clean_line):
                is_phase_2 = True
                if pre_content:
                    chunks.append(Document(page_content="PHẦN ĐẦU\n" + "\n".join(pre_content),
                                           metadata={"source": book_name, "title": book_name, "section": "Intro"}))
                active_title = line_strip
                last_processed_title = line_strip
                current_disease_buffer = []
                continue
            pre_content.append(line_strip)
            continue

        is_upper = (clean_line.isupper() and len(clean_line) > 5
                    and not re.match(sub_patterns[0], clean_line)
                    and not any(bad in clean_line.upper() for bad in ["TRANG ", "NXB "]))
        is_appendix = any(k in clean_line.upper() for k in ["PHU PHUONG", "PHU LUC", "BENH AN"])

        if is_upper:
            process_buffer(current_disease_buffer, active_title)
            current_disease_buffer = []
            if is_appendix:
                active_title = f"{last_processed_title} - {line_strip}"
            else:
                active_title = line_strip
                last_processed_title = line_strip
            continue
        current_disease_buffer.append(line_strip)

    process_buffer(current_disease_buffer, active_title)
    return chunks


def split_nhi_khoa() -> List[Document]:
    print("[PROCESS] Processing Nhi Khoa YHCT...")
    file_path = FILES["nhi_khoa"]

    if not os.path.exists(file_path):
        print(f"[WARNING] File not found: {file_path}")
        return []

    raw_text = Docx2txtLoader(file_path).load()[0].page_content

    def is_skip(line: str) -> bool:
        line = line.strip()
        return (not line or line.lower() == "</break>" or re.fullmatch(r"_+", line) is not None)

    lines = [line.strip() for line in raw_text.split("\n") if not is_skip(line)]

    chapter_pattern = re.compile(r"^chuong\s+([ivxlcdm\d]+)", re.I)
    lesson_pattern = re.compile(r"^bai\s+\d+", re.I)
    roman_header = re.compile(r"^[IVXLCDM]+\.\s+.+")
    number_header = re.compile(r"^(\d+(?:\.\d+)*\.)\s+(.+)")

    def parse_number_path(header: str):
        nums = header.split()[0].strip(".")
        return [int(x) for x in nums.split(".")]

    chunks = []
    current_chapter = None
    in_chapter = False
    current_lesson = None
    current_title = None
    section_stack = []
    content_buffer = []

    def flush_buffer():
        if not content_buffer or not section_stack:
            return
        full_section = " > ".join(h for _, h in section_stack)
        leaf_header = section_stack[-1][1]
        chunks.append(
            Document(
                page_content="\n".join([leaf_header] + content_buffer).strip(),
                metadata={
                    "source": "nhi-khoa-y-hoc-co-truyen",
                    "title": current_title,
                    "section": full_section,
                },
            )
        )
        content_buffer.clear()

    for line in lines:
        clean_line = normalize_text_for_match(line)
        chap_match = chapter_pattern.match(clean_line)
        if chap_match:
            flush_buffer()
            current_chapter = chap_match.group(1).upper()
            in_chapter = True
            current_lesson = None
            current_title = None
            section_stack.clear()
            continue

        if not in_chapter:
            continue

        if lesson_pattern.match(clean_line):
            flush_buffer()
            section_stack.clear()
            current_lesson = line
            current_title = None
            continue

        if current_lesson and not current_title and clean_line.isupper():
            current_title = line
            continue

        if not current_title:
            continue

        if roman_header.match(line):
            flush_buffer()
            section_stack = [(1, line)]
            continue

        num_match = number_header.match(line)
        if num_match:
            if current_chapter == "I":
                continue
            flush_buffer()
            level = len(parse_number_path(line)) + 1
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()
            section_stack.append((level, line))
            continue

        if section_stack:
            content_buffer.append(line)

    flush_buffer()
    return chunks


def split_noi_khoa() -> List[Document]:
    print("[PROCESS] Processing Noi Khoa General...")
    file_path = FILES["noi_khoa_general"]

    if not os.path.exists(file_path):
        print(f"[WARNING] File not found: {file_path}")
        return []

    loader = Docx2txtLoader(file_path)
    raw_text = loader.load()[0].page_content
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    # Generalized chapter extraction: All-caps titles that represent diseases/chapters
    sections = []
    current_title = "Tổng quan"
    current_lines = []

    for line in lines:
        clean = normalize_text_for_match(line)
        if (
            clean.isupper()
            and 3 < len(clean) < 80
            and not re.match(r"^(\d+|[IVXLCDM]+)\.", clean)
            and not any(clean.startswith(k) for k in ["CHUONG ", "PHAN ", "MUC ", "BAI "])
        ):
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    sub_patterns = [
        r"^\d+\.\s+[A-Z]",      # 1. ĐẠI CƯƠNG, 2. BIỆN CHÚNG, 3. CÁCH CHỮA
        r"^\d+\.\d+\.\s",       # 1.1., 1.2., 2.1.
        r"^\d+\.\d+\.\d+\.\s",  # 1.1.1.
        r"^[a-z]\.\s",          # a., b.
    ]

    def recursive_split_gen(lines, current_title, current_section_name, pattern_idx):
        if pattern_idx >= len(sub_patterns):
            content = "\n".join(lines).strip()
            if not content:
                return []
            return [
                Document(
                    page_content=content,
                    metadata={
                        "disease": current_title,
                        "title": current_title,
                        "section": current_section_name,
                        "source": "noi-khoa-y-hoc-co-truyen",
                    },
                )
            ]

        current_pattern = sub_patterns[pattern_idx]
        splits = []
        for i, line in enumerate(lines):
            clean_line = normalize_text_for_match(line.strip())
            if re.match(current_pattern, clean_line):
                splits.append((i, line.strip()))

        if not splits:
            return recursive_split_gen(lines, current_title, current_section_name, pattern_idx + 1)

        results = []
        splits = [(0, None)] + splits + [(len(lines), None)]

        for j in range(len(splits) - 1):
            start_idx, header = splits[j]
            end_idx = splits[j + 1][0]
            sub_lines = lines[start_idx + 1 : end_idx]

            if header is None:
                if not sub_lines:
                    continue
                suffix = " (Dẫn nhập)" if " (Dẫn nhập)" not in current_section_name else ""
                new_section_name = f"{current_section_name}{suffix}"
                results.extend(recursive_split_gen(sub_lines, current_title, new_section_name, pattern_idx + 1))
            else:
                new_section_name = f"{current_section_name} > {header}"
                content_for_next_level = [header] + sub_lines
                results.extend(recursive_split_gen(content_for_next_level, current_title, new_section_name, pattern_idx + 1))

        return results

    refined_docs = []
    for title, sec_lines in sections:
        refined_docs.extend(recursive_split_gen(sec_lines, title, title, pattern_idx=0))

    chunks = [d for d in refined_docs if "</break>" not in d.metadata.get("disease", "")]
    return chunks


# Backward-compatible names for older imports.
_looks_like_heading = is_section_heading
_generic_split_text = split_sections
_generic_split_docx = split_docx
_split_with_fallback = split_source
split_text_into_sections = split_sections
split_docx_with_generic_strategy = split_docx
split_builtin_source_with_fallback = split_source
split_noi_khoa_gs_chau = split_gs_chau
split_benh_ngu_quan = split_ngu_quan
split_noi_khoa_general = split_noi_khoa