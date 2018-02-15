
# Mafiascum Mod Tool

Provides moderator tools and automation for mafiascum.net games.

# Features

* Filters many different things a mod might be interested in:
  * `@mod` notes to the mod
  * V/LA notices
  * Votes and unvotes
* Automatic vote counter
  * Username matching is more accurate than the robandkriskris.com counter (at least for Mini 1991)
  * Starts from the vote count starting on a given post instead of the start of the day. (With some limitations)
* Terminal colors
* Quote blocks are automatically filtered out
* ... More to come!

# Installation

You will need 3.4+ installed, plus the following packages from pip:

* fuzzywuzzy
* lxml
* requests
* (OPTIONAL) python-Levenshtein
