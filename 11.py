import os
from dotenv import load_dotenv

print(load_dotenv())
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

print("JWT_SECRET_KEY =", JWT_SECRET_KEY)