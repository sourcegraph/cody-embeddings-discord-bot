# Cody Embeddings Discord Bot 

The Cody Embeddings Discord Bot is an exciting new way to create code embeddings directly from Discord! This bot, written in Python, allows you to simply enter a GitHub repository URL in Discord and the bot will request an embedding for that repo from Sourcegraph.

## Request Embeddings

This `discordbot.py` script does the following:

- [`embedding`](https://sourcegraph.com/github.com/sourcegraph/cody-embeddings-discord-bot/-/blob/discordbot.py?L62) accepts Git repository url from Discord registered by slash_command API
- [`send_graphql_request`](https://sourcegraph.com/github.com/sourcegraph/cody-embeddings-discord-bot/-/blob/discordbot.py?L30) submits the repository url to Sourcegraph API to request embedding via GraphQL

## Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot locally
SG_TOKEN="SOURCEGRAPH_SITE_ADMIN_TOKEN" DISCORD_TOKEN="DISCORD_BOT_TOKEN" python discordbot.py
```

## Updating the script

The Docker image is published to GCP Container Registry in the `cody-embeddings-discord-bot` project. Once the script is updated do the following to publish the Docker image:

```bash
# Build Docker image
docker build -t cody-embedding-discord-bot .

# Tag the image
docker tag cody-embedding-discord-bot us-central1-docker.pkg.dev/cody-embeddings-discord-bot/cody-embeddings-discord-bot/cody-embedding-discord-bot

# Push the image
docker push us-central1-docker.pkg.dev/cody-embeddings-discord-bot/cody-embeddings-discord-bot/cody-embedding-discord-bot
```

*Before building the Docker image, make sure the Docker base image has an AMD64 architecture. If you are building the Docker image on an Apple Silicon machine, you can use the `docker buildx build --platform linux/amd64 .` command to specify the AMD64 architecture. This will ensure the Docker image is compatible with AMD64 systems.*