
import os
import sys
import time
import json
import random
import asyncio
import logging
import sqlite3
import threading
import platform
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ==================== CONFIG ====================

BOT_NAME = "TestBot"
BOT_VERSION = "1.0.0"
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "8080"))
PREFIX = "!"
START_TIME = time.time()
DATABASE = "bot.db"
MODE = "discord" if TOKEN else "simulation"

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(BOT_NAME)

# ==================== DATABASE ====================

def init_db():
    with sqlite3.connect(DATABASE) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                command TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.commit()

    logger.info("SQLite database initialized")


def save_command(username, command):
    with sqlite3.connect(DATABASE, timeout=5) as db:
        db.execute(
            """
            INSERT INTO commands
            (username, command, created_at)
            VALUES (?, ?, ?)
            """,
            (
                str(username),
                str(command),
                datetime.now(timezone.utc).isoformat()
            )
        )
        db.commit()


def total_commands():
    with sqlite3.connect(DATABASE) as db:
        return db.execute(
            "SELECT COUNT(*) FROM commands"
        ).fetchone()[0]


# ==================== SYSTEM ====================

def uptime():
    seconds = int(time.time() - START_TIME)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return f"{days}d {hours}h {minutes}m {seconds}s"


def system_stats():
    load = None
    memory = None

    try:
        load = round(os.getloadavg()[0], 2)
    except (AttributeError, OSError):
        pass

    try:
        with open("/proc/meminfo") as file:
            values = {}

            for line in file:
                key, value = line.split(":", 1)
                values[key] = int(value.strip().split()[0])

        total = values["MemTotal"]
        available = values["MemAvailable"]

        memory = round(
            (total - available) / total * 100, 2
        )
    except (OSError, KeyError, ValueError):
        pass

    return {
        "name": BOT_NAME,
        "version": BOT_VERSION,
        "status": "running",
        "mode": MODE,
        "uptime": uptime(),
        "platform": platform.system(),
        "python": platform.python_version(),
        "cpu_cores": os.cpu_count(),
        "load_average": load,
        "system_memory_percent": memory,
        "total_commands": total_commands(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== HTTP SERVER ====================

class HTTPHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):

        if self.path == "/":
            self.send_json({
                "message": f"{BOT_NAME} is running!",
                "version": BOT_VERSION,
                "mode": MODE,
                "endpoints": [
                    "/health",
                    "/stats",
                    "/commands"
                ]
            })

        elif self.path == "/health":
            self.send_json({
                "status": "ok",
                "mode": MODE,
                "uptime": uptime()
            })

        elif self.path == "/stats":
            self.send_json(system_stats())

        elif self.path == "/commands":
            self.send_json({
                "commands": [
                    "!ping",
                    "!help",
                    "!uptime",
                    "!server",
                    "!userinfo",
                    "!stats",
                    "!roll",
                    "!coin",
                    "!random",
                    "!say",
                    "!clear",
                    "!kick",
                    "!ban"
                ]
            })

        else:
            self.send_json({
                "error": "Not Found"
            }, 404)

    def log_message(self, format, *args):
        logger.info(
            "HTTP | %s | %s",
            self.client_address[0],
            format % args
        )


def start_http_server():
    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        HTTPHandler
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )
    thread.start()

    logger.info("HTTP server listening on port %s", PORT)

    return server


# ==================== SIMULATION ====================

async def simulation_mode():

    logger.warning("Discord token not provided")
    logger.info("Starting simulation mode")
    logger.info("No external API or credentials required")

    users = [
        "TestUser_01",
        "TestUser_02",
        "TestUser_03",
        "TestAdmin",
        "TestDeveloper"
    ]

    commands = [
        "ping",
        "uptime",
        "server",
        "userinfo",
        "stats",
        "roll",
        "coin",
        "random",
        "help"
    ]

    responses = {
        "ping": lambda: f"Pong! {random.randint(10, 90)}ms",
        "uptime": uptime,
        "server": lambda: "Simulation server",
        "userinfo": lambda: "Simulated user information",
        "stats": lambda: f"Commands: {total_commands()}",
        "roll": lambda: f"Dice: {random.randint(1, 6)}",
        "coin": lambda: random.choice(["Heads", "Tails"]),
        "random": lambda: str(random.randint(1, 100)),
        "help": lambda: ", ".join(commands)
    }

    logger.info("Simulation bot is online")

    while True:

        user = random.choice(users)
        command = random.choice(commands)

        logger.info(
            "SIMULATION | %s executed !%s",
            user,
            command
        )

        save_command(user, command)

        response = responses[command]()

        logger.info("BOT RESPONSE | %s", response)

        logger.info(
            "SYSTEM | Uptime: %s | Commands: %s",
            uptime(),
            total_commands()
        )

        await asyncio.sleep(random.randint(5, 15))


# ==================== DISCORD BOT ====================

