from app.kafka_consumer import start_consumer
import dotenv

dotenv.load_dotenv()

def main():
    print("Hello from devops-agents!")
    start_consumer()


if __name__ == "__main__":
    main()
