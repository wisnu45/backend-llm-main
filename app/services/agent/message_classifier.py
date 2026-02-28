"""
Message classification and routing service for fast message categorization.
Handles small talk detection, ambiguous message identification, and routing decisions.
"""
import re
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger('agent.message_classifier')

# Pre-compiled patterns for quick message classification
SMALL_TALK_PATTERNS = {
    "greeting": [
        r"^(hai|halo|hello|hi|yo)$",
        r"^selamat (pagi|siang|sore|malam)$",
        r"^(pagi|siang|sore|malam)$",
        r"^ass?alam(u'?alaikum)?$",
    ],
    "thanks": [
        r"terima kasih", r"makasih", r"makasi", r"thanks", r"thank you", r"thx", r"trims", r"trimakasih",
    ],
    "bye": [
        r"bye", r"good ?bye", r"dadah", r"daa?h", r"sampai jumpa", r"see you", r"selamat tinggal",
    ],
}

AFFIRMATION_WORDS = {
    "ok", "oke", "okey", "okelah", "sip", "siap", "baik", "noted", "ya", "iya", "yup",
    "betul", "benar", "siipp", "okeee",
}

QUESTION_WORDS = {
    "apa", "siapa", "kapan", "dimana", "di mana", "bagaimana", "kenapa", "mengapa", "berapa",
    "what", "who", "when", "where", "how", "why",
}

ACTION_VERBS = {
    "cari", "jelaskan", "terangkan", "rangkuman", "ringkas", "bandingkan", "buat", "tulis",
    "berikan", "sebutkan", "hitung", "analisa", "analisis", "tunjukkan", "lihat", "definisikan",
    "explain", "summarize", "compare", "write", "list", "calculate", "analyze", "show", "find",
}

AMBIGUOUS_FILLERS = {"lanjut", "lanjutkan", "detail", "detailnya", "gimana", "bagaimana?", "tolong"}

SMALL_TALK_REPLIES = {
    "greeting": "Halo! Vita di sini—ada yang bisa Vita bantu cari?",
    "thanks": "Sama-sama! Senang bisa membantu; kalau ada yang lain, panggil Vita ya.",
    "bye": "Sampai jumpa, dan bila butuh bantuan lagi tinggal panggil Vita.",
    "affirmation": "Siap, Vita lanjut bantu—ada lagi yang ingin Anda cari?",
}

ACTION_INTENT_WORDS = re.compile(
    r"\b("
    # verbs of state & action
    r"sudah|akan|telah|bekerja|punya|dapat|ingin|mau|"
    r"bertambah|berkurang|menjadi|menyuruh|menjelaskan|"
    r"mengapa|kenapa|bagaimana|apa|"
    # request / command verbs
    r"tolong|harap|harapannya|mohon|iz[i|j]n(?:kan)?|ajukan|"
    r"ajukanlah|buat|cari|tulis|sebutkan|jelaskan|lihat|"
    r"perlihatkan|berikan|tampilkan|"
    # contextual nouns indicating HR/work intent
    r"cuti|sakit|iz[i|j]in sakit|iz[i|j]in cuti|absen|masuk|keluar|hadir|tidak hadir|"
    # english support
    r"please|help|find|show|calculate|summarize|explain|define|request|submit"
    r")\b"
)

DEFAULT_REPLY = "Halo! Vita di sini—ada yang bisa Vita bantu cari?"

