from nicegui import ui
from utils.parsing import get_eval_math

def format_num_inr(num_val):
    """Format float into standard accounting formatting, e.g. 1,000.00"""
    return f"{float(num_val):,.2f}"

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
