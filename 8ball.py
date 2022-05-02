#!/usr/bin/env python3

import asyncio
import os
import re
import sys
from textwrap import dedent

with open("keys.txt", "w") as f:
    f.write(os.environ["AI21_API_KEY"])
os.environ["AI21_API_KEY_FILE"] = "keys.txt"
from pyai21.completions import get_ai21

from slack_sdk.web import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

loop = asyncio.new_event_loop()

prompt = lambda question: f"""
The Omnisicient 8-ball responds to questions; although it sometimes answers like a standard 8-ball, its responses are often unusually profound and detailed. Some examples are as follows:

Q: Are people inherently good?
A: Are you inherently good? Are those you love inherently good? ... Very doubtful. 😁

Q: Will I ever find happiness?
A: Put me down and walk into the woods. Close your eyes and pay close attention to your physical sensations. Tell yourself: "I am completely okay. My life is perfect." Do you flinch? Does your body resist? How? Why? ✅

In this case, 8-ball's reply is unusually insightful and somewhat unexpected:
Q: {question}
A:"""

async def eight_ball(question):
    try:
        return (await get_ai21(
            prompt=prompt(question),
            stops=["\n"],
            temp=0.93,
            top_p=0.9,
            presence_penalty=0.2,
        )).strip()
    except:
        return await eight_ball(question)


if len(sys.argv) > 1 and sys.argv[1] == "--dry":
    while True:
        question = input("> ")

        async def print_answer():
            print(await eight_ball(question))

        task = loop.create_task(print_answer())
        loop.run_until_complete(task)


client = SocketModeClient(
    app_token=os.environ["SLACK_XAPP_TOKEN"],
    web_client=WebClient(token=os.environ["SLACK_XOXB_TOKEN"])
)


def listener(client: SocketModeClient, req: SocketModeRequest):
    client.send_socket_mode_response(
        SocketModeResponse(envelope_id=req.envelope_id)
    )

    if req.type != "events_api" or req.payload["event"]["type"] != "app_mention":
        return

    try:
        thread = req.payload["event"]["thread_ts"]
    except KeyError:
        thread = None

    raw_question = req.payload["event"]["text"]
    question = raw_question.replace(re.search(r" ?<@.*> ?", raw_question)[0], "")
    print("New question:", question)

    async def send_answer():
        client.web_client.chat_postMessage(
            channel=req.payload["event"]["channel"],
            thread_ts=thread,
            text=await eight_ball(question)
        )

    task = loop.create_task(send_answer())
    loop.run_until_complete(task)


client.socket_mode_request_listeners.append(listener)
client.connect()

from threading import Event
Event().wait()
