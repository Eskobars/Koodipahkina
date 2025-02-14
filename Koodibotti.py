import requests
from config import TOKEN, API_URL

class Player:
    def __init__(self, name):
        self.name = name
        self.money = 11
        self.cards = []

    def calculate_points(self):
        card_points = sum(min(series) for series in self.cards if series)
        return card_points - self.money

    def add_card(self, card):
        for series in self.cards:
            if card == series[-1] + 1:
                series.append(card)
                return
            elif card == series[0] - 1:
                series.insert(0, card)
                return
        self.cards.append([card])

    def __str__(self):
        return f"{self.name}: Money={self.money}, Cards={self.cards}, Points={self.calculate_points()}"

class Game:
    API_URL = "https://koodipahkina.monad.fi/api/game"

    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.game_id = None
        self.status = None

    def create_game(self):
        response = requests.post(f"{API_URL}", headers=self.headers)
        if response.status_code == 200:
            game_data = response.json()
            self.game_id = game_data["gameId"]
            self.status = game_data["status"]
            print("Game created successfully.")
        else:
            print("Failed to create game:", response.json())

    def send_action(self, take_card):
        action = {"takeCard": take_card}
        try:
            response = requests.post(f"{self.API_URL}/{self.game_id}/action", headers=self.headers, json=action)
            if response.status_code == 200:
                try:
                    self.status = response.json()["status"]
                except ValueError:
                    print("Failed to decode JSON from server response.")
            else:
                print(f"Failed to send action: HTTP {response.status_code}")
                print("Response content:", response.text)
        except requests.exceptions.RequestException as e:
            print(f"Network error while sending action: {e}")

    def calculate_final_scores(self):
        final_scores = {}
        for player in self.status["players"]:
            card_points = sum(min(series) for series in player["cards"] if series)
            money = player["money"]
            total_points = card_points - money
            final_scores[player["name"]] = {
                "score": total_points,
                "money_left": money
            }
        return final_scores

    def play(self):
        while not self.status["finished"]:
            current_card = self.status["card"]
            coins_on_card = self.status["money"]
            players = self.status["players"]
            current_player = players[0]

            print(f"Current card: {current_card} with {coins_on_card} coins")
            print(f"{current_player['name']}'s turn (Money: {current_player['money']})")

            if current_player["money"] == 0:
                print(f"{current_player['name']} is forced to take the card!")
                self.send_action(take_card=True)
            else:
                if self.should_bet(current_card, coins_on_card, current_player):
                    print(f"{current_player['name']} bets a coin on the card.")
                    self.send_action(take_card=False)
                else:
                    print(f"{current_player['name']} takes the card and {coins_on_card} coins.")
                    self.send_action(take_card=True)

        print("\nGame Over! Final Scores:")
        final_scores = self.calculate_final_scores()

        print(f"{'Name':<15} {'Score':<10} {'Money Left':<12} {'Cards'}")
        print("-" * 50)

        for player_data in self.status["players"]:
            name = player_data["name"]
            score = final_scores[name]["score"]
            money_left = final_scores[name]["money_left"]
            cards = player_data["cards"]
            
            formatted_cards = ', '.join(map(str, cards))
            
            print(f"{name:<15} {score:<10} {money_left:<12} {formatted_cards}")
    
    def fits_in_series(self, card, player):
        return any(
            card == max(series) + 1 or card == min(series) - 1
            for series in player["cards"]
        )

    def should_bet(self, card, coins, player):
        is_start_of_game = self.status["cardsLeft"] >= 15
        is_middle_game =  5 < self.status["cardsLeft"] < 15
        is_endgame = self.status["cardsLeft"] <= 5
        enough_money_to_end_round = player["money"] >= self.status["cardsLeft"] * 2
        fits_series = self.fits_in_series(card, player)

        # Always collect cards that have more coins than the value of the card
        if coins >= card: 
            return False
        
        # Always collect a card if it fits a series
        if fits_series:
            return False

        # Collect coins and avoid high value cards at the start of the game
        if is_start_of_game:
            if coins >= 9:
                return False
            if player["money"] > 10 and card > 15:
                return True
            
        # Avoid taking high value cards at the middle of the game
        if is_middle_game and card >= 20:
            return True

        # At the end of the game we avoid high value cards
        if is_endgame:
            if card >= 25:
                return True
            
        # Bet if there's enough money to end the round
        if enough_money_to_end_round:
            return True

        return True

if __name__ == "__main__":
    game = Game(TOKEN)

    # Set the number of games to play
    number_of_games = 20

    for i in range(number_of_games):
        print(f"\nStarting Game {i + 1}...")
        game.create_game()
        game.play()

    print(f"\n{number_of_games} games have been played.")