def run_discord():

    try:
        import discord
        from discord.ext import commands
    except ImportError:
        logger.error("Install discord.py: pip install discord.py")
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(
        command_prefix=PREFIX,
        intents=intents,
        allowed_mentions=discord.AllowedMentions.none()
    )

    @bot.event
    async def on_ready():

        logger.info("Discord bot connected: %s", bot.user)
        logger.info("Connected servers: %s", len(bot.guilds))

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="!help"
            )
        )

    @bot.event
    async def on_member_join(member):

        channel = member.guild.system_channel

        if channel:
            permissions = channel.permissions_for(member.guild.me)

            if permissions.send_messages:
                await channel.send(
                    f"Welcome, {member.display_name}!"
                )

        logger.info("MEMBER JOIN | %s", member.id)

    @bot.event
    async def on_command_completion(ctx):
        save_command(ctx.author.id, ctx.command.name)

        logger.info(
            "COMMAND | User: %s | Command: %s",
            ctx.author.id,
            ctx.command.name
        )

    @bot.command()
    async def ping(ctx):
        await ctx.send(
            f"Pong! {round(bot.latency * 1000)}ms"
        )

    @bot.command(name="uptime")
    async def uptime_command(ctx):
        await ctx.send(f"Bot uptime: {uptime()}")

    @bot.command()
    @commands.guild_only()
    async def server(ctx):

        guild = ctx.guild

        embed = discord.Embed(
            title="Server Information",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Server",
            value=guild.name
        )

        embed.add_field(
            name="Members",
            value=guild.member_count
        )

        embed.add_field(
            name="Channels",
            value=len(guild.channels)
        )

        embed.add_field(
            name="Roles",
            value=len(guild.roles)
        )

        await ctx.send(embed=embed)

    @bot.command()
    @commands.guild_only()
    async def userinfo(
        ctx,
        member: discord.Member = None
    ):

        member = member or ctx.author

        embed = discord.Embed(
            title="User Information",
            color=discord.Color.green()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="Username",
            value=member.display_name
        )

        embed.add_field(
            name="User ID",
            value=str(member.id)
        )

        embed.add_field(
            name="Created",
            value=member.created_at.strftime("%d/%m/%Y")
        )

        await ctx.send(embed=embed)

    @bot.command()
    async def stats(ctx):

        data = system_stats()

        embed = discord.Embed(
            title="Bot Statistics",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Servers",
            value=len(bot.guilds)
        )

        embed.add_field(
            name="Commands",
            value=data["total_commands"]
        )

        embed.add_field(
            name="Uptime",
            value=data["uptime"]
        )

        embed.add_field(
            name="Python",
            value=data["python"]
        )

        await ctx.send(embed=embed)

    @bot.command()
    async def roll(ctx):
        await ctx.send(
            f"Dice result: {random.randint(1, 6)}"
        )

    @bot.command()
    async def coin(ctx):
        await ctx.send(
            random.choice(["Heads", "Tails"])
        )

    @bot.command(name="random")
    async def random_number(
        ctx,
        minimum: int = 1,
        maximum: int = 100
    ):

        if minimum > maximum:
            await ctx.send("Invalid number range.")
            return

        await ctx.send(
            str(random.randint(minimum, maximum))
        )

    @bot.command()
    @commands.has_permissions(manage_messages=True)
    async def say(ctx, *, message: str):

        if len(message) > 1800:
            await ctx.send("Message is too long.")
            return

        await ctx.send(
            f"{ctx.author.display_name}: {message}"
        )

    @bot.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear(ctx, amount: int = 5):

        amount = max(1, min(amount, 100))

        deleted = await ctx.channel.purge(
            limit=amount + 1
        )

        await ctx.send(
            f"Deleted {len(deleted)} messages.",
            delete_after=5
        )

    def can_moderate(ctx, member):

        if member.id in (
            ctx.guild.owner_id,
            ctx.author.id,
            bot.user.id
        ):
            return False

        if ctx.guild.me.top_role <= member.top_role:
            return False

        if ctx.author.id == ctx.guild.owner_id:
            return True

        return ctx.author.top_role > member.top_role

    @bot.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        ctx,
        member: discord.Member,
        *,
        reason="No reason provided"
    ):

        if not can_moderate(ctx, member):
            await ctx.send("Role hierarchy prevents this action.")
            return

        await member.kick(reason=reason[:400])

        await ctx.send(
            f"{member.display_name} was kicked."
        )

    @bot.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        ctx,
        member: discord.Member,
        *,
        reason="No reason provided"
    ):

        if not can_moderate(ctx, member):
            await ctx.send("Role hierarchy prevents this action.")
            return

        await member.ban(reason=reason[:400])

        await ctx.send(
            f"{member.display_name} was banned."
        )

    @bot.event
    async def on_command_error(ctx, error):

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Insufficient permissions.")

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot permissions are missing.")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argument.")

        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument.")

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command requires a server.")

        else:
            logger.error("COMMAND ERROR | %s", type(error).__name__)
            await ctx.send("An unexpected error occurred.")

    bot.run(TOKEN)


# ==================== ENTRY POINT ====================

if __name__ == "__main__":

    print("=" * 50)
    print(f"  {BOT_NAME} v{BOT_VERSION}")
    print(f"  Mode: {MODE.upper()}")
    print(f"  Python: {platform.python_version()}")
    print(f"  Port: {PORT}")
    print("=" * 50)

    init_db()
    http_server = start_http_server()

    try:

        if TOKEN:
            run_discord()
        else:
            asyncio.run(simulation_mode())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

    finally:
        http_server.shutdown()
        http_server.server_close()
        logger.info("Shutdown completed")
