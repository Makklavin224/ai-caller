import asyncio

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.base_transport import TransportParams

from .audiosocket import AudioSocketTransport
from .config import Settings as Cfg
from .prompt import FIRST_MESSAGE, SYSTEM_PROMPT


async def run_bot(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    cfg: Cfg,
    call_uuid: str,
):
    logger.info(f"Starting pipeline for call {call_uuid}")

    params = TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_sample_rate=16000,
        audio_out_sample_rate=16000,
        vad_analyzer=SileroVADAnalyzer(),
        vad_audio_passthrough=True,
    )
    transport = AudioSocketTransport(reader, writer, params)

    stt = DeepgramSTTService(
        api_key=cfg.deepgram_api_key,
        settings=DeepgramSTTService.Settings(
            model="nova-3-general",
            language="ru",
            punctuate=True,
        ),
    )

    llm = OpenAILLMService(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        settings=OpenAILLMService.Settings(
            model=cfg.openai_model,
            temperature=0.1,
        ),
    )

    tts = ElevenLabsTTSService(
        api_key=cfg.elevenlabs_api_key,
        sample_rate=16000,
        settings=ElevenLabsTTSService.Settings(
            voice=cfg.elevenlabs_voice_id,
            model=cfg.elevenlabs_model,
            stability=0.5,
            similarity_boost=0.75,
            speed=1.2,
            language="ru",
        ),
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": FIRST_MESSAGE},
    ]
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=False,
        ),
    )

    await task.queue_frames([TTSSpeakFrame(FIRST_MESSAGE)])

    runner = PipelineRunner(handle_sigint=False)
    try:
        await runner.run(task)
    except Exception:
        logger.exception(f"Pipeline for {call_uuid} failed")
    finally:
        try:
            await task.queue_frame(EndFrame())
        except Exception:
            pass
        logger.info(f"Pipeline for {call_uuid} finished")
