"""Parse uploaded files (HTML/PDF/CSV/Excel) → extract financial data.

For HTML: use regex on text + look for common patterns
For PDF: use pypdf to extract text, then regex
For CSV/Excel: read as DataFrame, look for known column names
"""

import io
import re
import pandas as pd


# ── Pattern library ──────────────────────────────────────────────
PATTERNS = {
    "adj_eps_ttm":     [r"adj\.?\s*eps[^$\d]{0,30}\$?(\d+\.\d+)",
                         r"adjusted\s+eps[^$\d]{0,30}\$?(\d+\.\d+)"],
    "adj_eps_fwd":     [r"(?:2026|2027|fy26|fwd|forward|guidance)[^$\d]{0,40}adj\.?\s*eps[^$\d]{0,20}\$?(\d+\.\d+)",
                         r"adj\.?\s*eps[^$\d]{0,30}\$(\d+\.\d+)\s*[-–]\s*\$?(\d+\.\d+)"],
    "revenue_ttm":     [r"revenue[^$\d]{0,30}\$?([\d,\.]+)\s*[bB]"],
    "revenue_growth":  [r"revenue\s*growth[^%\d]{0,15}([\d\.]+)\s*%",
                         r"\(\+([\d\.]+)\s*%\s*yoy\)"],
    "eps_growth":      [r"(?:eps|earnings)\s*growth[^%\d]{0,15}([\d\.]+)\s*%"],
    "fwd_pe":          [r"(?:fwd|forward)\s*p[/\\]?e[^\d]{0,15}([\d\.]+)\s*[x×]"],
    "pe_multiple":     [r"p[/\\]?e\s*(?:multiple|ratio)?[^\d]{0,15}([\d\.]+)\s*[x×]"],
    "ev_ebitda":       [r"ev[/\\]?ebitda[^\d]{0,15}([\d\.]+)\s*[x×]"],
    "wacc":            [r"wacc[^%\d]{0,15}([\d\.]+)\s*%"],
    "discount_rate":   [r"discount\s*rate[^%\d]{0,15}([\d\.]+)\s*%"],
    "price_target":    [r"(?:price\s*target|consensus\s*pt|pt)[^$\d]{0,15}\$?([\d\.]+)"],
    "current_price":   [r"(?:stock\s*price|current\s*price)[^$\d]{0,15}\$?([\d\.]+)",
                         r"~\$(\d{2,4})"],
    "bear_fv":         [r"bear[^$\d]{0,40}\$([\d,\.]+)(?:\s*[-–]\s*\$?([\d,\.]+))?"],
    "base_fv":         [r"base[^$\d]{0,40}\$([\d,\.]+)(?:\s*[-–]\s*\$?([\d,\.]+))?"],
    "bull_fv":         [r"bull[^$\d]{0,40}\$([\d,\.]+)(?:\s*[-–]\s*\$?([\d,\.]+))?"],
}


def _extract_first_match(text: str, patterns: list[str]) -> float | None:
    """Try each pattern, return first numeric match."""
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            try:
                groups = m.groups()
                nums = [float(g.replace(",", "")) for g in groups if g]
                if not nums:
                    continue
                if len(nums) > 1:
                    return sum(nums) / len(nums)
                return nums[0]
            except ValueError:
                continue
    return None


def parse_text(text: str) -> dict:
    """Apply all regex patterns to a text blob → return extracted fields."""
    out = {}
    for key, patterns in PATTERNS.items():
        v = _extract_first_match(text, patterns)
        if v is not None:
            if key in ("revenue_growth", "eps_growth", "wacc", "discount_rate"):
                if v > 1:
                    out[key] = v / 100
                else:
                    out[key] = v
            else:
                out[key] = v
    return out


def parse_html(content: bytes | str) -> dict:
    """Extract from HTML — strip tags then regex."""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text)
    return parse_text(text)


def parse_pdf(content: bytes) -> dict:
    """Extract from PDF using pypdf."""
    try:
        import pypdf
    except ImportError:
        try:
            import PyPDF2 as pypdf
        except ImportError:
            return {"_error": "Please install pypdf: pip install pypdf"}

    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return parse_text(text)
    except Exception as e:
        return {"_error": f"PDF parse error: {e}"}


def parse_csv(content: bytes) -> dict:
    """Read CSV expecting key/value or column-based layout."""
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        return {"_error": f"CSV error: {e}"}
    return _df_to_overrides(df)


def parse_excel(content: bytes) -> dict:
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        return {"_error": f"Excel error: {e}"}
    return _df_to_overrides(df)


def _df_to_overrides(df: pd.DataFrame) -> dict:
    """Convert DataFrame to override dict.

    Supports:
    1. Two-column key/value: [field, value]
    2. Single-row with named columns
    """
    out = {}
    cols = [c.lower().strip() for c in df.columns]

    if len(df.columns) == 2:
        df.columns = ["field", "value"]
        for _, row in df.iterrows():
            k = str(row["field"]).strip().lower().replace(" ", "_")
            try:
                v = float(row["value"])
                out[k] = v
            except (ValueError, TypeError):
                if pd.notna(row["value"]):
                    out[k] = str(row["value"])
    else:
        for col in df.columns:
            k = col.strip().lower().replace(" ", "_")
            v = df[col].iloc[0] if len(df) > 0 else None
            if pd.isna(v):
                continue
            try:
                out[k] = float(v)
            except (ValueError, TypeError):
                out[k] = str(v)
    return out


def parse_file(filename: str, content: bytes) -> dict:
    """Auto-detect format from filename."""
    name = filename.lower()
    if name.endswith(".html") or name.endswith(".htm"):
        return parse_html(content)
    if name.endswith(".pdf"):
        return parse_pdf(content)
    if name.endswith(".csv"):
        return parse_csv(content)
    if name.endswith((".xlsx", ".xls")):
        return parse_excel(content)
    try:
        return parse_text(content.decode("utf-8", errors="ignore"))
    except Exception:
        return {"_error": "Unsupported file format"}


def template_csv() -> str:
    """Return CSV template for users to fill out manually."""
    return """field,value
adj_eps_ttm,8.97
adj_eps_fwd,10.45
revenue_growth,0.10
eps_growth,0.14
custom_pe,25
custom_wacc,0.09
bear_fv,207
base_fv,270
bull_fv,335
notes,Backlog $30.8B raised guidance
source,Analyst report May 2026
"""
