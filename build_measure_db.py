import argparse
from app import app, db
from models import rebuild_plot_database, rebuild_measure_database

if __name__ == "__main__":
    print("Building database from %s"%app.config['GLOBAL_MEASURES_PATH'])
    rebuild_measure_database()
    rebuild_plot_database()
