#!/bin/bash
# Quick commands for managing the diploma_work application

echo "🎓 Diploma Work - Quick Commands"
echo "================================"
echo ""

# Function to show menu
show_menu() {
    echo "Select an option:"
    echo ""
    echo "1)  Start all services"
    echo "2)  Stop all services"
    echo "3)  Restart all services"
    echo "4)  View all logs"
    echo "5)  View backend logs"
    echo "6)  View database logs"
    echo "7)  View frontend logs"
    echo "8)  View parser logs"
    echo "9)  Check service status"
    echo "10) Rebuild all services"
    echo "11) Clean up (remove containers and volumes)"
    echo "12) Open backend API (browser)"
    echo "13) Open frontend (browser)"
    echo "14) Database shell (psql)"
    echo "15) Backend shell (bash)"
    echo "0)  Exit"
    echo ""
}

# Main loop
while true; do
    show_menu
    read -p "Enter choice [0-15]: " choice
    echo ""
    
    case $choice in
        1)
            echo "🚀 Starting all services..."
            docker-compose up -d
            ;;
        2)
            echo "🛑 Stopping all services..."
            docker-compose down
            ;;
        3)
            echo "🔄 Restarting all services..."
            docker-compose restart
            ;;
        4)
            echo "📜 Showing all logs (Ctrl+C to exit)..."
            docker-compose logs -f
            ;;
        5)
            echo "📜 Showing backend logs (Ctrl+C to exit)..."
            docker-compose logs -f backend
            ;;
        6)
            echo "📜 Showing database logs (Ctrl+C to exit)..."
            docker-compose logs -f db
            ;;
        7)
            echo "📜 Showing frontend logs (Ctrl+C to exit)..."
            docker-compose logs -f frontend
            ;;
        8)
            echo "📜 Showing parser logs (Ctrl+C to exit)..."
            docker-compose logs -f parser-service
            ;;
        9)
            echo "📊 Service status:"
            docker-compose ps
            echo ""
            echo "🔍 Health check:"
            curl -s http://localhost:8000/health | jq . || echo "Backend not responding"
            ;;
        10)
            echo "🔨 Rebuilding all services..."
            docker-compose up --build -d
            ;;
        11)
            echo "⚠️  This will remove all containers and volumes!"
            read -p "Are you sure? (y/N): " confirm
            if [[ $confirm == "y" || $confirm == "Y" ]]; then
                docker-compose down -v
                echo "✅ Cleaned up"
            else
                echo "❌ Cancelled"
            fi
            ;;
        12)
            echo "🌐 Opening backend API..."
            if command -v xdg-open &> /dev/null; then
                xdg-open http://localhost:8000/docs
            elif command -v open &> /dev/null; then
                open http://localhost:8000/docs
            else
                start http://localhost:8000/docs
            fi
            ;;
        13)
            echo "🌐 Opening frontend..."
            if command -v xdg-open &> /dev/null; then
                xdg-open http://localhost
            elif command -v open &> /dev/null; then
                open http://localhost
            else
                start http://localhost
            fi
            ;;
        14)
            echo "💾 Opening database shell..."
            docker-compose exec db psql -U postgres -d eventdb
            ;;
        15)
            echo "🐚 Opening backend shell..."
            docker-compose exec backend bash
            ;;
        0)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option. Please try again."
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    clear
done
