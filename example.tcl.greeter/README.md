# Tcl Greeter

The Tcl Greeter is a Fabulor API-v2 manifest plugin that welcomes users when
they join configured IRC channels.

## Commands

Run these commands from a tab on the network you want to configure:

```text
/greeter enable <channel>
/greeter disable <channel>
/greeter status
```

For example, `/greeter enable #test` in a DALnet tab enables DALnet `#test`
only. Libera.Chat `#test` remains disabled until enabled from a Libera.Chat
tab.

The plugin saves its enabled network/channel pairs in `settings.conf` beside
`plugin.tcl` and restores them when Fabulor restarts.

## Behaviour

- Consumes its own `/greeter` commands while leaving other commands alone.
- Listens for IRC `JOIN` events.
- Sends `Hello, <nickname>!` to enabled channels.
- Matches both network and channel names.
- Does not greet the client's own nickname.

## Deployment

Deploy `plugin.json` and `plugin.tcl` directly under a profile plugin folder,
for example:

```text
%APPDATA%\Fabulor\plugins\example.tcl.greeter\
```

