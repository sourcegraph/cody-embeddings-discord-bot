import asyncio
import string
import discord
from config import SG_TOKEN, DISCORD_TOKEN
import requests
from discord.ext.commands import Bot
import re
from aiohttp import web
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)


def sanitize_repo_url(repo_url):
    allowed_chars = set(string.ascii_letters + string.digits + "./_-")
    disallowed_chars = set(repo_url) - allowed_chars

    for char in disallowed_chars:
        repo_url = repo_url.replace(char, "")

    return repo_url


def send_graphql_request(repo_url):
    # clean repo_url to prevent injection
    repo_url = sanitize_repo_url(repo_url)

    url = "https://sourcegraph.com/.api/graphql"
    body = f"""
    mutation {{
      scheduleRepositoriesForEmbedding(
        repoNames: [
          "{repo_url}"
        ]
      ) {{
        alwaysNil
      }}
    }}
    """
    response = requests.post(
        url=url, json={"query": body}, headers={"Authorization": f"token {SG_TOKEN}"}
    )
    print("response status code: ", response.status_code)
    if response.status_code == 200:
        logger.info(response.text)


intents = discord.Intents.default()
intents.messages = True

bot = Bot(command_prefix="embeddings", intents=intents)


@bot.slash_command(description="Create Embedding for Cody.")
@discord.option("name", description="Enter the public GitHub repo.")
async def embedding(ctx: discord.ApplicationContext, repo_url: str):
    try:
        await ctx.respond(f"Processing {repo_url}")
        send_graphql_request(
            repo_url=re.sub(r"^(www\.|https://)(.*?)/?$", r"\2", repo_url)
        )
        await ctx.send(f"✅ Embedding processing!\nShould be ready in ~30 minutes.")
    except asyncio.TimeoutError:
        await ctx.send("⚠️ Timed out, please try again!")
    except Exception as e:
        await ctx.send(f"❌ Error occurred: {e}")


async def healthcheck(request):
    logger.info("Healthcheck endpoint called - returned 200 OK response")
    return web.Response(text="OK")


async def main():
    app = web.Application()
    app.add_routes([web.get("/healthcheck", healthcheck)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, os.environ.get("HTTP_HOST"), os.environ.get("HTTP_PORT"))
    await site.start()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    bot.run(DISCORD_TOKEN)
