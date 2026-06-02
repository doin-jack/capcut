"""단어 리스트를 자막 라인 그룹으로 묶는 알고리즘."""
import re
from dataclasses import dataclass, field

from core.srt_writer import Subtitle


@dataclass
class Word:
    """단어 단위 인식 결과."""
    start: float
    end: float
    text: str


# 문장 종결 부호 (마지막 글자에 위치)
_SENTENCE_ENDINGS = (".", "?", "!", "~")

# 한국어 의미 단위 경계 후보: 연결 어미 + 격조사 + 종결 보조사
# 단어 끝(부호 제거 후)이 이 패턴들로 끝나면 분할 후보
_CLAUSE_ENDING_RE = re.compile(
    r"(?:"
    # 연결 어미
    r"어서|아서|여서|해서|되서|와서|가서|봐서|"
    r"하고|되고|이고|"
    r"으며|하며|되며|"
    r"으면서|하면서|되면서|면서|"
    r"으면|하면|되면|"
    r"지만|"
    r"는데|은데|인데|ㄴ데|"
    r"으니까|니까|"
    r"으므로|므로|"
    r"으나|"
    r"거나|"
    r"다가|"
    r"도록|"
    # 격조사/보조사 (장소·방향·범위 등 절 경계 힌트)
    r"에서|에게|으로|부터|까지|에는|에도|에만|"
    # 인용·명사화 어미
    r"이라고|라고|"
    r"는지|은지|ㄴ지"
    r")$"
)


def split_by_sentence_ending(words: list[Word]) -> list[list[Word]]:
    """단어 리스트를 문장 종결 부호 기준으로 그룹화한다.

    종결 부호는 그룹의 마지막 단어에 포함된다.
    """
    if not words:
        return []
    groups: list[list[Word]] = []
    current: list[Word] = []
    for word in words:
        current.append(word)
        # 마지막 글자가 종결 부호인지 확인 (공백 제거 후)
        stripped = word.text.rstrip()
        if stripped and stripped[-1] in _SENTENCE_ENDINGS:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def split_by_korean_clause(
    words: list[Word],
    min_clause_chars: int = 14,
) -> list[list[Word]]:
    """한국어 연결 어미 경계에서 분할한다.

    어미 매칭된 단어의 직후를 경계로 삼되, 누적 글자수가 min_clause_chars 이상일
    때만 분할한다(너무 잘게 쪼개지지 않도록).
    """
    if not words:
        return []
    groups: list[list[Word]] = []
    current: list[Word] = []
    current_chars = 0
    for word in words:
        current.append(word)
        current_chars += len(word.text)
        stripped = word.text.rstrip(",.?!~ ")
        if (
            stripped
            and len(stripped) >= 2
            and _CLAUSE_ENDING_RE.search(stripped)
            and current_chars >= min_clause_chars
        ):
            groups.append(current)
            current = []
            current_chars = 0
    if current:
        groups.append(current)
    return groups


def split_by_pause(words: list[Word], pause_threshold: float = 0.7) -> list[list[Word]]:
    """단어 사이 간격이 임계값 이상이면 분할한다."""
    if not words:
        return []
    groups: list[list[Word]] = []
    current: list[Word] = [words[0]]
    for prev, curr in zip(words, words[1:]):
        gap = curr.start - prev.end
        if gap >= pause_threshold:
            groups.append(current)
            current = [curr]
        else:
            current.append(curr)
    groups.append(current)
    return groups


def split_by_max_length(
    words: list[Word],
    max_chars: int = 42,
    max_duration: float = 6.0,
) -> list[list[Word]]:
    """최대 글자수 또는 최대 길이(초) 초과 시 분할한다.

    글자수는 공백 제외 단어 텍스트 합계 기준.
    """
    if not words:
        return []
    groups: list[list[Word]] = []
    current: list[Word] = []
    current_chars = 0
    group_start = words[0].start
    for word in words:
        added_chars = len(word.text)
        projected_chars = current_chars + added_chars
        projected_duration = word.end - group_start if current else 0
        # 빈 그룹이 아니고, 추가하면 한계 초과 시 분할
        if current and (projected_chars > max_chars or projected_duration > max_duration):
            groups.append(current)
            current = [word]
            current_chars = added_chars
            group_start = word.start
        else:
            current.append(word)
            current_chars = projected_chars
            if len(current) == 1:
                group_start = word.start
    if current:
        groups.append(current)
    return groups


