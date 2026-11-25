from datetime import timedelta

ACCESS_TOKEN_HEADER = "X-Access-Token"
REFRESH_TOKEN_HEADER = "X-Access-Token"
ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_LIFETIME = timedelta(days=1)
INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."
