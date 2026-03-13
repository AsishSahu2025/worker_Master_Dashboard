# from .mqtt_command_queue import mqtt_publish_queue

# def publish_mqtt_command(topic, payload):

#     print("QUEUE PUSH:", topic, payload)

#     try:
#         mqtt_publish_queue.put({
#             "topic": topic,
#             "payload": payload
#         })

#     except Exception as e:
#         print("MQTT queue error:", e)