import datetime
import json
import os
import sys

import pytz
from PCSOLotto import PCSOLotto

OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'lotto-results.json')

# PCSO draws each 6-number game three times a week and the digit games daily,
# so a two week window always contains at least one draw for every game.
LOOKBACK_DAYS = 14

# Games whose PCSO name doesn't slugify to a stable id on its own, because the
# site spells them inconsistently ("Superlotto 6/49" vs "Super Lotto 6/49").
GAME_ID_BY_TOKEN = [
    ('6/58', 'ultra-lotto-6-58'),
    ('6/55', 'grand-lotto-6-55'),
    ('6/49', 'super-lotto-6-49'),
    ('6/45', 'mega-lotto-6-45'),
    ('6/42', 'lotto-6-42'),
]


def game_id(game_name):
    """Map a PCSO game name to the stable id the frontend renders."""
    for token, slug in GAME_ID_BY_TOKEN:
        if token in game_name:
            return slug

    # Everything else (6D, 4D, 3D, 2D, and any game PCSO adds later) keeps a
    # slug derived from its own name, so new games show up without a code change.
    slug = ''.join(c.lower() if c.isalnum() else '-' for c in game_name)
    return '-'.join(part for part in slug.split('-') if part)


def scrape_latest_results():
    """Return the most recent draw for every game PCSO published recently."""
    lotto = PCSOLotto()

    manila_now = datetime.datetime.now(pytz.timezone('Asia/Manila'))
    start_date = manila_now - datetime.timedelta(days=LOOKBACK_DAYS)

    print(f"Searching PCSO results from "
          f"{start_date.strftime('%Y/%m/%d')} to {manila_now.strftime('%Y/%m/%d')}...")

    # results() is keyed by draw date, then by game name:
    #   {'2026/08/14': {'Ultra Lotto 6/58': {'combinations': [...], ...}}}
    scraped_data = lotto.results(
        start_date=start_date.strftime('%Y/%m/%d'),
        end_date=manila_now.strftime('%Y/%m/%d'),
    )

    latest = {}
    for draw_date, games in scraped_data.items():
        for game_name, details in games.items():
            entry = {
                'name': game_name,
                'combination': '-'.join(details.get('combinations', [])),
                'draw_date': draw_date.replace('/', '-'),
                'jackpot': details.get('jackpot', ''),
                'winners': details.get('winners', 0),
            }

            # A game can be drawn several times inside the window; keep the newest.
            current = latest.get(game_id(game_name))
            if current is None or entry['draw_date'] > current['draw_date']:
                latest[game_id(game_name)] = entry

    return latest


def load_existing_games():
    """Previously saved results, so games without a draw today aren't dropped."""
    try:
        with open(OUTPUT_FILE) as f:
            return json.load(f).get('games', {})
    except (OSError, ValueError):
        return {}


def main():
    print('Initializing PCSO Lotto Scraper...')

    try:
        latest = scrape_latest_results()
    except (TypeError, AttributeError, IndexError) as e:
        # The search form is missing from the page PCSO returned. That is almost
        # always their edge blocking the request rather than a parsing bug --
        # PCSO refuses many datacenter/CI IP ranges with an "Access Denied" page.
        print(f'Error: PCSO did not return the expected results page ({e}).')
        print('The request was most likely blocked. Existing data left untouched.')
        return 1
    except Exception as e:
        print(f'Error scraping data: {e}')
        print('Existing data left untouched.')
        return 1

    if not latest:
        print('Error: PCSO returned no draws for the search window.')
        print('Existing data left untouched.')
        return 1

    # Merge over the saved results so every game keeps its most recent draw,
    # even on days when that game isn't drawn at all.
    games = load_existing_games()
    for slug, entry in latest.items():
        saved = games.get(slug)
        if saved is None or entry['draw_date'] >= saved.get('draw_date', ''):
            games[slug] = entry

    payload = {
        'generated_at': datetime.datetime.now(
            pytz.timezone('Asia/Manila')).isoformat(timespec='seconds'),
        'games': dict(sorted(games.items())),
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(payload, f, indent=4)
        f.write('\n')

    print(f'Wrote {len(games)} games to lotto-results.json '
          f'({len(latest)} refreshed from this run).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
