#!/bin/bash

# Activate virtual environment
source /opt/venv/bin/activate

# Ensure /app/logs directory exists
mkdir -p /app/logs

# Function to handle process termination
function terminate_processes {
    echo "Terminating processes..."
    pkill -f "python3 manage.py"
    pkill -f "daphne"
    exit
}

# Trap SIGTERM signal to gracefully terminate processes
trap terminate_processes SIGTERM

# Run Remote sensing script and handle errors
echo "Starting Remote sensing script..."
python3 manage.py testing &> /app/logs/Remote_sensing.log &
if [ $? -ne 0 ]; then
    echo "Error starting Remote sensing script..."
    exit 1
fi

# Run voip and handle errors
echo "Starting voip..."
python3 manage.py voip &> /app/logs/voip.log &
if [ $? -ne 0 ]; then
    echo "Error starting voip"
    exit 1
fi

# Start Daphne server and handle errors
echo "Starting Django server..."
python3 manage.py runserver 0.0.0.0:8000 &> /app/logs/django_server.log &
if [ $? -ne 0 ]; then
    echo "Error starting Django server"
    exit 1
fi

# Run Telegram Bot in the foreground
echo "Starting Telegram Bot in the foreground..."
python3 manage.py Telegram_Bot &> /app/logs/telegram_bot.log
if [ $? -ne 0 ]; then
    echo "Error running Telegram Bot"
    exit 1
fi

# Start subscribe_alerts in background
echo "Starting subscribe_alerts..."
python manage.py subscribe_alerts &

echo "✅ All services started!"
echo "Django server: http://0.0.0.0:8000"
echo "MQTT subscriber: Running in background"
# Keep container running
wait