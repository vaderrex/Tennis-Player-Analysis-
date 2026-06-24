import os
import sys
sys.path.append(r"c:\Users\npsta\Downloads\Tennis\Tennis")

from tennis_etl.database import build_engine
from tennis_etl.config import Settings
from sqlalchemy import text

s = Settings.from_environment()
e = build_engine(s.database_url)

with e.connect() as conn:
    print("--- Inspecting FACT_Rankings for Wins/Losses/WinPercentage ---")
    sql = """
    SELECT TOP 10 
        Rank, Points, CompetitionsPlayed, RankMovement, 
        Wins, Losses, WinPercentage 
    FROM FACT_Rankings
    """
    res = conn.execute(text(sql)).fetchall()
    for row in res:
        print(row)
