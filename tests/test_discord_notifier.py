from src.notifiers.discord import DiscordNotifier


def test_discord_notifier_initialization_with_url():
    """Test DiscordNotifier initializes with webhook URL"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    assert notifier.webhook_url == webhook_url
    assert notifier.failures == []


def test_discord_notifier_initialization_with_none():
    """Test DiscordNotifier handles None webhook URL"""
    notifier = DiscordNotifier(None)

    assert notifier.webhook_url is None
    assert notifier.failures == []
