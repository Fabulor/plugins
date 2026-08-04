using Fabulor.Plugins;

public sealed class GreeterPlugin : IFabulorPlugin
{
    private FabulorContext? _context;
    private bool _reportedFirstMessage;

    public void Init(FabulorContext context)
    {
        _context = context;
        var user = context.GetUserInfo();
        context.Log($"Hello, {user.Nickname ?? "unknown"}. C# sample ready.");
        context.RegisterCallback("message", OnMessage);
    }

    private void OnMessage(FabulorEvent evt)
    {
        if (_reportedFirstMessage || _context is null)
        {
            return;
        }

        _reportedFirstMessage = true;
        var location = string.IsNullOrWhiteSpace(evt.Channel)
            ? "the active session"
            : evt.Channel;
        _context.Log($"C# sample observed its first incoming message event in {location}.");
    }
}
