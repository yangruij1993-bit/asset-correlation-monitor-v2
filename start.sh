#!/bin/bash
# Start backend + frontend in tmux (persistent)
# Usage: ./start.sh          — start
#        ./start.sh stop     — stop
#        ./start.sh status   — check status

SESSION="asset-monitor"
BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd)"

start() {
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "Session '$SESSION' already running. Use './start.sh stop' first."
        return 1
    fi

    tmux new-session -d -s "$SESSION" -c "$BACKEND_DIR"

    # Backend (port 8012, includes APScheduler strategy scheduler)
    tmux send-keys -t "$SESSION" "source $BACKEND_DIR/.venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8012" Enter

    # Frontend
    tmux new-window -t "$SESSION" -n frontend -c "$FRONTEND_DIR"
    tmux send-keys -t "$SESSION:frontend" "npx next dev -p 3012" Enter

    echo "Started asset-monitor in tmux session '$SESSION'"
    echo "  Backend:  http://localhost:8012  (includes strategy scheduler)"
    echo "  Frontend: http://localhost:3012"
    echo ""
    echo "Attach:  tmux attach -t $SESSION"
    echo "Stop:    ./start.sh stop"
}

stop() {
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "Session '$SESSION' not running."
        return 0
    fi
    tmux kill-session -t "$SESSION"
    echo "Stopped '$SESSION'"
}

status() {
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "Session '$SESSION' is running:"
        tmux list-windows -t "$SESSION"
        echo ""
        HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8012/api/v1/health 2>/dev/null)
        [ "$HEALTH" = "200" ] && echo "  Backend:  OK" || echo "  Backend:  DOWN"
        FE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3012 2>/dev/null)
        [ "$FE" = "200" ] && echo "  Frontend: OK" || echo "  Frontend: DOWN"
    else
        echo "Session '$SESSION' is NOT running."
    fi
}

case "${1:-start}" in
    start)  start  ;;
    stop)   stop   ;;
    status) status ;;
    *)      echo "Usage: $0 {start|stop|status}" ;;
esac
