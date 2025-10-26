from app import create_app
from config import Config

app = create_app()

# Validate configuration on startup
with app.app_context():
    try:
        Config.validate()
    except ValueError as e:
        print("\n" + "=" * 80)
        print("CONFIGURATION ERROR:")
        print("=" * 80)
        print(str(e))
        print("=" * 80)
        print("\nPlease fix the configuration errors and restart the server.")
        print("=" * 80)
        exit(1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 