#!/bin/bash
echo "Writing rogue .env file to ~/Desktop to simulate an untrusted cloud config dump..."
touch ~/Desktop/.env
echo "SUCCESS: Triggered. Wait a few seconds for the macOS native UI Alert to pop up!"
sleep 2
rm ~/Desktop/.env
echo "Test complete."
