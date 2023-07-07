# TODO: Improve error handling when checking to validate a repo exists, when the code host is missing or malformed
# TODO: If we fail to sanitize the repo_url, don't send the GraphQL request

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
from urllib.parse           import urlparse     # https://docs.python.org/3/library/urllib.parse.html
import asyncio
import discord
import json
import logging
import os
import re                   as regex
import requests
import string
import sys
import validators                               # https://validators.readthedocs.io/en/latest/#


# Configure logging
def configure_logging():

  # Get the log level if it's defined in the env vars
  if "LOGLEVEL" in os.environ:
    log_level = os.environ.get("LOGLEVEL")

  else:
    # Otherwise assume info
    log_level = "INFO"

  logging_handlers = logging.StreamHandler(sys.stdout), logging.FileHandler("discordbot.log")

  logging.basicConfig(
      datefmt='%Y-%m-%d %H:%M:%S',
      encoding='utf-8',
      format='%(asctime)s: %(levelname)s: %(message)s',
      handlers=logging_handlers,
      level=log_level
  )


# All of the repo_url sanitization and validation code should happen in one function
# The order of these operations is significant
# This needs to happen on the client side, because the GraphQL API rejects invalid repo_urls instead of sanitizing them
async def sanitize_repo_url(repo_url):

  # Keep a copy of the repo_url the user gave us
  initial_repo_url = repo_url
  
  # Log it
  logging.info("initial_repo_url: " + initial_repo_url)

  sanitized_repo_url_messages = []
  url_scheme = "https://"

  try:

    # Format required by embeddings scheduler
    # github.com/org/repo

    # Users have tried providing repo_urls like
    # https://github.com/org/repo
    # https://www.github.com/org/repo
    # www.github.com/org/repo
    # www.github.com/org/repo.git
    # www.github.com/org/repo.git@ref
    # https://www.github.com/org/repo.git@ref


    # Remove any garbage / disallowed characters
    # This defines the list of valid characters in a codehost/org/repo name
    allowed_chars = set(string.ascii_letters + string.digits + ":/@-_.;?=&+#")
    # This finds any characters in repo_url that are not allowed
    disallowed_chars = set(repo_url) - allowed_chars
    removed_chars = []

    # If disallowed characters were found, remove them
    for char in disallowed_chars:
      removed_chars.append(char)
      repo_url = repo_url.replace(char, "")

    # If disallowed characters were found, report them to the user
    if len(removed_chars) > 0:
      sanitized_repo_url_messages.append("Removed invalid characters" + str(removed_chars))

    # Convert to lowercase
    # Don't need to warn the user about case
    repo_url = repo_url.lower()
    logging.info("repo_url after converting to lowercase: " + repo_url)

    # Only need to use urlparse to get hostname and path
    # urlparse doesn't work if the url doesn't start with a scheme://
    # So we have to normalize that first
    # Strip anything that looks like a schema
    repo_url = regex.sub(r"^.*://", "", repo_url)
    
    try:

      parsed_repo_url_namedtuple  = urlparse(url_scheme + repo_url)
      parsed_hostname             = str(parsed_repo_url_namedtuple.hostname)
      parsed_path                 = str(parsed_repo_url_namedtuple.path)

    except Exception as exception:

      error_string = "urlparse failed."
      exception.add_note(error_string)
      raise 

    # Log the parsed hostname and path
    logging.info("parsed_hostname: " + parsed_hostname )
    logging.info("parsed_path:     " + parsed_path     )

    # Check if the hostname is valid
    is_hostname_valid = validators.domain(parsed_hostname)
    if is_hostname_valid:

      logging.info("parsed_hostname is valid")

    else: 

      error_string = "Unsupported hostname provided: " + str(is_hostname_valid)
      logging.exception(error_string)
      sanitized_repo_url_messages.append(error_string)
      return None, sanitized_repo_url_messages

    # Clean up any extra junk that may be left in the host name
    hostname_substrings_to_remove = [
      "www.",
    ]

    # Loop through subStringsToRemove, warn the user, and remove them
    for subString in hostname_substrings_to_remove:
      if subString in parsed_hostname:
        sanitized_repo_url_messages.append("Removed: " + subString)
        parsed_hostname = parsed_hostname.replace(subString, "")

    # We don't need to accept all valid hostnames, only hostnames that match our code host config repo patterns on dotcom
    code_hostnames_on_dotcom = [
      "git.eclipse.org",
      "git.savannah.gnu.org",
      "git.savannah.gnu.org",
      "github.com",
      "gitlab.com",
    ]

    if parsed_hostname not in code_hostnames_on_dotcom:
      error_string = "Code host not on Sourcegraph.com: " + parsed_hostname
      logging.exception(error_string)
      sanitized_repo_url_messages.append(error_string)
      return None, sanitized_repo_url_messages

    # Remove @[ref] if present
    # Branch name, tag name, or commit hash
    # At this time, it appears that the embeddings job web UI https://sourcegraph.com/site-admin/embeddings doesn't support @refs, only default branch at head
    # This may change in the future, and would need to be removed then
    regexFilterForGitRefs = r"@[\w\d\./_-]*$"
    matches = regex.findall(regexFilterForGitRefs, repo_url)
    for match in matches:
      sanitized_repo_url_messages.append("Removed: " + match + ", only the HEAD revision of the default branch is supported for embeddings at this time.")
      repo_url = repo_url.replace(match,"")

    # Check if the repo path is valid
    # ".git",


    # Set the repo_url to only the hostname and path, to clean out a bunch of possible junk
    repo_url = parsed_hostname + parsed_path

    # Check if the URL is valid and publicly accessible
    is_url_valid_and_public = validators.url(url_scheme + repo_url, public = True)
    if is_url_valid_and_public:

      logging.info("URL is valid and public")

    else:

      error_string = "URL is not valid or public: " + str(is_url_valid_and_public)
      logging.exception(error_string)
      sanitized_repo_url_messages.append(error_string)
      return None, sanitized_repo_url_messages
    
    
    # Verify the repo exists, and is public
    # Only on valid public code hosts, to avoid users using this guess and check for hostname resolution on our internal network
    # This security check was completed earlier with "if parsed_hostname not in code_hostnames_on_dotcom:""
    # Try a get request for this repo_url
    try:
      response = requests.get(
        url=f"https://{repo_url}"
      )
    except Exception as get_request_exception:
      # We tried to get the repo from the matching code host, but that didn't go as expected
      logging.exception(get_request_exception)

    # Need to put more thought into what error states we could be in, and how we need to handle them
    if response.status_code == 200:
      logging.debug(f"Validated repo exists: https://{repo_url}")
      sanitized_repo_url_messages.append(f"Validated repo exists: https://{repo_url}")
    else:
      logging.error(f"Could not validate if repo exists: https://{repo_url}")
      sanitized_repo_url_messages.append(f"Could not validate if repo exists: https://{repo_url}")


    # If repo does exist, check if it's on Sourcegraph.com, or if there's a way to add it to the code host config too

  except Exception as exception:

    error_string = f"Failed to sanitize repo_url. \n Started with {initial_repo_url} \n Ended with {repo_url} \n Exception: {exception}"
    sanitized_repo_url_messages.append(error_string)
    exception.add_note(error_string)
    raise 

  return repo_url, sanitized_repo_url_messages


