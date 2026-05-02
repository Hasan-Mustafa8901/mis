from nicegui import ui

def format_num_inr(num_val):
    """Format float into standard accounting formatting, e.g. 1,000.00"""
    try:
        return f"{float(num_val):,.2f}"
    except (ValueError, TypeError):
        return "0.00"

def get_eval_math(val_str):
    import re
    val_clean = str(val_str).replace(",", "").strip()
    if not val_clean:
        return None
    # Allow numbers and basic operators
    if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", val_clean):
        try:
            # Using eval safely for math only
            return eval(val_clean, {"__builtins__": {}}, {})
        except Exception:
            return None
    return None

def parsed_val(ui_input_element) -> float | int:
    """Safe evaluation helper to get the numeric underlying float value from accounting_input or ui.number"""
    if not ui_input_element:
        return 0
    v = getattr(ui_input_element, "value", None)
    if v is None or v == "":
        return 0
    try:
        if isinstance(v, (int, float)):
            return float(v)
        v_str = str(v).replace(",", "").strip()
        import re
        if re.fullmatch(r"[\d\+\-\*\/\.\s()]+", v_str):
            res = float(eval(v_str, {"__builtins__": {}}, {}))
            return int(res) if res.is_integer() else res
        return float(v_str) if "." in v_str else int(v_str)
    except Exception:
        return 0

def accounting_input(
    label_text: str, placeholder: str = "", container_classes: str = "w-full"
) -> ui.input:
    with ui.column().classes(f"gap-0 {container_classes} mb-1"):
        inp = (
            ui.input(label=label_text, placeholder=placeholder)
            .props("outlined dense")
            .classes("w-full")
        )
        hint = ui.label("").classes(
            "text-[11px] text-green-600 font-bold ml-1 h-3 -mt-2"
        )

    def handle_eval(e):
        val = e.value
        if not val:
            hint.set_text("")
            return
        try:
            res = get_eval_math(val)
            if res is not None:
                res_str = format_num_inr(res)
                val_clean = str(val).replace(",", "").strip()
                if val_clean != str(res) and not val_clean.replace(".", "").isdigit():
                    hint.set_text(f"= {res_str}")
                else:
                    hint.set_text("")
                hint.classes(replace="text-red-500", add="text-green-600")
                return
        except Exception:
            pass
        hint.set_text("Invalid math")
        hint.classes(replace="text-green-600", add="text-red-500")

    def handle_blur(e=None):
        if not inp.value:
            return
        try:
            res = get_eval_math(inp.value)
            if res is not None:
                inp.set_value(format_num_inr(res))
                hint.set_text("")
        except Exception:
            pass

    inp.on_value_change(handle_eval)
    inp.on("blur", handle_blur)
    inp.on("keyup.enter", handle_blur)
    return inp
