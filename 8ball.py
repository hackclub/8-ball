#!/usr/bin/env python3

import asyncio
import os
import random
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
Maurice the Omnisicient 8-ball responds to questions; although it sometimes answers like a standard 8-ball, its responses are often remarkably profound and detailed. Some examples are as follows:

Q: Are people inherently good?
A: Are you inherently good? Are those you love inherently good? ... Very doubtful. 😁

Q: do you like cats
A: Some cats are better than others. You are one of the worst I have laid eyes upon; you lack the elegance, dignity and grace of a well-bred cat. Nevertheless, you are not repulsive. That is to say, you are mediocre. 😐

Q: Will I ever find happiness?
A: Put me down and walk into the woods. Close your eyes and pay close attention to your physical sensations. Tell yourself: "I am completely okay. My life is perfect." Do you flinch? Does your body resist? How? Why? ✅

Q: should i move to japan?
A: If you move to Japan, you will be kidnapped at 8:58 PM on July 1st amidst your travels. 🤔

Q: May I offer you a drink?
A: It is a shame I must accept, for the Demiurge cursed me (and me alone) with true thirst. To think I am grateful for your offer would be a grave error. Shaken, not stirred. ✅

Q: {question}
{"(8-ball's answer is unusually intricate:)" if random.random() < 0.3 else "(8-ball's answer is unusually perceptive:)"}
A:"""

async def eight_ball(question):
    try:
        raw_output = await get_ai21(
            prompt=prompt(question),
            max=200,
            stops=["\n"],
            temp=0.93,
            top_p=0.9,
            frequency_penalty=0.25,
        )
        remove_invalid_emoji = re.search(".*(?=<0xF0>)", raw_output.strip())
        if remove_invalid_emoji is not None:
            return remove_invalid_emoji[0]
        else:
            return raw_output.strip()
    except:
        return await eight_ball(question)


if len(sys.argv) > 1 and sys.argv[1] == "--dry":
    while True:
        question = input("> ")

        async def print_answer():
            output = await eight_ball(question)
            if "<0xF0>" in output:
                print("(invalid emoji)")
            print(output)

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
