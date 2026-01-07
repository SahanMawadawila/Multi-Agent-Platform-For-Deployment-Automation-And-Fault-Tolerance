# tools/kafka_client.py
import json
import time

# Mocking Kafka Producer for demonstration. 
# In prod, use: from kafka import KafkaProducer
class SystemNotifier:
    def send_update(self, step_name: str, status: str, details: str = ""):
        """
        Sends a JSON event to the 'user-updates' topic.
        We hardcode this in the graph, so the Agent can't forget it.
        """
        message = {
            "timestamp": time.time(),
            "step": step_name,
            "status": status, # 'started', 'completed', 'failed'
            "details": details
        }
        # producer.send('user-updates', value=message)
        print(f"\n[KAFKA EVENT] >>> {json.dumps(message, indent=2)}")