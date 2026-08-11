using System.Linq;
using System.Reflection;
using System.Text.Json;
using Fabulor.Plugins;

public sealed class GreeterPlugin : IFabulorPlugin
{
    private static readonly string SettingsPath = Path.Combine(
        Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? AppContext.BaseDirectory,
        "settings.json");

    private readonly Dictionary<string, GreeterTarget> _targets = new(StringComparer.Ordinal);
    private FabulorContext? _context;

    public void Init(FabulorContext context)
    {
        _context = context;
        LoadTargets();
        context.RegisterCallback("command", OnCommand);
        context.RegisterCallback("server:JOIN", OnJoin);
    }

    private FabulorEventResult OnCommand(FabulorEvent evt)
    {
        if (!string.Equals(evt.Word1, "greeter", StringComparison.OrdinalIgnoreCase))
        {
            return FabulorEventResult.Continue;
        }

        var action = evt.Word2?.Trim().ToLowerInvariant();
        var channel = (evt.Word3 ?? string.Empty).TrimStart(':');
        var network = evt.Network ?? string.Empty;

        if (action is "status" or "list")
        {
            LogStatus();
            return FabulorEventResult.Consume;
        }

        if (action is not ("enable" or "disable") || string.IsNullOrWhiteSpace(channel))
        {
            Log("Usage: /greeter enable <channel> | disable <channel> | status");
            return FabulorEventResult.Consume;
        }

        if (string.IsNullOrWhiteSpace(network))
        {
            Log("C# Greeter needs an active network for this command.");
            return FabulorEventResult.Consume;
        }

        var key = TargetKey(network, channel);
        if (action == "enable")
        {
            if (_targets.ContainsKey(key))
            {
                Log($"C# Greeter is already enabled for {channel} on {network}.");
                return FabulorEventResult.Consume;
            }

            _targets[key] = new GreeterTarget(network, channel);
            if (!TrySaveTargets())
            {
                _targets.Remove(key);
                return FabulorEventResult.Consume;
            }

            Log($"C# Greeter enabled for {channel} on {network}.");
            return FabulorEventResult.Consume;
        }

        if (!_targets.Remove(key, out var removedTarget))
        {
            Log($"C# Greeter is not enabled for {channel} on {network}.");
            return FabulorEventResult.Consume;
        }

        if (!TrySaveTargets())
        {
            _targets[key] = removedTarget;
            return FabulorEventResult.Consume;
        }

        Log($"C# Greeter disabled for {channel} on {network}.");
        return FabulorEventResult.Consume;
    }

    private void OnJoin(FabulorEvent evt)
    {
        var network = evt.Network ?? string.Empty;
        var channel = (evt.Channel ?? evt.Word3 ?? string.Empty).TrimStart(':');
        if (!_targets.ContainsKey(TargetKey(network, channel)))
        {
            return;
        }

        var nickname = JoinNickname(evt.Word1);
        if (string.IsNullOrWhiteSpace(nickname)
            || string.Equals(nickname, evt.Nick, StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        if (_context!.SendMessage(channel, $"Hello, {nickname}!"))
        {
            Log($"C# Greeter welcomed {nickname} in {channel} on {network}.");
        }
        else
        {
            Log($"C# Greeter could not welcome {nickname} in {channel} on {network}.");
        }
    }

    private void LoadTargets()
    {
        _targets.Clear();
        if (!File.Exists(SettingsPath))
        {
            return;
        }

        try
        {
            var settings = JsonSerializer.Deserialize<GreeterSettings>(File.ReadAllText(SettingsPath));
            foreach (var target in (settings?.Targets ?? [])
                         .Where(target => !string.IsNullOrWhiteSpace(target.Network)
                                          && !string.IsNullOrWhiteSpace(target.Channel)))
            {
                _targets[TargetKey(target.Network, target.Channel)] = target;
            }
        }
        catch (Exception error) when (error is IOException or JsonException or UnauthorizedAccessException)
        {
            Log($"C# Greeter could not read its settings: {error.Message}");
        }
    }

    private bool TrySaveTargets()
    {
        try
        {
            var settings = new GreeterSettings
            {
                Targets = _targets.Values
                    .OrderBy(target => target.Network, StringComparer.OrdinalIgnoreCase)
                    .ThenBy(target => target.Channel, StringComparer.OrdinalIgnoreCase)
                    .ToList(),
            };
            var temporaryPath = $"{SettingsPath}.tmp";
            File.WriteAllText(temporaryPath, JsonSerializer.Serialize(settings, new JsonSerializerOptions
            {
                WriteIndented = true,
            }));
            File.Move(temporaryPath, SettingsPath, true);
            return true;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            Log($"C# Greeter could not save its settings: {error.Message}");
            return false;
        }
    }

    private void LogStatus()
    {
        if (_targets.Count == 0)
        {
            Log("C# Greeter has no enabled channels.");
            return;
        }

        Log("C# Greeter enabled channels:");
        foreach (var target in _targets.Values
                     .OrderBy(target => target.Network, StringComparer.OrdinalIgnoreCase)
                     .ThenBy(target => target.Channel, StringComparer.OrdinalIgnoreCase))
        {
            Log($"  {target.Channel} on {target.Network}");
        }
    }

    private void Log(string message)
    {
        _context?.Log(message);
    }

    private static string JoinNickname(string? prefix)
    {
        var value = prefix?.TrimStart(':') ?? string.Empty;
        var separator = value.IndexOf('!');
        return separator >= 0 ? value[..separator] : value;
    }

    private static string TargetKey(string network, string channel)
    {
        return $"{network.Trim().ToUpperInvariant()}\u001f{channel.Trim().ToUpperInvariant()}";
    }

    private sealed record GreeterTarget(string Network, string Channel);

    private sealed class GreeterSettings
    {
        public List<GreeterTarget> Targets { get; init; } = [];
    }
}
