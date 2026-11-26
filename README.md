# MCPedia

This is a discord bot integrating [the Minecraft wiki](minecraft.wiki) and other useful features to help with playing Minecraft and sharing information on Discord.\
Right now the bot itself isn't publicly available, but I have plans to change that in the future.

## What's happening with the project?
Bot won't be publicly available for the time being, as I don't a host for it. Once I got time to look into hosting options, I will cleanup the repo from unnecesseary files and hopefully open the bot to the public

## Tests

The unit tests live in `tests/` and run fully offline: wiki/HTTP calls, Discord
contexts and interactions are mocked, so no token or network access is needed.

```sh
python3.11 -m venv .venv
.venv/bin/pip install pytest pytest-asyncio py-cord pymediawiki beautifulsoup4 \
    requests Pillow aiohttp python-dotenv
.venv/bin/python -m pytest
```

Use Python 3.10 or 3.11 – `py-cord` 2.4 relies on the removed `audioop` module
on newer Python versions. `pytest` must be able to import the project root,
which the test setup handles automatically.

### Live wiki contract tests

`tests/test_wiki_api_integration.py` checks the assumptions the cogs make
against the real Minecraft Wiki API (search results, table-of-contents shape,
infobox/crafting-grid markup and villager trade tables). It also runs `/wiki`
end to end for a range of phrases that produce different content types —
disambiguations (`gold`), mobs, items, blocks, biomes, dimensions, mechanics,
people, redstone and commands — asserting the resolved page title, the
expected embed/select structure, and that every generated section embed obeys
Discord's field/size limits. They are skipped by default so normal test runs
stay offline; opt in with:

```sh
MCPEDIA_RUN_INTEGRATION=1 pytest -m integration
```

These are intentionally sensitive to wiki changes: a failure means the wiki
markup or API contract drifted and a parser needs updating.
Bot won't be publicly available for the time being, as I don't have a host for it. Once I got time to look into hosting options, I will cleanup the repo from unnecesseary files and hopefully open the bot to the public
