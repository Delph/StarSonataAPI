# StarSonataAPI
A simple Python API for interacting with the [Star Sonata](https://starsonata.com) game server as a chat client user.

## A rather bad usage guide
Import and create an instance of the API
```python
from StarSonataAPI import *
from StarSonataAPI.message_types import *

ss = StarSonataAPI()
```

Setup an account instance, provide the username and password you wish to log in as;
```python
account = Account('aUsername', 'aPassword')
```

Setup message handlers for messages you wish to capture, e.g.,;
```python
@ss.on_event(SC_TEXTMESSAGE)
async def text_message(message):
  tm = TextMessage()
  tm.buf_in(message.payload)

  print(f'[{tm.channel_name}] {tm.username}: {tm.message}')
```
`message` is the raw message sent by the server, generate the correct message object and `buf_in` to get usable data.

Connect to server and start handling messages by calling `run`;
```python
ss.run(account)
```
`run` is async, and can be chucked into an asyncio task list.
