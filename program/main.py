import asyncio
from qasync import QEventLoop
from gui import init_gui

async def main():
    app, window = init_gui()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)


    print("Discus-2cT Lift Calculator started")

    with loop:
        loop.run_forever()

asyncio.run(main())