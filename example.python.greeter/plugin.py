import json
from pathlib import Path
import fabulor


_SETTINGS_PATH = Path(__file__).with_name("settings.json")
_EAT_ALL = 3
_targets = {}


def _same_name(left, right):
    return bool(left and right and left.casefold() == right.casefold())


def _target_key(network, channel):
    return network.casefold(), channel.casefold()


def _event_word(event, index):
    words = event.get("words") or []
    if index < len(words):
        return words[index]
    return event.get(f"word{index + 1}") or ""


def _joining_nickname(event):
    prefix = _event_word(event, 0).lstrip(":")
    return prefix.split("!", 1)[0]


def _joined_channel(event, user):
    channel = user.get("channel") or _event_word(event, 2)
    return channel.lstrip(":")


def _load_targets():
    _targets.clear()
    if not _SETTINGS_PATH.exists():
        return

    try:
        settings = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        for target in settings.get("targets", []):
            network = target.get("network") or ""
            channel = target.get("channel") or ""
            if network and channel:
                _targets[_target_key(network, channel)] = (network, channel)
    except (OSError, TypeError, ValueError) as error:
        fabulor.log(f"Python Greeter could not read its settings: {error}")


def _save_targets():
    settings = {
        "targets": [
            {"network": network, "channel": channel}
            for network, channel in sorted(
                _targets.values(), key=lambda item: (item[0].casefold(), item[1].casefold())
            )
        ]
    }
    temporary_path = _SETTINGS_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(settings, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(_SETTINGS_PATH)


def _log_usage():
    fabulor.log(
        "Usage: /greeter enable <channel> | disable <channel> | status"
    )


def on_greeter_command(event):
    action = _event_word(event, 1).casefold()
    channel = _event_word(event, 2).lstrip(":")
    user = fabulor.get_user_info()
    network = user.get("network_name") or ""

    if action in ("status", "list"):
        if not _targets:
            fabulor.log("Python Greeter has no enabled channels.")
        else:
            fabulor.log("Python Greeter enabled channels:")
            for configured_network, configured_channel in sorted(
                _targets.values(), key=lambda item: (item[0].casefold(), item[1].casefold())
            ):
                fabulor.log(f"  {configured_channel} on {configured_network}")
        return _EAT_ALL

    if action not in ("enable", "disable") or not channel:
        _log_usage()
        return _EAT_ALL

    if not network:
        fabulor.log("Python Greeter needs an active network for this command.")
        return _EAT_ALL

    key = _target_key(network, channel)
    if action == "enable":
        if key in _targets:
            fabulor.log(f"Python Greeter is already enabled for {channel} on {network}.")
            return _EAT_ALL
        _targets[key] = (network, channel)
        result = "enabled"
    else:
        if key not in _targets:
            fabulor.log(f"Python Greeter is not enabled for {channel} on {network}.")
            return _EAT_ALL
        del _targets[key]
        result = "disabled"

    try:
        _save_targets()
    except OSError as error:
        if action == "enable":
            del _targets[key]
        else:
            _targets[key] = (network, channel)
        fabulor.log(f"Python Greeter could not save its settings: {error}")
        return _EAT_ALL

    fabulor.log(f"Python Greeter {result} for {channel} on {network}.")
    return _EAT_ALL


def on_join(event):
    user = fabulor.get_user_info()
    network = user.get("network_name") or ""
    channel = _joined_channel(event, user)

    if _target_key(network, channel) not in _targets:
        return

    nickname = _joining_nickname(event)
    own_nickname = user.get("nickname") or ""
    if not nickname or _same_name(nickname, own_nickname):
        return

    fabulor.send_message(channel, f"Hello, {nickname}!")
    fabulor.log(f"Python Greeter welcomed {nickname} in {channel} on {network}.")
    return


def init():
    _load_targets()
    fabulor.register_callback("command:GREETER", on_greeter_command)
    fabulor.register_callback("server:JOIN", on_join)
