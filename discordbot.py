
# TODO: GraphQL query for embeddingExists every 5 minutes, then tag the user that their embedding is ready
# TODO: Check when the embeddings job is completed
# TODO: Check the completed embeddings job for errors
# Interaction tokens are valid for 15 minutes, meaning you can respond to an interaction within that amount of time.
# https://discord.com/developers/docs/interactions/receiving-and-responding#followup-messages

# TODO: Build a button the user can press to check status (completion vs errors)
# TODO: Build a button the user can press to retry
# https://discord.com/developers/docs/interactions/message-components

# TODO: Sort out where the asyncio timeout exception needs to go

# Docs:
# We're actually using the pycord interface
# We have Cody embeddings for it :)
# https://sourcegraph.com/github.com/Pycord-Development/pycord

# General information about Discord's Python interface
# https://discordpy.readthedocs.io/en/latest/interactions/api.html

from aiohttp                import web
from config                 import SG_TOKEN, DISCORD_TOKEN
from discord.ext.commands   import Bot
import asyncio
import discord
import json
import logging
import os
import re                   as regex
import requests
import string
import sys


# Configure logging
def configure_logging():

  # Get the log level if it's defined in the env vars
  if "LOGLEVEL" in os.environ:
    logLevel = os.environ.get("LOGLEVEL")

  else:
    # Otherwise assume info
    logLevel = "INFO"

  # Get the existing logger
  logger = logging.getLogger(__name__)
  logger.setLevel(logLevel)

  # Add a new StreamHandler
  stream_handler = logging.StreamHandler()
  stream_handler.setLevel(logLevel)
  logger.addHandler(stream_handler)

  if "MODE" in os.environ:
    mode = os.environ.get("MODE")

    if mode == "DEV":
      logging_handler = logging.StreamHandler(sys.stdout)

      logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8',
        format='%(asctime)s: %(levelname)s: %(message)s',
        level=logLevel
      )

  return logger

# Declaring this as a global, not sure why that seems to be needed
logger = configure_logging()


# All of the repo_url sanitization and validation code should happen in one function
# This needs to happen on the client side, because the GraphQL API rejects invalid repo_urls instead of sanitizing them
def sanitize_repo_url(repo_url):

  try:

    # The order of these operations is significant

    # Format required by embeddings scheduler
    # github.com/org/repo

    # Users have tried providing repo_urls like
    # https://github.com/org/repo
    # https://www.github.com/org/repo
    # www.github.com/org/repo
    # www.github.com/org/repo.git
    # www.github.com/org/repo.git@ref

    sanitized_repo_url_messages = []
    subStringsToRemove = [
      "https://",
      "http://",
      "www.",
      ".git",
      "git@",
    ]

    # Convert to lowercase
    # Don't need to warn the user about case
    repo_url = repo_url.lower()

    # Remove all whitespaces
    repo_url = regex.sub(r"\s+", "", repo_url, flags=regex.UNICODE)

    # Loop through prefixesToRemove warn the user, and remove them
    for subString in subStringsToRemove:
      if subString in repo_url:
        sanitized_repo_url_messages.append("Removed: " + subString)
        repo_url = repo_url.replace(subString, "")

    # Remove @[ref] if present
    # Branch name, tag name, or commit hash
    # At this time, it appears that the embeddings job web UI https://sourcegraph.com/site-admin/embeddings doesn't support @refs, only default branch at head
    # This may change in the future, and would need to be removed then
    regexFilterForGitRefs = r"@[\w\d\./_-]*$"
    matches = regex.findall(regexFilterForGitRefs, repo_url)
    for match in matches:
      sanitized_repo_url_messages.append("Removed: " + match + ", only the HEAD revision of the default branch is supported for embeddings at this time.")
      repo_url = repo_url.replace(match,"")

    # Cleanup any invalid characters remaining
    allowed_chars = set(string.ascii_letters + string.digits + "./_-")
    disallowed_chars = set(repo_url) - allowed_chars
    removed_chars = []

    for char in disallowed_chars:
      removed_chars.append(char)
      repo_url = repo_url.replace(char, "")

    if len(removed_chars) > 0:
      sanitized_repo_url_messages.append("Removed invalid characters" + str(removed_chars))

    # Verify the repo exists and is public
    response = requests.get(
      url=f"https://{repo_url}"
    )

    if response.status_code == 200:
      logger.debug(f"Validated repo exists: https://{repo_url}")
      sanitized_repo_url_messages.append(f"Validated repo exists: https://{repo_url}")
    else:
      logger.error(f"Failed to validate repo exists: https://{repo_url}")
      sanitized_repo_url_messages.append(f"Failed to validate repo exists: https://{repo_url}")

  except Exception as e:
    logger.exception(e)

  return repo_url, sanitized_repo_url_messages


