from typing import List, Dict
import pandas as pd


class BaseValidator:
    def __init__(self, schema: dict, rules: dict):
        self.schema = schema
        self.rules = rules

    def _fix_for_missing(self, field: str) -> str:
        """Prescriptive fix note for a missing value, derived from the schema."""
        spec = self.schema.get("fields", {}).get(field, {})
        hint = spec.get("fix") or spec.get("pattern_message")
        if hint:
            return f"Populate {field}: {hint}"
        domain = self.schema.get("domain", "base")
        return f"Populate {field} (required by the {domain} preset schema)."

    def _fix_for_pattern(self, field: str, spec: dict) -> str:
        """Prescriptive fix note for a format violation."""
        hint = spec.get("fix")
        if hint:
            return hint
        msg = spec.get("pattern_message")
        if msg:
            return f"Reformat to match: {msg}"
        return f"Reformat {field} to match the {self.schema.get('domain', 'base')} preset schema."

    def validate(self, df: pd.DataFrame) -> List[Dict]:
        issues: List[Dict] = []
        required_fields = self.schema.get("required", [])
        for field in required_fields:
            if field not in df.columns:
                issues.append({
                    "row": None,
                    "field": field,
                    "severity": "HIGH",
                    "message": "Missing required column",
                    "fix": self._fix_for_missing(field),
                })
                continue
            missing_mask = df[field].isna() | (df[field].astype(str).str.strip() == "")
            for idx in df[missing_mask].index:
                issues.append({
                    "row": int(idx),
                    "field": field,
                    "severity": "HIGH",
                    "message": "Missing value",
                    "fix": self._fix_for_missing(field),
                })

        for field, spec in self.schema.get("fields", {}).items():
            if field not in df.columns:
                continue
            pattern = spec.get("pattern")
            if pattern:
                mask = df[field].notna() & ~df[field].astype(str).str.replace(r"\.0$", "", regex=True).str.match(pattern)
                for idx in df[mask].index:
                    issues.append({
                        "row": int(idx),
                        "field": field,
                        "severity": spec.get("severity", "MEDIUM"),
                        "message": spec.get("pattern_message", f"Invalid format for {field}"),
                        "fix": self._fix_for_pattern(field, spec),
                    })

        return issues
