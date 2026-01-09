# CSV to Kafka Metadata Streamer - Execution Instructions

## Prerequisites

1. **Kafka Broker Running**
   ```bash
   # Start Kafka (if using Docker)
   docker-compose up -d kafka
   
   # Or start locally installed Kafka
   # Navigate to Kafka installation directory
   bin/kafka-server-start.sh config/server.properties
   ```

2. **Create Kafka Topic** (if not exists)
   ```bash
   # Create topic for raw metadata events
   kafka-topics.sh --create --topic raw_metadata_events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
   
   # Or using Docker
   docker exec -it <kafka_container> kafka-topics.sh --create --topic raw_metadata_events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
   ```

3. **CSV Files in Downloads**
   - Place your CSV files in `~/Downloads/`
   - CSV files must have headers: `user_id, action_type, resource, device_id, ip_address, bytes_accessed`
   - Additional columns will be ignored

## Execution Steps

### 1. Activate Virtual Environment
```bash
source kafka-envs/bin/activate
```

### 2. Verify Dependencies
```bash
# Check if kafka-python is installed
pip list | grep kafka-python

# Install if missing (should already be installed)
pip install kafka-python
```

### 3. Run the Script
```bash
python csv_to_kafka_streamer.py
```

## Script Behavior

- **Discovery**: Automatically finds all `.csv` files in `~/Downloads/`
- **Sequential Processing**: Processes one CSV file completely before moving to the next
- **Rate Limiting**: Sends exactly 1 event every 20 seconds
- **Event Format**: Each CSV row becomes a JSON metadata event with UUID, timestamp, and source_file
- **Error Handling**: Continues processing next file if one fails

## Monitoring

### Check Kafka Topic
```bash
# Consume events to verify they're being sent
kafka-console-consumer.sh --topic raw_metadata_events --bootstrap-server localhost:9092 --from-beginning
```

### Stop the Script
- Press `Ctrl+C` to gracefully stop streaming

## Troubleshooting

1. **Connection Refused**: Ensure Kafka broker is running on localhost:9092
2. **No CSV Files**: Verify CSV files exist in ~/Downloads/ with correct headers
3. **Topic Not Found**: Create the topic using the command above
4. **Permission Issues**: Ensure read access to ~/Downloads/ directory

## Expected Output

```
🚀 CSV to Kafka Metadata Streamer
========================================
✓ Found 3 CSV files in Downloads directory
  - user_activity_2024_01.csv
  - user_activity_2024_02.csv
  - user_activity_2024_03.csv
✓ Kafka producer connected to localhost:9092

🔄 Processing file: user_activity_2024_01.csv
✓ CSV headers: user_id, action_type, resource, device_id, ip_address, bytes_accessed
✓ Sent event 1 from user_activity_2024_01.csv (partition: 0, offset: 0)
✓ Sent event 2 from user_activity_2024_01.csv (partition: 1, offset: 0)
...
✓ Completed streaming 150 events from user_activity_2024_01.csv

🎉 Streaming completed! Total events processed: 450
```
