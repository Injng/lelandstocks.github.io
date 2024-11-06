import json
import os
from collections import Counter
from datetime import datetime, timedelta
from glob import glob

import flask
import pandas as pd
from babel.numbers import format_currency
from flask import render_template
from scipy.stats import zscore
from zoneinfo import ZoneInfo

# this whole file is to render the html table
app = flask.Flask("leaderboard")


def get_five_number_summary(df):
    average_money = df["Money In Account"].mean()
    q1_money = df["Money In Account"].quantile(0.25)
    median_money = df["Money In Account"].median()
    q3_money = df["Money In Account"].quantile(0.75)
    std_money = df["Money In Account"].std()
    return average_money, q1_money, median_money, q3_money, std_money

def make_index_page():
     with app.app_context():
        leaderboard_files = sorted(
            glob("./backend/leaderboards/in_time/*")
        )  # This section formats everything nicely for the charts!
        labels = []
        min_monies = []
        max_monies = []
        q1_monies = []
        median_monies = []
        q3_monies = []
        for file in leaderboard_files:
            with open(file, "r") as file:
                dict_leaderboard = json.load(file)
            # Get a date time object from the file name, so I can use it as a label for the chart
            file_name = os.path.basename(file.name)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time_str = date_time_str.replace("_", ":")
            date_time_str = (
                datetime.strptime(date_time_str, "%Y-%m-%d-%H:%M")
                - timedelta(hours=3, minutes=0)
            ).strftime("%H:%M:%S %m-%d-%Y")  # The final string in the right format
            labels.append(date_time_str)

            df2 = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
            df2.reset_index(level=0, inplace=True)
            if (
                len(df2.columns) == 3
            ):  # IF the file has only 3 columns, then add a new column to the dataframe as a place holder
                df2["Stocks Invested In"] = [0 for i in range(len(df2))]
            df2.columns = [
                "Account Name",
                "Money In Account",
                "Stocks Invested In",
                "Investopedia Link",
            ]
            df2 = df2.sort_values(by=["Money In Account"], ascending=False)
            _1, q1_money, median_money, q3_money, _2 = get_five_number_summary(
                df2
            )  # get some key numbers for the charts
            min_monies.append(int(df2["Money In Account"].min()))
            max_monies.append(int(df2["Money In Account"].max()))
            q1_monies.append(int(q1_money))
            median_monies.append(int(median_money))
            q3_monies.append(int(q3_money))

        ### This whole section makes the Individual Statistics
        # Load json as dictionary, then organise it properly: https://stackoverflow.com/a/44607210
        with open("backend/leaderboards/leaderboard-latest.json", "r") as file:
            dict_leaderboard = json.load(file)
        df = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
        df.reset_index(level=0, inplace=True)
        df.columns = [
            "Account Name",
            "Money In Account",
            "Investopedia Link",
            "Stocks Invested In",
        ]
        df = df.sort_values(by=["Money In Account"], ascending=False)
        df["Ranking"] = range(1, 1 + len(df))
        all_stocks = []
        for stocks in df["Stocks Invested In"]:
            all_stocks.extend(stocks)
        stock_cnt = Counter(all_stocks)
        stock_cnt = stock_cnt.most_common()  # In order to determine the most common stocks. Now stock_cnt is a list of tuples
        df["Stocks Invested In"] = df["Stocks Invested In"].apply(
            lambda x: ", ".join(x)
        )
        df["Z-Score"] = zscore(df["Money In Account"])
        # Replace Account Name with Account Link
        df["Account Link"] = df.apply(
            lambda row: f'<a href="{row["Investopedia Link"]}" class= "underline text-blue-600 hover:text-blue-800 visited:text-purple-600" target="_blank">{row["Account Name"]}</a>',
            axis=1,
        )

        # This gets the location of the the GOAT himself, Mr. Miller
        miller_location = df.loc[
            df["Account Name"] == "teachermiller", "Ranking"
        ].values[0]

        # Drop the old Account Name and Investopedia Link columns
        df = df.drop(columns=["Account Name", "Investopedia Link"])

        # Rearrange columns with Account Link
        df = df[
            [
                "Ranking",
                "Account Link",
                "Money In Account",
                "Stocks Invested In",
                "Z-Score",
            ]
        ]

        # Update column_names
        column_names = [
            "Ranking",
            "Account Link",
            "Money In Account",
            "Stocks Invested In",
            "Z-Score",
        ]
        # This rearranges the columns to make things be in the right order
        average_money, q1_money, median_money, q3_money, std_money = (
            get_five_number_summary(df)
        )
        df["Money In Account"] = df["Money In Account"].apply(
            lambda x: format_currency(x, currency="USD", locale="en_US")
        )
        # Render the html template as shown here: https://stackoverflow.com/a/56296451
        rendered = render_template(
            "index.html",
            average_money="${:,.2f}".format(average_money),
            q1_money="${:,.2f}".format(q1_money),
            median_money="${:,.2f}".format(median_money),
            q3_money="${:,.2f}".format(q3_money),
            std_money="${:,.2f}".format(std_money),
            column_names=column_names,  # Updated column names
            row_data=list(df.values.tolist()),
            link_column="Account Link",  # Update link column
            update_time=datetime.utcnow()
            .astimezone(ZoneInfo("US/Pacific"))
            .strftime("%H:%M:%S %m-%d-%Y"),
            labels=labels,
            miller_location=miller_location,
            min_monies=min_monies,
            max_monies=max_monies,
            q1_monies=q1_monies,
            median_monies=median_monies,
            q3_monies=q3_monies,
            stock_cnt=stock_cnt,
            zip=zip,
        )
        return rendered

