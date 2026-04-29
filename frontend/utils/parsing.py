import re

def get_eval_math(val_str):
    val_clean = str(val_str).replace(",", "").strip()
    if not val_clean:
        return None
    if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", val_clean):
        try:
            return eval(val_clean)
        except:
            return None
    return None

def parsed_val(ui_input_element) -> float | int:
    """Safe evaluation helper to get the numeric underlying float value from accounting_input or ui.number"""
    if not ui_input_element:
        return 0
    v = getattr(ui_input_element, "value", None)
    if not v:
        return 0
    try:
        if isinstance(v, (int, float)):
            return float(v)
        v_str = str(v).replace(",", "").strip()
        
        if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", v_str):
            res = float(eval(v_str))
            return int(res) if res.is_integer() else res
        return float(v_str) if "." in v_str else int(v_str)
    except Exception:
        return 0
