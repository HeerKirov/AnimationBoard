source venv/bin/activate
if [ -f "PID" ]; then
    kill $(cat PID)
    rm PID
fi
python3 manage.py crontab remove > /dev/null
deactivate