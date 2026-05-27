from __future__ import annotations
from pathlib import Path
import os
import json
import re
from typing import Iterator, Tuple, Dict, Any, List, Optional

# -----------------------------------------------------------------------------
# Regexes (robust to AFP styles)
# -----------------------------------------------------------------------------
# Start of a lemma-like statement; allow names, locales, attributes.
LEMMA_START_RE = re.compile(
    r'^\s*(?:lemma|theorem|proposition|corollary)\b', re.UNICODE
)
# End markers for a block header / one-liner proofs.
QED_RE   = re.compile(r'^\s*qed\b', re.UNICODE)
BY_RE    = re.compile(r'^\s*by\b', re.UNICODE)
PROOF_RE = re.compile(r'^\s*proof\b', re.UNICODE)

# Theory header bits
IMPORTS_RE    = re.compile(r'^\s*imports\s+(.*)$', re.UNICODE)
THEORY_HDR_RE = re.compile(r'^\s*theory\s+([A-Za-z_][A-Za-z0-9_]*)\b', re.UNICODE)

# Identifiers, defs
ID_RE   = re.compile(r"\b([A-Za-z_][A-Za-z0-9_']*)\b", re.UNICODE)
DEF_RE  = re.compile(r"\b([A-Za-z_][A-Za-z0-9_']*)_def\b", re.UNICODE)

# Quoted formulas (ASCII quotes) and cartouches (‹ … ›)
QUOTE_RE     = re.compile(r'"([^"]+)"', re.UNICODE | re.DOTALL)
CARTOUCHE_RE = re.compile(r'‹(.*?)›', re.UNICODE | re.DOTALL)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _expand_dir(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))

def _theory_header_info(thy_text: str) -> Dict[str, Any]:
    theory = None
    imports: List[str] = []
    for line in thy_text.splitlines()[:200]:
        m1 = THEORY_HDR_RE.match(line)
        if m1 and theory is None:
            theory = m1.group(1)
        m2 = IMPORTS_RE.match(line)
        if m2:
            # crude split on whitespace; filter 'begin'
            imports += [tok.strip() for tok in m2.group(1).split()
                        if tok.strip() and tok.strip() != "begin"]
    return {"theory": theory, "imports": imports}

def _premises_from_goal(stmt: str) -> Optional[str]:
    # Very light heuristic: text before the last '⟹' or inside ⟦ ⟧
    if "⟹" in stmt:
        try:
            return stmt.rsplit("⟹", 1)[0].strip()
        except Exception:
            return None
    if "⟦" in stmt and "⟧" in stmt:
        try:
            return stmt.split("⟦", 1)[1].split("⟧", 1)[0].strip()
        except Exception:
            return None
    return None

def _defs_and_names(block: str) -> Dict[str, Any]:
    defs = sorted(set(DEF_RE.findall(block)))
    names = sorted(set(ID_RE.findall(block)))
    return {"defs_in_block": defs, "names_in_block": names}

def _first_quoted_or_cartouche(text: str) -> Optional[str]:
    # Prefer the LAST quote/cartouche in the header (often the "shows" formula)
    qs = QUOTE_RE.findall(text)
    cs = CARTOUCHE_RE.findall(text)
    seq = []
    if qs: seq.extend(qs)
    if cs: seq.extend(cs)
    if seq:
        return seq[-1].strip()
    return None

def _header_region(lines: List[str], start: int, end: int) -> str:
    """
    Return the lemma header region (from 'start' up to the first 'proof'/'by'
    line or up to 'end' if not present). This keeps assumptions/shows text.
    """
    j = start + 1
    while j < end:
        L = lines[j]
        if PROOF_RE.match(L) or BY_RE.match(L) or QED_RE.match(L):
            break
        # Stop header if we hit an empty line followed by indented proof text.
        if not L.strip() and j + 1 < end and lines[j + 1].strip().startswith(("-", "have", "show", "fix", "assume")):
            break
        j += 1
    return "\n".join(lines[start:j])

