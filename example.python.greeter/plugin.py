import fabulor

_reported_first_message = False


def on_message(event):
    global _reported_first_message

    if _reported_first_message:
        return None

    _reported_first_message = True
    user = fabulor.get_user_info()
    location = user.get("channel") or "the active session"
    fabulor.log(f"Python sample observed its first incoming message event in {location}.")
    return None


def init():
    user = fabulor.get_user_info()
    nickname = user.get("nickname") or "unknown"
    fabulor.log(f"Hello, {nickname}. Python sample ready.")
    fabulor.register_callback("message", on_message)
