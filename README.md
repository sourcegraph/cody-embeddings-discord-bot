# Cody Embeddings Discord Bot 

The Cody Embeddings Discord Bot is an exciting new way to create code embeddings directly from Discord! This bot, written in Python, allows you to simply enter a GitHub repository URL in Discord and the bot will request an embedding for that repo from Sourcegraph.

## Request Embeddings

This `discordbot.py` script does the following:

- [`embedding`](https://sourcegraph.com/github.com/sourcegraph/cody-embeddings-discord-bot/-/blob/discordbot.py?L62) accepts Git repository url from Discord registered by slash_command API
- [`send_graphql_request`](https://sourcegraph.com/github.com/sourcegraph/cody-embeddings-discord-bot/-/blob/discordbot.py?L30) submits the repository url to Sourcegraph API to request embedding via GraphQL

## Testing Locally

Retrieve [Discord dev_cody_embeddings_bot token from 1Password](https://start.1password.com/open/i?a=HEDEDSLHPBFGRBTKAKJWE23XX4&v=dnrhbauihkhjs5ag6vszsme45a&i=7v7petpsowuvd7iwl6xhfg34ey&h=my.1password.com)

See the [cody-embeddings-test channel](https://discord.com/channels/969688426372825169/1126274921820074096) to interact with the bot while running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot locally
SG_TOKEN="SOURCEGRAPH_SITE_ADMIN_TOKEN" DISCORD_TOKEN="DISCORD_BOT_TOKEN" python3 discordbot.py

# Optional environment variables

LOGLEVEL=DEBUG # Increases log output
MODE=DEV # Changes log output formatting for human readability
SG_SERVER="sourcegraph.com" # Can specify your own Sourcegraph server

# To run the Docker image locally
# Build the image
docker build -t cody-embedding-discord-bot .

# Run with env vars
docker run \
--env SG_TOKEN="Your Sourcegraph token" \
--env DISCORD_TOKEN="The Discord token" \
cody-embedding-discord-bot
```

## Updating the script

The Docker image is published to GCP Container Registry in the `cody-embeddings-discord-bot` project. Once the script is updated do the following to publish the Docker image:

```bash
# Build Docker image
docker build -t cody-embedding-discord-bot .

# If you're on an M1 / M2 mac
docker buildx build --platform linux/amd64 .

# Tag the image
docker tag cody-embedding-discord-bot us-central1-docker.pkg.dev/cody-embeddings-discord-bot/cody-embeddings-discord-bot/cody-embedding-discord-bot

# Push the image
docker push us-central1-docker.pkg.dev/cody-embeddings-discord-bot/cody-embeddings-discord-bot/cody-embedding-discord-bot
```

*Before building the Docker image, make sure the Docker base image has an AMD64 architecture. If you are building the Docker image on an Apple Silicon machine, you can use the `docker buildx build --platform linux/amd64 .` command to specify the AMD64 architecture. This will ensure the Docker image is compatible with AMD64 systems.*