import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt

app = FastAPI()

origins = ["http://localhost", "http://localhost:8080", "http://localhost:8081", "http://localhost:3000", "http://localhost:3001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))


def on_message(client, userdata, msg):
    userdata["payload"] = msg.payload.decode()
    print("Received message '" + str(msg.payload) + "' on topic '" + msg.topic + "' with QoS " + str(msg.qos))
    client.user_data = userdata
    client.unsubscribe(msg.topic)


client = mqtt.Client(userdata={})
client.on_connect = on_connect
client.on_message = on_message
client.connect("mqtt", 1884, 60)
client.loop_start()


@app.get("/{topic:path}")
async def read_mqtt_message(topic: str):
    try:
        client.subscribe(topic)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid MQTT topic")
    print("Subscribed to " + topic)
    client.user_data = {}
    if not topic:
        raise HTTPException(status_code=400, detail="Invalid MQTT topic")

    timeout = 5
    while "payload" not in client.user_data and timeout > 0:
        timeout -= 1
        print("Waiting for message... " + str(timeout))
        await asyncio.sleep(1)

    if timeout == 0:
        raise HTTPException(status_code=400, detail="Timeout waiting for MQTT message (the topic may not exist)")

    payload = client.user_data["payload"]
    del client.user_data["payload"]
    return {"topic": topic, "payload": payload}


@app.on_event("shutdown")
def shutdown_event():
    client.loop_stop()
    client.disconnect()