def make_user_page(player_name):
    with app.app_context():
        leaderboard_files = sorted(
            glob("./backend/leaderboards/in_time/*")
        )  # This section formats everything nicely for the charts!
        labels = []
        player_money = []
        rankings = []
        for file in leaderboard_files:
            with open(file, "r") as file:
                dict_leaderboard = json.load(file)
            # Get a date time object from the file name, so I can use it as a label for the chart
            file_name = os.path.basename(file.name)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time_str = date_time_str.replace("_", ":")
            date_time_str = (
                datetime.strptime(date_time_str, "%Y-%m-%d-%H:%M")
                - timedelta(hours=3, minutes=0)
            ).strftime("%H:%M:%S %m-%d-%Y")  # The final string in the right format
            labels.append(date_time_str)

            df = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
            df.reset_index(level=0, inplace=True)
            if (
                len(df.columns) == 3
            ):  # IF the file has only 3 columns, then add a new column to the dataframe as a place holder
                df["Stocks Invested In"] = [0 for i in range(len(df))]
            df.columns = [
                "Account Name",
                "Money In Account",
                "Stocks Invested In",
                "Investopedia Link",
            ]
            df = df.sort_values(by=["Money In Account"], ascending=False)
            df["Ranking"] = range(1, 1 + len(df))
            if player_name in df["Account Name"].values:
                rankings.append(
                    float(df.loc[df["Account Name"] == player_name, "Ranking"].values[0])
                )
                player_money.append(
                    float(df.loc[df["Account Name"] == player_name, "Money In Account"].values[0])
                )

        player_stocks = []
        print(df.loc[df["Account Name"] == player_name, "Stocks Invested In"])
        rendered = render_template(
            "player.html",
            labels=labels,
            player_money=player_money,
            player_name=player_name,
            player_stocks=player_stocks,  # Add player_stocks to template
            update_time=datetime.utcnow()
            .astimezone(ZoneInfo("US/Pacific"))
            .strftime("%H:%M:%S %m-%d-%Y"),
            zip=zip,
        )
        return rendered

if __name__ == "__main__":
    with app.app_context():
        ### This whole section makes the chart shown at the top of the page!
        print(make_index_page())