def _outline_from_header(header_line: str, goal: str) -> str:
    # If the header itself carries a proof mode (rare), keep it; else add minimal skeleton.
    if PROOF_RE.search(header_line):
        proof_mode = header_line.strip()
        return f'lemma "{goal}"\n{proof_mode}\n  sorry\nqed\n'
    return f'lemma "{goal}"\nproof\n  sorry\nqed\n'

# -----------------------------------------------------------------------------
# Main iterator
# -----------------------------------------------------------------------------

# F29c: skip lemmas inside locale / context / instantiation / overloading /
# interpretation blocks, where the goal depends on `fixes` / `assumes` clauses
# from the enclosing block. When extracted standalone they're typically
# non-theorems under `imports Main` — they need their locale's hypotheses
# in scope. Top-level (theory-body) lemmas are unaffected.
_BLOCK_OPEN_KW_RE = re.compile(
    r'^\s*(?P<kind>locale|context|sublocale|interpretation|instantiation|'
    r'overloading|instance|notepad|experiment|bundle|class)\b'
    r'\s*(?P<name>[A-Za-z_][A-Za-z0-9_\']*)?',
    re.UNICODE,
)
_BLOCK_BEGIN_ON_LINE_RE = re.compile(r'\bbegin\b')
_BARE_BEGIN_RE = re.compile(r'^\s*begin\b')
_BARE_END_RE = re.compile(r'^\s*end\b')


def _compute_block_stacks(lines: List[str]) -> List[List[Tuple[str, str]]]:
    """For each line, return the stack of enclosing block openings as
    [(kind, name), ...]. Theory body itself is the empty stack. Used both for
    F29c depth-tracking (depth = len(stack)) and F29-Approach-A class-lift
    (need to know the innermost class/context name to add the right
    `'a::<class>` type constraint when lifting a locale-bound lemma)."""
    stacks: List[List[Tuple[str, str]]] = []
    stack: List[Tuple[str, str]] = []
    pending: Optional[Tuple[str, str]] = None
    for raw in lines:
        m = _BLOCK_OPEN_KW_RE.match(raw)
        if m:
            kind = m.group('kind')
            name = m.group('name') or '<anon>'
            entry = (kind, name)
            if _BLOCK_BEGIN_ON_LINE_RE.search(raw):
                stack.append(entry)
                pending = None
            else:
                # The new opener replaces any previously-pending one; the older
                # locale/class declaration had no body before this one started.
                pending = entry
        elif _BARE_BEGIN_RE.match(raw):
            if pending is not None:
                stack.append(pending)
                pending = None
            # else: theory body's begin, don't push.
        elif _BARE_END_RE.match(raw):
            if stack:
                stack.pop()
            pending = None
        stacks.append(list(stack))
    return stacks


def _compute_block_depths(lines: List[str]) -> List[int]:
    """Backwards-compat shim — depth at line i is just len(stack at line i)."""
    return [len(s) for s in _compute_block_stacks(lines)]


# F29-Approach-A: typeclass classes whose lemmas can be safely lifted to
# top-level by annotating the first free variable with `'a::<class>`. We
# bootstrap from the fact that any `class X` declaration in HOL defines a
# typeclass — collect those names per-file and use them to decide whether a
# `context X begin` block is also a typeclass scope (vs an arbitrary locale
# instance, which we still drop).
_CLASS_DECL_RE = re.compile(
    r'^\s*class\s+([A-Za-z_][A-Za-z0-9_\']*)\b', re.UNICODE)


def _collect_classes_in_file(lines: List[str]) -> set:
    """Return the set of typeclass names declared via `class X` in this file."""
    out: set = set()
    for raw in lines:
        m = _CLASS_DECL_RE.match(raw)
        if m:
            out.add(m.group(1))
    return out