class MessageClassifier:
    """
    Handles fast message classification for routing and response optimization.
    """

    def __init__(self):
        """Initialize the message classifier."""
        pass

    def normalize_text(self, text: str) -> str:
        """Return lowercase text without extra spaces or zero-width chars."""
        t = re.sub(r"\s+", " ", str(text).strip().lower())
        # Remove zero-width characters if needed
        return re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)

    def classify_message(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Cheap message routing:
        - Detect small talk (greetings/thanks/bye/affirmation)
        - Detect ambiguous very-short messages without meaningful verbs
        
        Returns:
            Tuple[str, Optional[str]]: (route, subtype)
            route in {"small_talk", "ambiguous", "rag"}
            subtype for small_talk in {"greeting", "thanks", "bye", "affirmation"}
        """
        t = self.normalize_text(text)
        tokens = re.findall(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9']+", t)
        wc = len(tokens)

        # Check contains questions or number, Don't classify
        if "?" in t or re.search(r"\d", t):
            return ("rag", None)

        # Check sentence contains action words, Don't classify
        if wc > 3 and ACTION_INTENT_WORDS.search(t):
            return ("rag", None)

        # Check for small talk patterns
        for subtype, patterns in SMALL_TALK_PATTERNS.items():
            if any(re.search(p, t) for p in patterns):
                return ("small_talk", subtype)

        # Check for affirmation words
        if wc <= 3 and (t in AFFIRMATION_WORDS or any(tok in AFFIRMATION_WORDS for tok in tokens)):
            return ("small_talk", "affirmation")

        # Check for ambiguous short messages
        if wc <= 4:
            has_q = any(qw in t for qw in QUESTION_WORDS)
            has_v = any(av in t for av in ACTION_VERBS)
            if (not has_v and (not has_q or wc <= 2)) or any(f in t for f in AMBIGUOUS_FILLERS):
                return ("ambiguous", None)

        return ("rag", None)

    def fast_classify(self, question: str) -> Tuple[str, Optional[str]]:
        """
        Fast classification method that wraps classify_message for compatibility.
        Returns (route_type, route_subtype) tuple.
        """
        return self.classify_message(question)

    def small_talk_reply(self, subtype: Optional[str]) -> str:
        """Return friendly canned responses for small talk."""
        return SMALL_TALK_REPLIES.get(subtype, DEFAULT_REPLY)

    def get_small_talk_reply(self, subtype: Optional[str]) -> str:
        """Return friendly canned responses for small talk."""
        return SMALL_TALK_REPLIES.get(subtype, DEFAULT_REPLY)

    def wants_explanation(self, text: str) -> bool:
        """Check if the user wants a detailed explanation."""
        try:
            t = (text or "").lower()
            explain_markers = [
                "jelaskan", "penjelasan", "terangkan", "detail", "lebih detail",
                "kenapa", "mengapa", "alasannya", "bagaimana caranya", "explain",
                "why", "how", "please explain", "beri penjelasan"
            ]
            return any(m in t for m in explain_markers)
        except Exception:
            return False

    @staticmethod
    def extract_arithmetic_expression(text: str) -> Optional[str]:
        """
        Ekstraksi ekspresi aritmatika dari bahasa alami (ID/EN).
        Tidak menggunakan LLM, hanya rule-based semantic + symbol filter.
        Mengembalikan string ekspresi bersih atau None jika bukan kalkulasi sederhana.
        """
        if not text or not isinstance(text, str):
            return None

        raw = text.strip().lower()

        # --- STEP 1: Prefilter semantik ringan ---
        # Pertanyaan matematika umumnya mengandung kata "berapa", "hasil", "total", dsb.
        math_hints = [
            "berapa", "hasil", "jumlah", "total", "sama dengan", "selisih", "kurang", "tambah",
            "kali", "bagi", "pangkat", "mod", "persen", "convert", "konversi", "ubah"
        ]
        if not any(k in raw for k in math_hints) and not re.search(r"\d", raw):
            return None

        # --- STEP 2: Pastikan ada angka dan operator potensial ---
        if not re.search(r"\d", raw):
            return None

        if not (re.search(r"[+\-*/x×:]", raw) or any(k in raw for k in math_hints)):
            return None

        # --- STEP 3: Normalisasi operator bahasa Indonesia & tipografis ---
        norm = raw
        replacements = [
            (r"\b(dikali|kali)\b", "*"),
            (r"\b(ditambah|tambah|plus)\b", "+"),
            (r"\b(dikurang|kurang|minus)\b", "-"),
            (r"\b(dibagi|bagi|per)\b", "/"),
            (r"\b(mod|modulo)\b", "%"),
            (r"\b(pangkat|^)\b", "**"),
        ]
        for pat, repl in replacements:
            norm = re.sub(pat, repl, norm)

        norm = norm.replace("×", "*").replace("x", "*").replace(":", "/")
        norm = norm.replace("^", "**")

        # --- STEP 4: Bersihkan kata-kata filler ---
        fillers = [
            "berapa", "hasil", "jumlah", "adalah", "berapa sih", "sama dengan",
            "tolong", "please", "mohon", "=", "?"
        ]
        for f in fillers:
            norm = norm.replace(f, " ")

        # --- STEP 5: Konversi angka dengan koma menjadi desimal ---
        norm = re.sub(r"(\d),(\d)", r"\1.\2", norm)

        # --- STEP 6: Hilangkan karakter non-angka/operator ---
        allowed = re.sub(r"[^0-9+\-*/().%\s]", " ", norm)
        allowed = re.sub(r"\s+", " ", allowed).strip()

        # --- STEP 7: Ekstraksi ekspresi aritmatika utama ---
        match = re.findall(r"[0-9().]+(?:\s*[+\-*/%]{1,2}\s*[0-9().]+)+", allowed)
        if not match:
            return None

        expr = max(match, key=len)

        # --- STEP 8: Validasi akhir ---
        if not re.search(r"[+\-*/%]", expr):
            return None
        if len(expr) > 80:
            return None
        # Validasi tanda kurung seimbang
        if expr.count("(") != expr.count(")"):
            return None

        return expr.strip()

    def safe_eval_expression(self, expr: str) -> Optional[float]:
        """Safely evaluate arithmetic expression using AST (no eval)."""
        import ast
        import operator as op

        allowed_ops = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.FloorDiv: op.floordiv,
            ast.Mod: op.mod,
            ast.Pow: op.pow,
            ast.UAdd: op.pos,
            ast.USub: op.neg,
        }

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](_eval(node.operand))
            if isinstance(node, ast.Num):  # Py<3.8
                return node.n
            if hasattr(ast, "Constant") and isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.Call):
                raise ValueError("Function calls are not allowed")
            raise ValueError("Unsupported expression")

        try:
            tree = ast.parse(expr, mode="eval")
            return float(_eval(tree))
        except Exception:
            return None

    def format_number_brief(self, value: float) -> str:
        """Format a number briefly for arithmetic results."""
        try:
            if abs(value - round(value)) < 1e-9:
                return str(int(round(value)))
            s = f"{value:.6f}"
            s = s.rstrip("0").rstrip(".")
            return s
        except Exception:
            return str(value)

    def explain_arithmetic(self, expr: str, result: float) -> str:
        """Return a concise but explicit explanation for a calculation in Indonesian."""
        try:
            pretty = expr.replace("**", "^").replace("*", "×").replace("/", "÷")
            ans = self.format_number_brief(result)

            # Heuristic operator detection
            has_mul = "×" in pretty
            has_add = "+" in pretty
            has_sub = "-" in pretty and not pretty.strip().startswith("-")
            has_div = "÷" in pretty
            has_pow = "^" in pretty

            explanation = [f"{pretty} = {ans}."]
            if has_pow:
                explanation.append("Pangkat berarti mengalikan bilangan basis dengan dirinya sendiri sejumlah pangkatnya.")
            if has_mul:
                # Try repeated addition if both operands small integers
                m = re.match(r"\s*(\d+)\s*×\s*(\d+)\s*$", pretty)
                if m:
                    a, b = int(m.group(1)), int(m.group(2))
                    if a <= 10 and b <= 10:
                        explanation.append(
                            f"Karena {a} dikali {b} adalah penjumlahan {a} sebanyak {b} kali: "
                            f"{'+'.join([str(a)] * b)} = {ans}."
                        )
                else:
                    explanation.append("Perkalian dapat dipahami sebagai penjumlahan berulang.")
            if has_div:
                explanation.append("Pembagian membagi bilangan menjadi bagian yang sama besar.")
            if has_add and not has_mul and not has_div and not has_pow:
                explanation.append("Penjumlahan menggabungkan nilai-nilai menjadi satu total.")
            if has_sub and not has_mul and not has_div and not has_pow:
                explanation.append("Pengurangan mengurangi suatu nilai dari nilai lainnya.")

            return " ".join(explanation)
        except Exception:
            ans = self.format_number_brief(result)
            return f"Hasilnya {ans}."
