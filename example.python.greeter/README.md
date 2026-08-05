# Python Greeter

Python Greeter is a small Fabulor manifest plugin that welcomes users when they
join configured IRC channels.

## Commands

Enter commands in a tab on the network you want to configure:

```text
/greeter enable <channel>
/greeter disable <channel>
/greeter status
```

For example, entering `/greeter enable #test` from a DALnet tab enables DALnet
`#test` only. Libera.Chat `#test` remains disabled unless the same command is
entered from a Libera.Chat tab.

Command results are displayed in the tab where the command was entered.
Settings are saved in `settings.json` beside the plugin and restored when
Fabulor restarts.

## Behaviour

- Listens for IRC `JOIN` events.
- Sends `Hello, <nickname>!` to enabled channels.
- Matches both network and channel names.
- Does not greet the client's own nickname.
- Supports multiple enabled network/channel pairs.

The plugin must declare the `events.command`, `events.server`, `messages.write`,
and `session.read` capabilities in `plugin.json`.

## Files

- `plugin.json` contains the manifest and required capabilities.
- `plugin.py` contains command handling, persistence, and JOIN handling.
- `settings.json` is created automatically after the first enable or disable
  command.

