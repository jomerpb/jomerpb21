"""Collect the latest PCSO draw results and write them to lotto-results.json.

PCSO's own site (pcso.gov.ph) answers every request from CI with a 403 from its
CDN, so results are read from lottopcso.com, which republishes them and whose
robots.txt allows the homepage this reads.
"""

import datetime
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

SOURCE_URL = 'https://www.lottopcso.com/'
OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'lotto-results.json')

REQUEST_HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/126.0.0.0 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9',
}

# The source spells the jackpot games "6/58 Ultra Lotto"; the site's own wording
# is kept for display, but the id has to stay stable for the frontend.
GAME_ID_BY_TOKEN = [
    ('6/58', 'ultra-lotto-6-58'),
    ('6/55', 'grand-lotto-6-55'),
    ('6/49', 'super-lotto-6-49'),
    ('6/45', 'mega-lotto-6-45'),
    ('6/42', 'lotto-6-42'),
]

# Rows labelling the combination in a jackpot game's table.
COMBINATION_LABELS = ('winning combination', 'combination')

# Rows carrying the prize in a jackpot or digit game's table.
JACKPOT_LABELS = ('jackpot prize', 'first prize')

WINNER_LABELS = ('jackpot winner', 'number of winner')

# A draw time, e.g. "9:00 PM", which is how the digit games label their rows.
DRAW_TIME = re.compile(r'^\d{1,2}:\d{2}\s*(AM|PM)$', re.IGNORECASE)

# A combination, e.g. "28-33-10-12-22-23" or "5-0-3".
COMBINATION = re.compile(r'^\d{1,2}(-\d{1,2})+$')


def slugify(text):
    slug = ''.join(c.lower() if c.isalnum() else '-' for c in text)
    return '-'.join(part for part in slug.split('-') if part)


def game_id(game_name, draw_time=None):
    """Build the stable id the frontend renders a game under."""
    for token, slug in GAME_ID_BY_TOKEN:
        if token in game_name:
            return slug

    slug = slugify(game_name)
    if draw_time:
        # "3D Lotto" + "9:00 PM" -> "3d-lotto-9pm", so each draw gets its own card.
        slug += '-' + slugify(draw_time).replace('-00-', '').replace('-', '')
    return slug


def parse_date(text):
    """Turn the source's "August 14, 2026" heading into "2026-08-14"."""
    for fmt in ('%B %d, %Y', '%b. %d, %Y', '%b %d, %Y'):
        try:
            return datetime.datetime.strptime(text.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def clean_prize(text):
    """The source prints "*" for a prize it hasn't published yet."""
    text = text.strip()
    return '' if text in ('*', '-', 'TBA') else text


def parse_winners(text):
    digits = re.sub(r'[^\d]', '', text.split('(')[0])
    return int(digits) if digits else None


def parse_results(html):
    """Read every game table on the page into {game_id: result}."""
    soup = BeautifulSoup(html, 'html.parser')
    games = {}

    for table in soup.find_all('table'):
        rows = [[cell.get_text(' ', strip=True)
                 for cell in row.find_all(['td', 'th'])]
                for row in table.find_all('tr')]
        rows = [row for row in rows if row]

        # A game table's header is the game name next to its draw date. Tables
        # that aren't a single game's result (prize claiming, jackpot summaries,
        # past winners) don't match and are skipped.
        if not rows or len(rows[0]) != 2:
            continue

        game_name = rows[0][0]
        draw_date = parse_date(rows[0][1])
        if not draw_date:
            continue

        combination = None
        jackpot = ''
        winners = None
        timed_draws = []

        for row in rows[1:]:
            if len(row) != 2:
                continue
            label, value = row[0].strip(), row[1].strip()
            lowered = label.lower()

            if DRAW_TIME.match(label) and COMBINATION.match(value):
                timed_draws.append((label, value))
            elif any(lowered.startswith(l) for l in COMBINATION_LABELS):
                combination = value
            elif any(lowered.startswith(l) for l in JACKPOT_LABELS):
                jackpot = clean_prize(value)
            elif any(lowered.startswith(l) for l in WINNER_LABELS) and winners is None:
                winners = parse_winners(value)

        if combination and COMBINATION.match(combination):
            # A jackpot game: one draw, listed as "Winning Combination".
            add_result(games, game_id(game_name), {
                'name': game_name,
                'combination': combination,
                'draw_date': draw_date,
                'jackpot': jackpot,
                'winners': winners,
            })
        elif len(timed_draws) == 1:
            # 4D and 6D are drawn once a day, so the time isn't worth a
            # separate card and the table's prize belongs to that one draw.
            add_result(games, game_id(game_name), {
                'name': game_name,
                'combination': timed_draws[0][1],
                'draw_date': draw_date,
                'jackpot': jackpot,
                'winners': winners,
            })
        else:
            # 3D, 2D and STL are drawn several times a day, each its own card.
            for draw_time, value in timed_draws:
                add_result(games, game_id(game_name, draw_time), {
                    'name': f'{game_name} {draw_time}',
                    'combination': value,
                    'draw_date': draw_date,
                    'jackpot': '',
                    'winners': None,
                })

    return games


def add_result(games, slug, entry):
    """Keep the newest draw when a game appears more than once on the page."""
    current = games.get(slug)
    if current is None or entry['draw_date'] > current['draw_date']:
        games[slug] = entry


def load_existing_games():
    """Previously saved results, so games without a draw today aren't dropped."""
    try:
        with open(OUTPUT_FILE) as f:
            return json.load(f).get('games', {})
    except (OSError, ValueError):
        return {}


def main():
    print(f'Fetching results from {SOURCE_URL}...')

    try:
        response = requests.get(SOURCE_URL, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f'Error: could not reach the results source ({e}).')
        print('Existing data left untouched.')
        return 1

    latest = parse_results(response.text)

    if not latest:
        # Better to keep serving yesterday's real results than to guess at
        # today's, so nothing is written and the failure is loud.
        print('Error: no results found on the page. The layout has likely changed.')
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
            ZoneInfo('Asia/Manila')).isoformat(timespec='seconds'),
        'source': SOURCE_URL,
        'games': dict(sorted(games.items())),
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
        f.write('\n')

    print(f'Wrote {len(games)} games to lotto-results.json '
          f'({len(latest)} refreshed from this run).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