# Determine Sourcegraph server URL, dotcom by default
def get_sourcegraph_server_addresses():

  # Start with a default of dotcom
  sg_server = "sourcegraph.com"

  # If this service was started with the SG_SERVER environment variable, then use it
  if "SG_SERVER" in os.environ:
    sg_server = os.environ.get("SG_SERVER")

  # If it's provided with http, remove it
  if "http://" in sg_server:
    sg_server.replace("http://","")

  # If it doesn't have https, prepend it
  if "https://" not in sg_server:
    sg_server = ''.join(["https://",sg_server])

  # If it has .api/graphql, remove it
  if ".api/graphql" in sg_server:
    sg_server.replace(".api/graphql","")

  # If it ends with a trailing slash or two, remove it
  sg_server = sg_server.rstrip("/")

  # Append the /.api/graphql endpoint to the sg_server, to get the sg_server_api
  sg_server_api = ''.join([sg_server,"/.api/graphql"])
  
  # Return both values
  return sg_server, sg_server_api


# Send the GraphQL API mutation to the Sourcegraph instance
def send_graphql_request(sanitized_repo_url, sg_server_api):

  message = ""
  success = False

  queryBody = f"""
  mutation {{
    scheduleRepositoriesForEmbedding(
      repoNames: [
        "{sanitized_repo_url}"
      ]
    ) {{
      alwaysNil
    }}
  }}
  """

  # Try / except block for GraphQL mutation
  try:

    # Post the query to the API endpoint
    response = requests.post(
      url=sg_server_api,
      json={"query": queryBody},
      headers={"Authorization": f"token {SG_TOKEN}"}
    )

  except asyncio.TimeoutError as e:

    logger.error(f"GraphQL query timed out: {e}")
    message = "⚠️ Timed out submitting embeddings job to the Sourcegraph server, please try again!"
    success = False

  except Exception as e:

    logger.error(f"GraphQL query failed: {e} {response}")
    success = False

  if response.status_code == 200:

    logger.debug(f"GraphQL query connection succeeded: {response.status_code} {response.text}")
    success = True
    responseJson = json.loads(response.text)

    if responseJson.get("errors"):
      logger.error(f"GraphQL query returned errors: {response.text}")
      success = False,
      errors = responseJson.get("errors")
      message = errors

      if "repo not found" in response.text:
        messages = []
        for error in errors:
          messages.append(error.get("message"))
        message = "\n".join(messages)

  else:

    logger.error(f"GraphQL query connection failed: {response.status_code} {response.text}")
    success = False,

  return success, message


# Configure and create an instance of the Discord bot
intents = discord.Intents.default()
intents.messages = True
bot = Bot(command_prefix="embeddings", intents=intents)


# Define the event handler for when the slash_command is received
@bot.slash_command(description="Request Cody embeddings for a repo")
@discord.option(name="repo_url", description="Enter the public repo in the format: github.com/org/repo")
async def embedding(ctx: discord.ApplicationContext, repo_url: str):

  # Try / except block for Discord bot messages
  try:

    # Sanitize the repo URL before responding to the Discord user, so the user can visually validate the sanitized repo URL is valid, and tag us for support if not
    sanitized_repo_url, sanitized_repo_url_messages = sanitize_repo_url(repo_url)

    # Get the Sourcegraph server and GraphQL api endpoints
    sg_server, sg_server_api = get_sourcegraph_server_addresses()

    # Acknowledge the command, to avoid showing an error to the user, "The application did not respond"
    await ctx.send_response(
      content="Received /embedding command, creating new thread in this channel.",
      ephemeral=True,
      delete_after=10
    )

    # Create the thread to reply in
    thread = await ctx.interaction.channel.create_thread(
        name=sanitized_repo_url.replace('github.com/',''),
        auto_archive_duration=60,
        type=discord.ChannelType.public_thread
    )

    # Send the initial message
    await thread.send(f"{ctx.author.mention} requested embeddings for {repo_url}")

    # If the sanitization returned sanitized_repo_url_messages, then respond to the user with them
    if len(sanitized_repo_url_messages) > 0:
      sanitized_repo_url_messages.insert(0, "Input sanitizer messages:")
      await thread.send(
        content="\n".join(sanitized_repo_url_messages),
        suppress=True
      )

    # Respond to the user's command
    await thread.send(
      content=f"Submitting {sanitized_repo_url} for embeddings on Sourcegraph.com",
      suppress=True
    )

    # Get the return value and respond to the user
    graphqlSendSuccess, message = send_graphql_request(sanitized_repo_url, sg_server_api)

    if graphqlSendSuccess == True:

      # Send a message back to the channel if the GraphQL mutation was successful
      responseToUser = f"""
✅ Embeddings are processing!
Embeddings are usually available within ~30 minutes, depending on the size of the repo.
To check if they're completed:
1. Go to your repo on Sourcegraph {sg_server + "/" + sanitized_repo_url}
2. Log in with your GitHub.com account
3. Click on the Ask Cody button near the top right
4. Check the Chat Context menu in the bottom left corner of the chat pane for a checkmark or X
"""
      await thread.send(
        content=responseToUser,
        suppress=True
      )

    else:

      # Send a message back to the channel if the GraphQL mutation was not successful, show an error to the user
      await thread.send(
        content=f"❌ Error submitting embeddings job to the Sourcegraph server: {message}",
        suppress=True
      )

  except Exception as e:
    logger.exception(e)
    await thread.send(
      content=f"❌ Error occurred: {e}",
      suppress=True
    )


# Provide a healthcheck endpoint for the container / pod
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
  configure_logging()
  asyncio.get_event_loop().run_until_complete(main())
  bot.run(DISCORD_TOKEN)
