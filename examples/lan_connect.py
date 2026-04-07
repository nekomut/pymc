import asyncio
from mcbe.dial import Dialer
from mcbe.raknet import RakNetNetwork
from mcbe.proto.login.data import IdentityData

async def main():
    # 1. RakNet で LAN サーバーを Ping して存在確認 (任意)
    network = RakNetNetwork()
    try:
        pong = await network.ping("127.0.0.1:19132")
        print(f"Server found: {pong.decode()}")
    except Exception as e:
        print(f"Server not responding: {e}")
        return

    # 2. RakNetNetwork を指定して接続
    dialer = Dialer(
        identity_data=IdentityData(display_name="pymc_player"),
        network=network,
    )
    async with await dialer.dial("127.0.0.1:19132") as conn:
        print("Connected to LAN world!")
        while not conn.closed:
            pk = await conn.read_packet()
            print(f"Received: {type(pk).__name__}")

asyncio.run(main())
