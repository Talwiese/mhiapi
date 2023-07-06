#!/usr/bin/env python3

# publisher.py - publishes measured values over MQTTs
# Copyright (C) 2023  Iman Ayatollahi, Talwiese IoT Solutions e.U.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import struct, socket, ssl, os.path, logging, logging.config, sys
import paho.mqtt.client as mqtt
from modules.inhouse.signalhandler import SignalHandler
from modules.inhouse.mhiacfg import MhiaConfig

CONFIG_PATH = "./config.yaml" if os.path.isfile("./config.yaml") else "./config_default.yaml"
CONFIG = MhiaConfig(CONFIG_PATH).get_config()

logging.config.dictConfig(CONFIG['logging'])
common_logger = logging.getLogger("standard")
error_logger = logging.getLogger("error")

common_logger.info("Starting publisher...")
config_path = "./config.yaml" if os.path.isfile("./config.yaml") else "./config_default.yaml"

def on_connect(client, userdata, flags, rc):
    """
    The function that is called whenever the client receives a CONNACK response from the server.
    """
    common_logger.info("Connected to MQTT broker with result code " + str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe("$SYS/#")

def on_message(client, userdata, msg):
    common_logger.info("Received: " + msg.topic + str(msg.payload))

def main():
    signalhandler = SignalHandler()
    socket_path = "./uds_samples"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(0.2)

    # establishing socket connection to sampler
    conn_attempt = 0
    while not (signalhandler.interrupt or signalhandler.terminate):
        conn_attempt += 1
        try:
            sock.connect(socket_path)
        except Exception as e:
            if temp_counter <= 30: temp_counter += 1
            else:
                error_logger.error(f"Could not connect to sampler after {temp_counter} tries!")
                common_logger.info("Exiting, could not establish uds connection with sampler!")
                sys.exit(1)
        else:
            sock.send("publ".encode(encoding = 'UTF-8'))
            break
    common_logger.info("Connected to sampler...")

    mqttc = mqtt.Client()
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    toSend = []
    certfile=CONFIG['publisher']['certfile_path']
    keyfile=CONFIG['publisher']['keyfile_path']
    cafile=CONFIG['publisher']['cafile_path']
    brokerhost=CONFIG['publisher']['broker_host']
    brokerport=CONFIG['publisher']['broker_port']

    common_logger.info(f"Attempting to connect to MQTT broker using client cert:{certfile} and using cafile:{cafile} to authenticate server (broker).")

    mqttc.tls_set(ca_certs=cafile, certfile=certfile, keyfile=keyfile, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS, ciphers=None) 

    # prepare topic
    HOSTNAME = socket.gethostname()
    topic_to_publish_about = CONFIG['publisher']['topic']
    topic_to_publish_about += ("/" + HOSTNAME + "/") if CONFIG['publisher']['add_hostname_to_topic'] else "/"
    common_logger.info("Will use this topic: " + topic_to_publish_about)
    #print(topic_to_publish_about)
    try:
        mqttc.connect(brokerhost, port=brokerport, keepalive=60, bind_address="")
    except Exception as e:
        if ("CERTIFICATE_VERIFY_FAILED" in str(e)): common_logger.info("Certificate not valid anymore! Contact administrator of the MQTT broker!")
        error_logger.error(f"CERTIFICATE_VERIFY_FAILED while trying to connect to MQTT broker!")
        common_logger.info("Exiting, could not establish MQTT connection.")
        #other exceptions
        sys.exit(1)
    else:
        common_logger.info(f"Connected to MQTT broker at {brokerhost}:{brokerport}.")
    finally: pass

    while not (signalhandler.interrupt or signalhandler.terminate):
        toSend.clear()
        # exception handling is still missing here, tbd
        while len(toSend) < 21:
            byx = sock.recv(20)
            channel, timestamp, value = struct.unpack('!idd', byx) #!idd means: int (4bytes), double (8bytes), double (8bytes)
            a, b = str(timestamp), str(value)
            mqttc.publish(topic_to_publish_about + "ch_" + str(channel) + "/sensor_time/", a)
            mqttc.publish(topic_to_publish_about + "ch_" + str(channel) + "/sensor_value/", b)
            toSend.append((a,b))
        
        #the next commented line was a test for https post instead of mqtt, maybe https option in future
        #requests.post('https://nr1.ayatollahi.com/pipein', data = toSend, cert=('./mhiaProbe1.crt', './mhiaProbe1.key.pem'))
    
if __name__=="__main__":
    main()    
