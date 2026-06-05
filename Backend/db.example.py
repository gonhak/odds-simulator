import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR_PASSWORD", # hasło do lokalnego serwera Mysql
        database="insight_betting_simulator"
    )