# First-free-variable regex used by the typeclass lift. Restricted to 1-2
# character lowercase identifiers (the conventional HOL free-variable shape:
# a, b, x, y, xs, ys, f, g, etc.) so we annotate value variables, not
# function/constant names. Annotating `(a::'a::group)` propagates the
# typeclass constraint via type inference to any operator that takes a as
# an argument (including the class's own methods); annotating `(mult::'a::group)`
# would mis-constrain mult to a value type and the goal won't typecheck.
_F29A2_VAR_RE = re.compile(r"\b([a-z][a-z']?)\b")
_F29A2_VAR_SKIP = frozenset({
    "if", "in", "is", "of", "on", "do", "to", "as", "or",
    "by", "or", "an", "no", "i'", "x'",
})


# Match an unclosed `\<...` marker ending at the current position — used by
# the lift to detect when a candidate identifier falls inside an Isabelle
# unicode symbol like `\<le>`, `\<top>`, `\<forall>`, etc. Annotating those
# produces broken markup: `\<(le::'a::class)>` won't parse.
_OPEN_ISABELLE_MARKER_RE = re.compile(r'\\<[^>]*$')


def _lift_with_typeclass(stmt: str, class_name: str) -> Optional[str]:
    """Approach A: annotate the first free lowercase variable in `stmt` with
    `(<var>::'a::<class_name>)`. Isabelle's type inference propagates the
    typeclass constraint from this single annotation throughout the goal,
    bringing the class's methods and axioms into scope. Returns None if no
    suitable free variable found."""
    for m in _F29A2_VAR_RE.finditer(stmt):
        var = m.group(1)
        if var in _F29A2_VAR_SKIP:
            continue
        before = stmt[:m.start()]
        # Don't annotate vars inside an Isabelle unicode marker — e.g. the
        # `le` in `\<le>`, the `or` in `\<or>`, the `fa` in `\<forall>`.
        # Replacing those would mangle the marker into unparseable syntax.
        if _OPEN_ISABELLE_MARKER_RE.search(before):
            continue
        # Don't annotate the content of a single-char subscript / superscript
        # marker — e.g. the `f` in `Gcd\<^sub>f\<^sub>i\<^sub>n` (a `Gcd_fin`
        # notation) — wrapping it as `(f::class)` makes the subscript apply
        # only to `(` and breaks the visual / parsing structure.
        if (before.endswith("\\<^sub>") or
                before.endswith("\\<^sup>") or
                before.endswith("\\<^bsub>") or
                before.endswith("\\<^isub>") or
                before.endswith("\\<^isup>")):
            continue
        # Don't annotate vars that already have a type annotation immediately
        # following them — avoids producing `((a::'a::ord)::'a::group)`.
        after = stmt[m.end():m.end() + 3]
        if after.startswith("::"):
            continue
        return re.sub(
            r'\b' + re.escape(var) + r'\b',
            f"({var}::'a::{class_name})",
            stmt, count=1,
        )
    return None


