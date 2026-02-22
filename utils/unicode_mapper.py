#!/usr/bin/env python3
"""
Fix Unicode characters that can trigger MSVC Compiler Error C3872 by
rewriting source/header files with ASCII look-alike replacements.

Usage:
  python fix_c3872.py -i lets_be_rational.cpp -h lets_be_rational.h -oout_dir

The script produces files with the same basename under `out_dir` (created
if necessary). It performs:
 - targeted replacements for Greek letters -> spelled names (θ -> theta)
 - subscript/superscript letters/numbers -> _suffix or plain letters
   (e.g. `bₘₐₓ` -> `b_max`, `sₗ` -> `s_l`)
 - common math symbols in comments -> ascii words or operators
 - fallback transliteration using the Unicode name (e.g. 'ℓ' -> 'ell')

It tries to keep identifiers readable and consistent across .cpp/.h files.
"""

from pathlib import Path
import argparse
import re
import unicodedata

# Explicit mappings for single characters to ASCII look-alikes
CHAR_MAP = {
    # Greek letters -> spelled names (keeps readability in identifiers)
    'θ': 'theta', 'Θ': 'Theta',
    'β': 'beta',  'Β': 'Beta', '𝛽':"ibeta",
    'π': 'pi',    'Π': 'Pi',
    'η': 'eta',
    'τ': 'tau',
    'μ': 'mu',
    'σ': 'sigma', 'Σ': 'Sigma',
    'ϕ': 'phi',   'φ': 'phi', 'Φ': 'Phi',
    'λ': 'lambda','Λ': 'Lambda',
    '√': 'sqrt',
    '∞': 'inf',
    '·': '*',     # middle dot -> star (math)
    '±': '+/-',
    '≤': '<=', '≥': '>=', '≠': '!=', '→': '->', '←': '<-', '↔': '<->',
    '…': '...', '­': '',  # soft-hyphen remove
    # mathematical minus / multiplication signs sometimes appear — map to ASCII
    '×': 'x', '÷': '/', '•': '*', '©':"copyright", '∛':'sqrt3', '⇔':"equiv", "≈":"simeq",
    "⟶":"rlim", "∈":"in", "≡":"eequiv", "ϵ":"iin" , "∂":"partial", "b̄":"hatb", "∫":"int" }

# Subscript and superscript characters mapping to ASCII letters/digits
SUBSCRIPT_MAP = {
    '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
    'ₐ': 'a', 'ₑ': 'e', 'ₒ': 'o', 'ₓ': 'x', 'ₔ': 'ə', 'ₕ': 'h', 'ₖ': 'k', 'ₗ': 'l', 'ₘ': 'm', 'ₙ': 'n',
    'ₚ': 'p', 'ₛ': 's', 'ₜ': 't', '₍': '(', '₎': ')',
    # common modifier letters appearing in code as "superscripts" or "modifier letters"
    'ᵤ': 'u', 'ᵗ': 't', 'ᵇ': 'b', 'ᵉ': 'e',
}

# Build regex character classes
SUBSCRIPT_CHARS = ''.join(re.escape(ch) for ch in SUBSCRIPT_MAP.keys())
SUBSCRIPT_SEQ_RE = re.compile(r'([A-Za-z0-9])([' + SUBSCRIPT_CHARS + r']+)')  # base + subscript seq

# general non-ascii regex
NON_ASCII_RE = re.compile(r'[^\x00-\x7F]')


def map_subscript_sequence(match: re.Match) -> str:
    base = match.group(1)
    seq = match.group(2)
    mapped = ''.join(SUBSCRIPT_MAP.get(ch, '') for ch in seq)
    # prepend underscore for readability/identifier separation
    if mapped:
        return f'{base}_{mapped}'
    return base


