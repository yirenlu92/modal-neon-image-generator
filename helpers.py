import os
import requests
import psycopg2


class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_API_TOKEN")
        if not self.token:
            raise EnvironmentError("TELEGRAM_BOT_API_TOKEN is not set")

    def sendMessage(self, CHAT_ID, MESSAGE_TO_SEND):
        url = "https://api.telegram.org/bot{}/sendMessage".format(self.token)
        data = {"chat_id": CHAT_ID, "text": MESSAGE_TO_SEND}

        try:
            response = requests.post(url, data=data, timeout=20)
            if response.status_code != 200:
                print(f"Error sending message: {response.content}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")

    def sendPhoto(self, CHAT_ID, IMAGE_BYTES):
        url = "https://api.telegram.org/bot{}/sendPhoto".format(self.token)
        files = {"photo": ("output.png", IMAGE_BYTES)}

        try:
            response = requests.post(
                url, params={"chat_id": CHAT_ID}, files=files, timeout=20
            )
            if response.status_code != 200:
                print(f"Error sending photo: {response.content}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")

    def sendPhotoUploadAction(self, CHAT_ID):
        url = "https://api.telegram.org/bot{}/sendChatAction".format(self.token)
        data = {"chat_id": CHAT_ID, "action": "upload_photo"}

        try:
            response = requests.post(url, data=data, timeout=20)
            if response.status_code != 200:
                print(f"Error sending photo upload action: {response.content}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")


class Database:
    import psycopg2

    def __init__(self):
        DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")

        if not DB_CONNECTION_STRING:
            raise EnvironmentError("DB_CONNECTION_STRING is not set")

        self.conn = psycopg2.connect(DB_CONNECTION_STRING)
        self.conn.autocommit = True

    # Table has only two columns: user_id and credits
    def create_table(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, credits INT)"
            )

    # By default, all users have 10 free credits
    def create_user(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, credits) VALUES (%s, 10) ON CONFLICT (user_id) DO NOTHING",
                (user_id,),
            )

    # Get the number of credits for a user
    def get_credits(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT credits FROM users WHERE user_id = %s", (user_id,))
            # If user does not exist, create a new user with 10 credits
            if cur.rowcount == 0:
                self.create_user(user_id)
                return 10
            return cur.fetchone()[0]

    def update_credits(self, user_id, credits):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET credits = %s WHERE user_id = %s", (credits, user_id)
            )

    def decrement_credits(self, user_id):
        # Update credits to credits - 1 for the user
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET credits = credits - 1 WHERE user_id = %s",
                (user_id,),
            )

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    Database().create_table()
