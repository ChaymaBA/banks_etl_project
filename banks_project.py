import requests
import sqlite3
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

url = "https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks"
exchange_rate_path = "./exchange_rate.csv"
table_attribs = ["Name", "MC_USD_Billion"]
output_path = "./Largest_banks.csv"
db_name = "Banks.db"
table_name = "Largest_banks"
log_file = "code_log.txt"


# Écrit un message avec la date et l'heure dans code_log.txt (journal des étapes)
def log_progress(message):
    timestamp_format = "%Y-%h-%d-%H:%M:%S"
    now = datetime.now().strftime(timestamp_format)
    with open(log_file, "a") as f:
        f.write(now + " : " + message + "\n")

# EXTRACT : récupère sur la page web le nom et la capitalisation (USD) de chaque banque, et renvoie un DataFrame
def extract(url, table_attribs):
    html_page = requests.get(url).text
    soup = BeautifulSoup(html_page, "html.parser")
    df = pd.DataFrame(columns=table_attribs)
    tables = soup.find_all("tbody")
    rows = tables[0].find_all("tr")
    for row in rows:
        col = row.find_all("td")
        if len(col) != 0:
            links = col[1].find_all("a")
            if len(links) > 1:
                name = links[1]["title"]
            else:
                name = col[1].get_text(strip=True)
            mc = float(col[2].get_text(strip=True).replace("\n", "").replace(",", ""))
            df = pd.concat(
                [df, pd.DataFrame({"Name": [name], "MC_USD_Billion": [mc]})],
                ignore_index=True,
            )
    return df

# TRANSFORM : lit les taux de change du CSV et ajoute les colonnes de capitalisation en GBP, EUR et INR
def transform(df, csv_path):
    exchange_df = pd.read_csv(csv_path)
    exchange_rate = exchange_df.set_index("Currency").to_dict()["Rate"]
    df["MC_GBP_Billion"] = [np.round(x * exchange_rate["GBP"], 2) for x in df["MC_USD_Billion"]]
    df["MC_EUR_Billion"] = [np.round(x * exchange_rate["EUR"], 2) for x in df["MC_USD_Billion"]]
    df["MC_INR_Billion"] = [np.round(x * exchange_rate["INR"], 2) for x in df["MC_USD_Billion"]]
    return df

# LOAD 1/2 :pour sauvegarde le DataFrame dans un fichier CSV

def load_to_csv(df, output_path):
    df.to_csv(output_path, index=False)

# LOAD 2/2: pour sauvegarde le DataFrame dans une table de la base de données SQLite

def load_to_db(df, sql_connection, table_name):
    df.to_sql(table_name, sql_connection, if_exists="replace", index=False)
# Exécute une requête SQL sur la base, affiche le résultat et note l'exécution dans le log

def run_query(query_statement, sql_connection):
    print(query_statement)
    query_output = pd.read_sql(query_statement, sql_connection)
    print(query_output)
    log_progress("Query executed: " + query_statement)


#p.p
log_progress("Preliminaries complete. Initiating ETL process")

df = extract(url, table_attribs)
print(df)
log_progress("Data extraction complete. Initiating Transformation process")

df = transform(df, exchange_rate_path)
log_progress("Data transformation complete. Initiating Loading process")

load_to_csv(df, output_path)
log_progress("Data saved to CSV file")

sql_connection = sqlite3.connect(db_name)
log_progress("SQL Connection initiated")

load_to_db(df, sql_connection, table_name)
log_progress("Data loaded to Database as a table, Executing queries")

run_query(f"SELECT * FROM {table_name}", sql_connection)
run_query(f"SELECT AVG(MC_GBP_Billion) FROM {table_name}", sql_connection)
run_query(f"SELECT Name FROM {table_name} LIMIT 5", sql_connection)

log_progress("Process Complete")
sql_connection.close()
log_progress("Server Connection closed")