def char_replacement(ch: str) -> str:
    """Return ASCII replacement for a single character ch."""
    if ch in CHAR_MAP:
        return CHAR_MAP[ch]
    if ch in SUBSCRIPT_MAP:
        # will be handled by seq regex for insertion of underscore; but if isolated, return mapped
        return SUBSCRIPT_MAP[ch]
    # fallback: try to derive from unicode name
    try:
        name = unicodedata.name(ch).lower()
        # common patterns
        if 'greek' in name and 'letter' in name:
            # take last token as name (e.g. 'greek small letter theta' -> 'theta')
            tokens = name.split()
            for token in reversed(tokens):
                if token.isalpha():
                    return token
        if 'subscript' in name or 'superscript' in name:
            # extract base char word(s)
            tokens = name.replace('-', ' ').split()
            # keep letters and digits
            filtered = ''.join(t for t in tokens if t.isalnum())
            if filtered:
                return filtered
        # fallback to ascii decomposition
        decomp = unicodedata.normalize('NFKD', ch)
        ascii_equiv = ''.join(c for c in decomp if ord(c) < 128)
        if ascii_equiv:
            return ascii_equiv
    except ValueError:
        pass
    # last resort: represent code point in ASCII-friendly form
    raise  RuntimeError( f'Cannot convert {ch} : U+{ord(ch):04X}')


def transform_text(text: str) -> str:
    if text.replace(" ","").startswith('//'):
        return text

    # 1) Replace explicit single-char mappings
    for k, v in CHAR_MAP.items():
        if k in text:
            text = text.replace(k, v)

    # 2) Replace sequences of subscript chars following an identifier base with _mapped
    text = SUBSCRIPT_SEQ_RE.sub(lambda m: map_subscript_sequence(m), text)

    # 3) Replace any remaining non-ascii characters one-by-one using fallback
    if NON_ASCII_RE.search(text):
        parts = []
        for ch in text:
            if ord(ch) < 128:
                parts.append(ch)
            else:
                parts.append(char_replacement(ch))
        text = ''.join(parts)
    return text

class TransformError(RuntimeError):
    def __init__(self, in_path: Path, line_no: int, line_text: str, original_exc: Exception):
        msg = (
            f"Failed to transform {in_path} at line {line_no}.\n"
            f"Line content:\n{line_text.rstrip()}\n"
            f"Original error: {type(original_exc).__name__}: {original_exc}"
        )
        super().__init__(msg)
        self.in_path = in_path
        self.line_no = line_no
        self.line_text = line_text
        self.original_exc = original_exc

def process_file(in_path: Path, out_path: Path):
    # content = in_path.read_text(encoding='utf-8')
    # new = transform_text(content)
    # out_path.write_text(new, encoding='utf-8')
    # print(f'Wrote: {out_path} ({len(content)} -> {len(new)} bytes)')

    out_lines: list[str] = []
    with in_path.open("r", encoding="utf-8", newline="") as fin:
        for line_no, line in enumerate(fin, start=1):
            try:
                new_line = transform_text(line)
            except Exception as e:
                raise TransformError(in_path, line_no, line, e) from e
            out_lines.append(new_line)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(out_lines), encoding="utf-8", newline="")
    print(f"Wrote: {out_path}")


def main():
    p = argparse.ArgumentParser(description='Replace Unicode in source/header to avoid MSVC C3872')
    p.add_argument('-i', '--input', required=True, help='input source file (e.g. lets_be_rational.cpp)')
    # p.add_argument('-h', '--header', required=False, help='optional header file (e.g. lets_be_rational.h)')
    p.add_argument('-o', '--out', required=True, help='output directory for rewritten files')
    args = p.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    in_cpp = Path(args.input)
    if not in_cpp.exists():
        raise SystemExit(f'Input file not found: {in_cpp}')
    out_cpp = outdir / in_cpp.name
    process_file(in_cpp, out_cpp)

    # if args.header:
    #     in_h = Path(args.header)
    #     if not in_h.exists():
    #         raise SystemExit(f'Header file not found: {in_h}')
    #     out_h = outdir / in_h.name
    #     process_file(in_h, out_h)


if __name__ == '__main__':
    import sys
    for f in ["lets_be_rational","normaldistribution","rationalcubic"]:
        sys.argv = ["unicode_mapper", "-i", f"include/{f}.h", "-o", "mapped/include"]
        main()
        sys.argv = ["unicode_mapper", "-i", f"src/{f}.cpp", "-o", "mapped/src"]
        main()