def iter_lemmas_with_proofs(thy_text: str) -> Iterator[Tuple[str, str, str]]:
    """
    Yields (full_block_text, lemma_stmt, outline_with_sorry) from a .thy.
    Robust to:
      - named lemmas ('lemma foo:')
      - cartouches (‹ … ›) and ASCII quotes
      - 'shows' on later lines
      - one-liner 'by …' proofs (no 'qed')

    F29c: skips lemmas inside locale/context/instantiation/overloading blocks
    since they typically depend on `fixes`/`assumes` clauses that aren't
    available when the goal is re-stated standalone under `imports Main`.

    F29-Approach-A: for `class X begin` and `context X begin` blocks where X
    is a typeclass declared earlier in the same file, lift the lemma by
    annotating its first free variable with `('a::X)`. Isabelle's type
    inference then provides the class's methods and axioms standalone.
    """
    lines = thy_text.splitlines()
    stacks = _compute_block_stacks(lines)
    classes_in_file = _collect_classes_in_file(lines)
    n = len(lines)
    i = 0
    while i < n:
        L = lines[i]
        if not LEMMA_START_RE.match(L):
            i += 1
            continue

        # F29c + F29-Approach-A: decide whether to skip, lift, or pass through.
        lift_class: Optional[str] = None
        if stacks[i]:
            innermost_kind, innermost_name = stacks[i][-1]
            # Lift candidate: innermost block is `class X` (always safe — by
            # definition X is a typeclass) OR `context X` where X has been
            # declared as a `class` in this same file (so we know it's a
            # typeclass context, not a locale instance).
            if innermost_kind == 'class':
                lift_class = innermost_name
            elif innermost_kind == 'context' and innermost_name in classes_in_file:
                lift_class = innermost_name
            else:
                # locale / instantiation / sublocale / etc. — F29c drop.
                i += 1
                continue

        # Find end of this lemma block: next lemma start OR explicit 'qed'
        j = i + 1
        while j < n:
            if LEMMA_START_RE.match(lines[j]):
                break
            if QED_RE.match(lines[j]):
                j += 1  # include qed
                break
            # If it's a one-liner 'by ...', consider this line as block end
            if BY_RE.match(lines[j]) and i + 1 == j:
                j += 1
                break
            j += 1

        block = "\n".join(lines[i:j])  # full lemma region
        header = _header_region(lines, i, j)
        stmt = _first_quoted_or_cartouche(header)

        if not stmt:
            # Fallback: scan whole block for a quoted formula (last one wins)
            stmt = _first_quoted_or_cartouche(block)

        if stmt:
            # F29-Approach-A: if we identified an enclosing typeclass earlier,
            # try to lift by annotating the first free var. If lifting fails
            # (no suitable free var), drop the lemma — emitting an unlifted
            # locale-resident statement would be a non-theorem in `imports Main`.
            if lift_class is not None:
                lifted = _lift_with_typeclass(stmt, lift_class)
                if lifted is None:
                    i = max(j, i + 1)
                    continue
                stmt = lifted
            outline = _outline_from_header(header.splitlines()[0] if header else lines[i], stmt)
            yield (block, stmt, outline)

        i = max(j, i + 1)

# -----------------------------------------------------------------------------
# Public miners
# -----------------------------------------------------------------------------

def mine_afp_corpus(src_dir: str, out_pairs: str) -> None:
    """
    Walk AFP sources, emit JSONL with {"goal": ..., "outline": ...}
    (kept for backward compatibility with existing scripts)
    """
    src = _expand_dir(src_dir)
    out_path = Path(out_pairs)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for thy in src.rglob("*.thy"):
            try:
                text = thy.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for _block, stmt, outline in iter_lemmas_with_proofs(text):
                try:
                    f.write(json.dumps({"goal": stmt, "outline": outline}, ensure_ascii=False) + "\n")
                    n += 1
                except Exception:
                    continue
    print(f"Wrote {n} pairs to {out_pairs}")

def mine_afp_corpus_rich(src_dir: str, out_jsonl: str) -> None:
    """
    Walk AFP sources and emit JSONL with:
      {"goal":..., "outline":..., "theory":..., "imports":[...], "premises":..., "defs_in_block":[...], "names_in_block":[...]}
    NOTE: still keeps 'goal' and 'outline' keys for compatibility.
    """
    src = _expand_dir(src_dir)
    out_path = Path(out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    for thy in src.rglob("*.thy"):
        try:
            text = thy.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hdr = _theory_header_info(text)
        recs_written = 0
        with out_path.open("a", encoding="utf-8") as f:
            for block, stmt, outline in iter_lemmas_with_proofs(text):
                rec: Dict[str, Any] = {
                    "goal": stmt,
                    "outline": outline,
                    "theory": hdr.get("theory"),
                    "imports": hdr.get("imports", []),
                    "premises": _premises_from_goal(stmt),
                }
                rec.update(_defs_and_names(block))
                try:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
                    recs_written += 1
                except Exception:
                    continue
        # Optional: simple progress for big trees (comment out if noisy)
        # print(f"{thy}: {recs_written} lemmas")
    print(f"Wrote {n} rich records to {out_jsonl}")
