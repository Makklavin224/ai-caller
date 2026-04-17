import asyncio
import sys

from loguru import logger

from .audiosocket import TYPE_UUID, read_message
from .bot import run_bot
from .config import Settings


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    settings: Settings,
):
    peer = writer.get_extra_info("peername")
    logger.info(f"AudioSocket connection from {peer}")

    try:
        msg_type, payload = await read_message(reader)
    except asyncio.IncompleteReadError:
        logger.warning("Peer closed before sending UUID")
        writer.close()
        return

    if msg_type != TYPE_UUID or len(payload) != 16:
        logger.error(
            f"Expected UUID frame (0x01, 16B), got type=0x{msg_type:02x} len={len(payload)}"
        )
        writer.close()
        return

    call_uuid = payload.hex()
    logger.info(f"Call UUID {call_uuid}")

    try:
        await run_bot(reader, writer, settings, call_uuid)
    except Exception:
        logger.exception("run_bot crashed")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    settings = Settings()
    logger.remove()
    logger.add(sys.stdout, level=settings.log_level)

    logger.info(
        f"AudioSocket server listening on "
        f"{settings.audiosocket_host}:{settings.audiosocket_port}"
    )

    server = await asyncio.start_server(
        lambda r, w: handle_connection(r, w, settings),
        settings.audiosocket_host,
        settings.audiosocket_port,
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