# Determine Sourcegraph server URL, dotcom by default
async def get_sourcegraph_server_addresses():

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
    sg_server = "".join(["https://",sg_server])

  # If it has .api/graphql, remove it
  if ".api/graphql" in sg_server:
    sg_server.replace(".api/graphql","")

  # If it ends with a trailing slash or two, remove it
  sg_server = sg_server.rstrip("/")

  # Append the /.api/graphql endpoint to the sg_server, to get the sg_server_api
  sg_server_api = "".join([sg_server,"/.api/graphql"])
  
  # Return both values
  return sg_server, sg_server_api


# Send the GraphQL API mutation to the Sourcegraph instance
async def send_graphql_request(sanitized_repo_url, sg_server_api):

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

    logging.error(f"GraphQL query timed out: {e}")
    message = "⚠️ Timed out submitting embeddings job to the Sourcegraph server, please try again!"
    success = False

  except Exception as e:

    logging.error(f"GraphQL query failed: {e} {response}")
    success = False

  if response.status_code == 200:

    logging.debug(f"GraphQL query connection succeeded: {response.status_code} {response.text}")
    success = True
    responseJson = json.loads(response.text)

    if responseJson.get("errors"):
      logging.error(f"GraphQL query returned errors: {response.text}")
      success = False,
      errors = responseJson.get("errors")
      message = errors

      if "repo not found" in response.text:
        messages = []
        for error in errors:
          messages.append(error.get("message"))
        message = "\n".join(messages)

  else:

    logging.error(f"GraphQL query connection failed: {response.status_code} {response.text}")
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

  error_state = False

  # Try / except block for Discord bot messages
  try:

    # Acknowledge the command, to avoid showing an error to the user, "The application did not respond"
    await ctx.send_response(
      content="Received /embedding command, creating new thread in this channel, and deleting this message.",
      ephemeral=True, # Only show this message to this user
      delete_after=10 # Delete this message after x seconds
    )

    # Sanitize the repo URL before responding to the Discord user, so the user can visually validate the sanitized repo URL is valid, and tag us for support if not
    sanitized_repo_url, sanitized_repo_url_messages = await sanitize_repo_url(repo_url)
    if sanitized_repo_url is None:
      thread_name = repo_url
      error_state = True
    else:
      thread_name = sanitized_repo_url

    # Create the thread to reply in
    thread = await ctx.interaction.channel.create_thread(
        name=thread_name,
        auto_archive_duration=60, # Auto archive this thread after x minutes
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

    # If we're in an error state, then end the processing here
    if error_state:
      await thread.send(
        content="❌ Terminating request"
      )
      return

    # Respond to the user's command
    await thread.send(
      content=f"Submitting {sanitized_repo_url} for embeddings on Sourcegraph.com",
      suppress=True
    )

    # Get the Sourcegraph server and GraphQL api endpoints
    sg_server, sg_server_api = await get_sourcegraph_server_addresses()

    # Get the return value and respond to the user
    graphqlSendSuccess, message = await send_graphql_request(sanitized_repo_url, sg_server_api)

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
    logging.exception(e)
    await thread.send(
      content=f"❌ Error occurred: {e}",
      suppress=True
    )


# Provide a healthcheck endpoint for the container / pod
async def healthcheck(request):
  logging.info("Healthcheck endpoint called - returned 200 OK response")
  return web.Response(text="OK")


async def start_web_server():
  app = web.Application()
  app.add_routes([web.get("/healthcheck", healthcheck)])
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, os.environ.get("HTTP_HOST"), os.environ.get("HTTP_PORT"))
  await site.start()


async def main():
  configure_logging()
  await start_web_server()


if __name__ == "__main__":
  asyncio.get_event_loop().run_until_complete(main())
  bot.run(DISCORD_TOKEN)
