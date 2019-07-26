import time
import requests
import configparser
import Adafruit_DHT
from influxdb import InfluxDBClient

# Configuration File
CONFIG_FILE = "settings.conf"

def get_reading(config):
    # InfluxDB connection info
    host = config['influxdb_settings']['host']
    port = config['influxdb_settings']['port']
    user = config['influxdb_settings']['user']
    password = config['influxdb_settings']['password']
    dbname = config['influxdb_settings']['dbname']

    # Create the InfluxDB client object
    client = InfluxDBClient(host, port, user, password, dbname)

    # Sensor details
    #sensor = str(config['sensor_settings']['sensor'])
    sensor = Adafruit_DHT.DHT11
    sensor_gpio = config['sensor_settings']['sensor_gpio_pin']
    measurement = config['sensor_settings']['measurement']
    location = config['sensor_settings']['location']

    humidity, celcius = Adafruit_DHT.read_retry(sensor, sensor_gpio)
    # Add Farhenheit for us 'Mericans
    farhenheit = celcius * 9 / 5 + 32

    # Structure Timestamp to UTC
    current_time = time.gmtime()
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', current_time)

    # Structure the data for write
    data = [
        {
            "measurement": measurement,
            "tags": {
                "location": location,
            },
            "time": timestamp,
            "fields": {
                "temperature_c": celcius,
                "temperature_f": farhenheit,
                "humidity": humidity
            }
        }
    ]

    # Write it!
    client.write_points(data)

    # Return the temperature value.
    return float(data[0]['fields']['temperature_f'])


def post_alert(config, trigger, value):
    # IFTTT Webhook Info
    ifttt_url = "https://maker.ifttt.com/trigger/{}/with/key/"
    ifttt_key = config['alerting_settings']['ifttt_key']

    # 'value' will be sent to IFTTT and can be included in alert
    data = {"value1": value}

    # Pass in event name to trigger appropriately
    ifttt_event_url = ifttt_url.format(trigger) + ifttt_key

    # Post it!
    requests.post(ifttt_event_url, json=data)


def read_config():
    cfg = configparser.ConfigParser()

    # Read the config
    cfg.read(CONFIG_FILE)

    # Read the Values from the config
    config = {section: {k: v for k, v in cfg.items(section)} for section in cfg.sections()}

    # Return the config
    return config


def main():
    # Initial threshold counter.
    threshold_counter = []

    # Read the config
    config = read_config()

    while True:
        # Get the reading and send to Influx
        current_temperature = get_reading(config)

        # If temp is higher than threshold, Append to counter
        if current_temperature > float(config['alerting_settings']['temperature_threshold_high']) or current_temperature < float(config['alerting_settings']['temperature_threshold_low']):
            threshold_counter.append(current_temperature)

        # If we hit threshold_count, alert and reset.
        # This prevents us from alerting every temperature check
        if len(threshold_counter) == int(config['alerting_settings']['threshold_count']):
            temperature_alert = config['alerting_settings']['ifttt_event_name']
            post_alert(config, temperature_alert, current_temperature)
            # Reset counter
            threshold_counter = []
        # Sleep the interval
        time.sleep(int(config['influxdb_settings']['interval']))


if __name__ == '__main__':
    main()