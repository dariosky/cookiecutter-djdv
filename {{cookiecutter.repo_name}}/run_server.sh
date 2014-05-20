#!/bin/bash{ % raw %}
GUNICORN_CMD={VENV_FOLDER}/bin/gunicorn
GUNICORN_ARGS="{GUNICORN_ARGUMENTS}"
PYTHONPATH={VENV_FOLDER}
LOG_PATH={GUNICORN_LOGFILE}
PID_PATH={GUNICORN_PID_FILE}
PORT={GUNICORN_PORT}

start_server () {{
  if [ -f $PID_PATH ]; then
    if [ "$(ps -p `cat $PID_PATH` | wc -l)" -gt 1 ]; then
       echo "A server is already running on port $PORT"
       return
    else
    	echo "We have the PID but not the process deleting PID and restarting" >&2
    	rm -f $PID_PATH
    fi
  fi
  cd {VENV_FOLDER}
  echo "starting gunicorn on port $PORT"
  exec $GUNICORN_CMD $GUNICORN_ARGS -b 127.0.0.1:$PORT --log-file $LOG_PATH --pid $PID_PATH {WSGI_APPLICATION}
}}

stop_server () {{
  if [ -f $PID_PATH ] && [ "$(ps -p `cat $PID_PATH` | wc -l)" -gt 1 ]; then
    echo "stopping server on port $PORT"
    kill -9  `cat $PID_PATH`
    rm -f $PID_PATH
  else
    if [ -f $PID_PATH ]; then
      echo "server not running"
      rm -f $PID_PATH
    else
      echo "No pid file found for server"
    fi
  fi
}}

case "$1" in
'start')
  start_server
  ;;
'stop')
  stop_server
  ;;
'restart')
  stop_server
  sleep 2
  start_server
  ;;
*)
  echo "Usage: $0 {{ start | stop | restart }}"
  ;;
esac

exit 0
#exec $GUNICORN_CMD $GUNICORN_ARGS -b 127.0.0.1:$PORT --log-file $LOG_PATH --pid $PID_PATH {WSGI_APPLICATION}
{ % endraw %}
