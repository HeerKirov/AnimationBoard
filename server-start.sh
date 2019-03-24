source venv/bin/activate
nohup gunicorn AnimationBoard.wsgi:application -b 0.0.0.0:8000 --reload >> SERVER.LOG 2>&1 &
echo $! > PID
python3 manage.py crontab add > /dev/null
echo web server started.
deactivate