def _group_duration(group: list[Word]) -> float:
    return group[-1].end - group[0].start


def _group_chars(group: list[Word]) -> int:
    return sum(len(w.text) for w in group)


def _ends_with_sentence_terminator(group: list[Word]) -> bool:
    """그룹의 마지막 단어가 문장 종결 부호로 끝나는지 확인."""
    if not group:
        return False
    stripped = group[-1].text.rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_ENDINGS


# 종결 부호 경계에서 병합을 막을 최소 그룹 간 간격(초)
_SENTENCE_BOUNDARY_GAP = 0.3


def _should_block_merge(prev_group: list[Word], next_group: list[Word]) -> bool:
    """두 그룹 사이가 명확한 문장 경계(종결 부호 + 충분한 호흡)인지 확인."""
    if not prev_group or not next_group:
        return False
    if not _ends_with_sentence_terminator(prev_group):
        return False
    gap = next_group[0].start - prev_group[-1].end
    return gap >= _SENTENCE_BOUNDARY_GAP


def merge_short_groups(
    groups: list[list[Word]],
    min_duration: float = 0.8,
    max_chars: int = 42,
    max_duration: float = 6.0,
) -> list[list[Word]]:
    """짧은(min_duration 미만) 그룹을 인접 그룹과 병합한다.

    병합 시 max_chars/max_duration을 위반하지 않을 때만 수행.
    종결 부호 + 호흡으로 명확히 분리된 문장 경계는 병합하지 않는다.
    """
    if not groups:
        return []
    result = [list(g) for g in groups]
    i = 0
    while i < len(result):
        if _group_duration(result[i]) >= min_duration:
            i += 1
            continue
        # 다음 그룹과 병합 시도 (명확한 문장 경계가 아닐 때만)
        if i + 1 < len(result) and not _should_block_merge(result[i], result[i + 1]):
            combined = result[i] + result[i + 1]
            new_duration = combined[-1].end - combined[0].start
            if _group_chars(combined) <= max_chars and new_duration <= max_duration:
                result[i] = combined
                del result[i + 1]
                continue
        # 다음과 못 합치면 이전과 시도 (명확한 문장 경계가 아닐 때만)
        if i > 0 and not _should_block_merge(result[i - 1], result[i]):
            combined = result[i - 1] + result[i]
            new_duration = combined[-1].end - combined[0].start
            if _group_chars(combined) <= max_chars and new_duration <= max_duration:
                result[i - 1] = combined
                del result[i]
                continue
        i += 1
    return result


def fix_overlaps(subtitles: list[Subtitle]) -> list[Subtitle]:
    """자막 간 시간 겹침을 보정한다. 겹치면 이전 자막의 end = 다음 start - 0.01."""
    fixed = [Subtitle(s.index, s.start, s.end, s.text) for s in subtitles]
    for prev, curr in zip(fixed, fixed[1:]):
        if prev.end > curr.start:
            prev.end = round(curr.start - 0.01, 3)
            if prev.end < prev.start:
                prev.end = prev.start
    return fixed


def wrap_text(text: str, max_chars_per_line: int = 21) -> str:
    """텍스트를 최대 글자수 기준으로 줄바꿈한다 (최대 2줄)."""
    if len(text) <= max_chars_per_line:
        return text
    # 공백 기준 분할 시도
    space_idx = text.rfind(" ", 0, max_chars_per_line + 1)
    if space_idx > 0:
        line1 = text[:space_idx]
        line2 = text[space_idx + 1:]
    else:
        # 공백 없으면 강제 분할
        line1 = text[:max_chars_per_line]
        line2 = text[max_chars_per_line:]
    # 둘째 줄이 너무 길면 잘림 (강제 2줄)
    if len(line2) > max_chars_per_line:
        line2 = line2[:max_chars_per_line]
    return f"{line1}\n{line2}"


