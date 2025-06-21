
import logging
import yaml
import sys
import os
from typing import TypedDict
from datetime import datetime

with open("config.yml", "r") as f: config = yaml.safe_load(f)

class TrainingDataLogger:
    def __init__(self, name):
        self.name = name
        self.log_file = f"{config['logging']["logs_dir"]}/{config['logging']['training']["file"]}"

    def log(self, data: dict):
        data["time"] = datetime.now().timestamp()
        with open(self.log_file, "a") as f:
            f.write(f"{dict(data)}\n")