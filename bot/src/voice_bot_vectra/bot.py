import asyncio

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
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
        audio_out_10ms_chunks=2,  # 20 ms per frame → matches AudioSocket wire rate
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
            system_instruction=SYSTEM_PROMPT,
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

    context = LLMContext(
        messages=[{"role": "assistant", "content": FIRST_MESSAGE}],
    )
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=False,
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
