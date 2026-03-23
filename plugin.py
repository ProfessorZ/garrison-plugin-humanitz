"""HumanitZ dedicated server plugin for Garrison.

Protocol: Source RCON (port 8888 by default).
RCON commands (from official docs):
  info            - Get current world info
  Players         - List connected players (name/SteamID)
  fetchbanned     - List banned player Steam IDs
  QuickRestart    - Restart in 1 minute
  RestartNow      - Restart immediately
  CancelRestart   - Cancel pending restart
  admin <message> - Broadcast admin message to all players
  kick <SteamID>  - Kick a player by Steam ID
  ban <SteamID>   - Ban a player by Steam ID
"""

from __future__ import annotations

import re

from app.plugins.base import (
    CommandDef,
    CommandParam,
    GamePlugin,
    PlayerInfo,
    ServerStatus,
)


class HumanitZPlugin(GamePlugin):
    """HumanitZ dedicated server plugin (Source RCON)."""

    @property
    def game_type(self) -> str:
        return "humanitz"

    @property
    def display_name(self) -> str:
        return "HumanitZ"

    async def parse_players(self, raw_response: str) -> list[PlayerInfo]:
        """Parse output of the 'Players' RCON command.

        Expected format (one player per line):
            PlayerName : 76561198XXXXXXXXX
        or simply a list of names. Falls back gracefully.
        """
        players: list[PlayerInfo] = []
        if not raw_response or not raw_response.strip():
            return players

        for line in raw_response.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Try "Name : SteamID" format
            match = re.match(r"^(.+?)\s*:\s*(\d{17})$", line)
            if match:
                players.append(PlayerInfo(name=match.group(1).strip(), steam_id=match.group(2)))
            else:
                # Fallback: treat whole line as name
                players.append(PlayerInfo(name=line))
        return players

    async def get_status(self, send_command) -> ServerStatus:
        """Fetch server status via 'info' and 'Players' RCON commands."""
        try:
            info_raw = await send_command("info")
            players_raw = await send_command("Players")
        except Exception:
            return ServerStatus(online=False)

        players = await self.parse_players(players_raw or "")

        extra: dict = {}
        # Parse info output for key=value pairs
        if info_raw:
            for line in info_raw.strip().splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    extra[k.strip()] = v.strip()
                elif ":" in line:
                    k, _, v = line.partition(":")
                    extra[k.strip()] = v.strip()

        version = extra.get("Version") or extra.get("version")
        return ServerStatus(
            online=True,
            player_count=len(players),
            version=version,
            extra=extra,
        )

    def get_commands(self) -> list[CommandDef]:
        return [
            CommandDef(
                name="admin",
                description="Broadcast an admin message to all players",
                category="Chat",
                params=[CommandParam(name="message", type="string", description="Message to broadcast")],
                admin_only=True,
                example="admin Server restarting in 5 minutes",
            ),
            CommandDef(
                name="kick",
                description="Kick a player by Steam ID",
                category="Players",
                params=[CommandParam(name="steam_id", type="string", description="Player Steam ID")],
                admin_only=True,
                example="kick 76561198000000000",
            ),
            CommandDef(
                name="ban",
                description="Ban a player by Steam ID",
                category="Players",
                params=[CommandParam(name="steam_id", type="string", description="Player Steam ID")],
                admin_only=True,
                example="ban 76561198000000000",
            ),
            CommandDef(
                name="fetchbanned",
                description="List all banned player Steam IDs",
                category="Players",
                admin_only=True,
            ),
            CommandDef(
                name="QuickRestart",
                description="Schedule a server restart in 1 minute",
                category="Server",
                admin_only=True,
            ),
            CommandDef(
                name="RestartNow",
                description="Restart the server immediately",
                category="Server",
                admin_only=True,
            ),
            CommandDef(
                name="CancelRestart",
                description="Cancel a pending restart",
                category="Server",
                admin_only=True,
            ),
            CommandDef(
                name="info",
                description="Get current world/server info",
                category="Server",
                admin_only=False,
            ),
            CommandDef(
                name="Players",
                description="List currently connected players",
                category="Players",
                admin_only=False,
            ),
        ]

    async def kick_player(self, send_command, name: str, reason: str = "") -> str:
        """Kick by Steam ID (name param expected to be Steam ID or name)."""
        return await send_command(f"kick {name}")

    async def ban_player(self, send_command, name: str, reason: str = "") -> str:
        """Ban by Steam ID."""
        result = await send_command(f"ban {name}")
        if reason:
            await send_command(f"admin Player {name} was banned. Reason: {reason}")
        return result

    async def get_player_roles(self) -> list[str]:
        return []

    async def poll_events(self, send_command, since: str | None = None) -> list[dict]:
        return []
