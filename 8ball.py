#!/usr/bin/env python3

import asyncio
import os
import re
from textwrap import dedent

with open("keys.txt", "w") as f:
    f.write(os.environ["AI21_API_KEY"])
os.environ["AI21_API_KEY_FILE"] = "keys.txt"
from pyai21.completions import get_ai21

from slack_sdk.web import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse


client = SocketModeClient(
    app_token=os.environ["SLACK_XAPP_TOKEN"],
    web_client=WebClient(token=os.environ["SLACK_XOXB_TOKEN"])
)
loop = asyncio.new_event_loop()


def listener(client: SocketModeClient, req: SocketModeRequest):
    client.send_socket_mode_response(
        SocketModeResponse(envelope_id=req.envelope_id)
    )

    if req.type != "events_api" or req.payload["event"]["type"] != "app_mention":
        return

    raw_question = req.payload["event"]["text"]
    question = raw_question.replace(re.search(r" ?<@.*> ?", raw_question)[0], "")
    print("New question:", question)

    prompt = dedent(f"""
    The Omnisicient 8-ball might answer various questions like so:

    Q: Will I find happiness?
    A: Not if I get my way. 🙂

    Q: Are your answers accurate?
    A: It is certain. ✅

    Q: Are people inherently good?
    A: My experiences with people have left me shaken.

    Q: {question}
    (Notice that the 8-ball's reply is somewhat florid and slightly ominous:)
    A:""")

    async def send_answer():
        try:
            answer = await get_ai21(
                prompt=prompt,
                stops=["\n"],
                temp=1.0,
                top_p=0.9,
            )
        except:
            # lmfao
            await send_answer()
            return

        client.web_client.chat_postMessage(channel=req.payload["event"]["channel"], text=answer)

    task = loop.create_task(send_answer())
    loop.run_until_complete(task)


client.socket_mode_request_listeners.append(listener)
client.connect()

from threading import Event
Event().wait()