def filter_hallucinations(groups: list[list[Word]]) -> list[list[Word]]:
    """동일 텍스트가 3회 이상 연속 반복되면 첫 1회만 남기고 나머지 제거.

    2회까지의 연속 반복은 환각으로 간주하지 않고 그대로 유지한다.
    """
    if not groups:
        return []
    texts = [" ".join(w.text for w in g).strip() for g in groups]
    n = len(groups)
    # 각 인덱스가 속한 연속 동일 텍스트 run의 (시작 인덱스, run 길이) 계산
    run_start = [0] * n
    run_length = [0] * n
    i = 0
    while i < n:
        j = i
        while j < n and texts[j] == texts[i]:
            j += 1
        length = j - i
        for k in range(i, j):
            run_start[k] = i
            run_length[k] = length
        i = j
    result: list[list[Word]] = []
    for idx, group in enumerate(groups):
        if run_length[idx] >= 3:
            # run의 첫 번째 항목만 유지
            if idx == run_start[idx]:
                result.append(group)
            # 그 외는 폐기
        else:
            result.append(group)
    return result


@dataclass
class SegmenterOptions:
    pause_threshold: float = 0.4
    max_chars: int = 16
    max_duration: float = 4.0
    min_duration: float = 0.4
    end_buffer: float = 0.05
    max_chars_per_line: int = 999  # 무조건 한 줄 (줄바꿈 비활성화)
    min_clause_chars: int = 6


def _flatten_text(group: list[Word]) -> str:
    """단어 그룹을 공백으로 연결한 텍스트로."""
    parts = [w.text for w in group]
    # 단어가 종결 부호 단독("." 같은)일 경우 공백 없이 붙이기
    text = ""
    for p in parts:
        if p in (".", "?", "!", "~", ",") and text:
            text += p
        elif text:
            text += " " + p
        else:
            text = p
    return text


def segment_words_to_subtitles(
    words: list[Word],
    options: SegmenterOptions,
) -> list[Subtitle]:
    """단어 리스트 → 자막 라인 리스트 (전체 파이프라인)."""
    if not words:
        return []

    # 1단계: 문장 종결 부호 분할
    groups: list[list[Word]] = []
    for sent_group in split_by_sentence_ending(words):
        # 2단계: 한국어 연결 어미 경계 분할 (의미 단위)
        for clause_group in split_by_korean_clause(sent_group, options.min_clause_chars):
            # 3단계: 호흡 분할
            for pause_group in split_by_pause(clause_group, options.pause_threshold):
                # 4단계: 최대 길이 분할
                groups.extend(
                    split_by_max_length(pause_group, options.max_chars, options.max_duration)
                )

    # 4단계: 환각 필터
    groups = filter_hallucinations(groups)

    # 5단계: 짧은 그룹 병합
    groups = merge_short_groups(
        groups, options.min_duration, options.max_chars, options.max_duration
    )

    # 6단계: Subtitle로 변환 + 줄바꿈 + end 버퍼
    subtitles: list[Subtitle] = []
    for idx, group in enumerate(groups, start=1):
        if not group:
            continue
        text = _flatten_text(group)
        text = wrap_text(text, options.max_chars_per_line)
        subtitles.append(
            Subtitle(
                index=idx,
                start=group[0].start,
                end=group[-1].end + options.end_buffer,
                text=text,
            )
        )

    # 7단계: 겹침 보정
    subtitles = fix_overlaps(subtitles)
    # 인덱스 재부여 (병합/제거 후 일관성)
    for new_idx, sub in enumerate(subtitles, start=1):
        sub.index = new_idx
    return subtitles
