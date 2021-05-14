#!/bin/bash

echo "Enter Github username: "

read USERNAME

sed -i "360s/$/ '${USERNAME}'/" dependency_analyzer_const.py

echo "Enter Github personal access token: "

read TOKEN

sed -i "361s/$/ '${TOKEN}'/" dependency_analyzer_const.py
