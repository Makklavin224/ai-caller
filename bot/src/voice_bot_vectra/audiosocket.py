"""Asterisk AudioSocket protocol + Pipecat 1.0 transport.

Wire protocol (per https://docs.asterisk.org/Latest_API/API_Documentation/Dialplan_Applications/AudioSocket/):
  [type: u8][len: u16 BE][payload: len bytes]
  0x00 hangup, 0x01 UUID(16B), 0x03 DTMF(1 ASCII), 0xff error(1B).
  Audio: 0x10=8kHz, 0x11=12kHz, 0x12=16kHz, 0x13=24kHz ... all signed linear 16-bit mono LE.

Stock Asterisk 20 (Debian 12) sends 0x10 (8 kHz slin). We upsample to 16 kHz
for Pipecat services (Deepgram nova-3, ElevenLabs) and downsample on write.
"""
from __future__ import annotations

import asyncio
import audioop
import struct

from loguru import logger
from pipecat.frames.frames import CancelFrame, EndFrame, InputAudioRawFrame, StartFrame
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport
from pipecat.transports.base_transport import BaseTransport, TransportParams

TYPE_HANGUP = 0x00
TYPE_UUID = 0x01
TYPE_DTMF = 0x03
TYPE_ERROR = 0xFF
TYPE_AUDIO_8K = 0x10
TYPE_AUDIO_16K = 0x12

HEADER_BYTES = 3
WIRE_RATE = 8000
PIPE_RATE = 16000
CHUNK_8K_20MS = 320  # 20 ms @ 8 kHz slin = 160 samples × 2 bytes


async def read_message(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    header = await reader.readexactly(HEADER_BYTES)
    msg_type = header[0]
    length = struct.unpack(">H", header[1:3])[0]
    payload = await reader.readexactly(length) if length else b""
    return msg_type, payload


def encode_message(msg_type: int, payload: bytes) -> bytes:
    return struct.pack(">BH", msg_type, len(payload)) + payload


class AudioSocketInput(BaseInputTransport):
    def __init__(self, reader: asyncio.StreamReader, params: TransportParams):
        super().__init__(params)
        self._reader = reader
        self._read_task: asyncio.Task | None = None
        self._rs_state = None  # audioop.ratecv continuity state

    async def start(self, frame: StartFrame):
        await super().start(frame)
        if self._read_task is None:
            self._read_task = asyncio.create_task(self._receive())

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        await self._cancel_task()

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        await self._cancel_task()

    async def _cancel_task(self):
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except (asyncio.CancelledError, Exception):
                pass
        self._read_task = None

    async def _receive(self):
        try:
            while True:
                msg_type, payload = await read_message(self._reader)
                if msg_type == TYPE_HANGUP:
                    logger.info("AudioSocket: hangup from Asterisk")
                    break
                if msg_type == TYPE_ERROR:
                    logger.error(f"AudioSocket error: {payload!r}")
                    break
                if msg_type == TYPE_DTMF:
                    logger.info(f"DTMF: {payload!r}")
                    continue
                if msg_type == TYPE_AUDIO_8K and payload:
                    audio, self._rs_state = audioop.ratecv(
                        payload, 2, 1, WIRE_RATE, PIPE_RATE, self._rs_state,
                    )
                    await self.push_audio_frame(
                        InputAudioRawFrame(
                            audio=audio,
                            sample_rate=PIPE_RATE,
                            num_channels=1,
                        )
                    )
                elif msg_type == TYPE_AUDIO_16K and payload:
                    await self.push_audio_frame(
                        InputAudioRawFrame(
                            audio=payload,
                            sample_rate=PIPE_RATE,
                            num_channels=1,
                        )
                    )
        except asyncio.IncompleteReadError:
            logger.info("AudioSocket: peer closed")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AudioSocket read loop failed")
        finally:
            await self.push_frame(EndFrame())


class AudioSocketOutput(BaseOutputTransport):
    def __init__(self, writer: asyncio.StreamWriter, params: TransportParams):
        super().__init__(params)
        self._writer = writer
        self._rs_state = None

    async def write_raw_audio_frames(self, frames: bytes):
        if not frames:
            return
        try:
            down, self._rs_state = audioop.ratecv(
                frames, 2, 1, PIPE_RATE, WIRE_RATE, self._rs_state,
            )
            for i in range(0, len(down), CHUNK_8K_20MS):
                chunk = down[i:i + CHUNK_8K_20MS]
                if len(chunk) < CHUNK_8K_20MS:
                    chunk = chunk + b"\x00" * (CHUNK_8K_20MS - len(chunk))
                self._writer.write(encode_message(TYPE_AUDIO_8K, chunk))
            await self._writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            logger.info("AudioSocket: write failed, peer gone")


class AudioSocketTransport(BaseTransport):
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        params: TransportParams,
    ):
        super().__init__(params=params)
        self._reader = reader
        self._writer = writer
        self._input: AudioSocketInput | None = None
        self._output: AudioSocketOutput | None = None

    def input(self) -> AudioSocketInput:
        if self._input is None:
            self._input = AudioSocketInput(self._reader, self._params)
        return self._input

    def output(self) -> AudioSocketOutput:
        if self._output is None:
            self._output = AudioSocketOutput(self._writer, self._params)
        return self._output
