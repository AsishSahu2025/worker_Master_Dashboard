#!/bin/bash

source /opt/venv/bin/activate
mkdir -p /app/logs

function terminate_processes {
    echo "Terminating processes..."
    pkill -f "python3 manage.py" || true
    pkill -f "Telegram_Bot_Admin.py" || true
    exit 0
}

trap terminate_processes SIGTERM SIGINT

echo "Starting Remote sensing script..."
python3 manage.py testing &> /app/logs/Remote_sensing.log &

echo "Starting voip..."
python3 manage.py voip &> /app/logs/voip.log &

echo "Starting Django server..."
python3 manage.py runserver 0.0.0.0:8000 &> /app/logs/django_server.log &

echo "Starting Telegram Bot..."
python3 Telegram_Bot_Admin.py &> /app/logs/telegram_bot.log &

echo "Starting Common Login backend..."

cd /commonlogin
python3 manage.py runserver 0.0.0.0:8001 &> /app/logs/commonlogin.log &
cd /app

echo "Starting subscribe_alerts..."
python3 manage.py subscribe_alerts &> /app/logs/subscribe_alerts.log &


echo "✅ All services started!"
echo "Django server: http://0.0.0.0:8000"

# keep container running
wait
