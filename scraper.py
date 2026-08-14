import json
import datetime
from PCSOLotto import PCSOLotto

def scrape_latest_results():
    print("Initializing PCSO Lotto Scraper...")
    
    try:
        lotto = PCSOLotto()
        
        # Attempt to fetch today's results (Usually posted after 10 PM)
        scraped_data = lotto.results_today()
        
        # Fallback: If tonight's results aren't up yet, grab the default recent draws
        if not scraped_data:
            print("Tonight's results not yet posted. Fetching recent defaults...")
            scraped_data = lotto.results_default_pcso()
        
        formatted_data = {}
        today_date = datetime.datetime.now().strftime("%b %d, %Y")
        
        # Loop through the scraped data to extract only the 6/58 and 6/55 games
        for game_name, game_details in scraped_data.items():
            if '6/58' in game_name:
                formatted_data["6/58"] = {
                    "date": today_date,
                    "combination": game_details.get('Winning Numbers', ''),
                    "jackpot": game_details.get('Jackpot Prize', '')
                }
            elif '6/55' in game_name:
                formatted_data["6/55"] = {
                    "date": today_date,
                    "combination": game_details.get('Winning Numbers', ''),
                    "jackpot": game_details.get('Jackpot Prize', '')
                }
        
        # Write the formatted data into the JSON file that our website reads
        with open('lotto-results.json', 'w') as f:
            json.dump(formatted_data, f, indent=4)
            
        print("Successfully generated lotto-results.json with live data!")

    except Exception as e:
        print(f"Error scraping data: {e}")

if __name__ == "__main__":
    scrape_latest_results()
