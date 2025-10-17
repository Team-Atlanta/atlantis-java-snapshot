#!/usr/bin/env python3

import argparse
import asyncio
import logging
import traceback
from pathlib import Path

from libDeepGen.engine import DeepGenEngine
from libDeepGen.submit import ZeroMQSubmit

from .cpmeta import CPMetadata
from .spa_task import add_spa_tasks
from .utils import CRS_ERR_LOG, CRS_WARN_LOG

CRS_ERR = CRS_ERR_LOG("cli")
CRS_WARN = CRS_WARN_LOG("cli")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from libCRS.otel import install_otel_logger

    install_otel_logger(action_name="crs-java:deepgen")
except Exception as e:
    print(f"{CRS_ERR} Failed to install OpenTelemetry logger: {e}.")


def parse_model_weights(models_str: str) -> dict:
    """Parse model:weight pairs (format: "model1:weight1,model2:weight2") into a dictionary"""
    if not models_str:
        return {}

    weighted_models = {}
    try:
        for pair in models_str.split(","):
            if ":" not in pair:
                logger.warning(
                    f"{CRS_WARN} Invalid model:weight pair: {pair}, expected format 'model:weight'"
                )
                continue

            model, weight_str = pair.split(":", 1)
            try:
                weight = int(weight_str)
                if weight <= 0:
                    logger.warning(
                        f"{CRS_WARN} Invalid weight {weight} for model {model}, must be positive"
                    )
                    continue
                weighted_models[model.strip()] = weight
            except ValueError:
                logger.warning(
                    f"{CRS_WARN} Invalid weight value: {weight_str}, must be an integer"
                )
    except Exception as e:
        logger.error(f"{CRS_ERR} Error parsing model weights: {e}")

    return weighted_models


def clean_shm_files(cp_name: str):
    """Clean shared memory files related to the CP name"""
    cp_shm_path = Path("/dev/shm")
    for item in cp_shm_path.iterdir():
        if cp_name in item.name:
            try:
                item.unlink()
                logger.info(f"Removed shared memory file: {item}")
            except Exception as e:
                logger.error(
                    f"Failed to remove shared memory file: {item}, error: {e}, {traceback.format_exc()}"
                )


async def run_deepgen(
    cores, weighted_models, metadata_path, workdir, zmq_url, run_time, para,
    spa_interval, spa_max_stuck_points, exec_files
):
    """Run the DeepGen engine"""
    try:
        workdir_path = Path(workdir)
        workdir_path.mkdir(parents=True, exist_ok=True)

        cp_metadata = CPMetadata(metadata_path)
        tasks = cp_metadata.create_harness_tasks(workdir_path, weighted_models)

        if not tasks:
            logger.error(
                f"{CRS_ERR} No valid harness tasks could be created from metadata"
            )
            return

        model = next(iter(weighted_models.keys()))

        logger.info(f"Using fallback model: {model}")
        logger.info(f"Using weighted models: {weighted_models}")

        submit_cls = ZeroMQSubmit
        submit_kwargs = {}
        if zmq_url:
            submit_kwargs["bind_addr"] = zmq_url

        shm_label = cp_metadata.cp_name.replace("/", "_")
        logger.info(f"Using shared memory label: {shm_label}")
        clean_shm_files(shm_label)

        async with DeepGenEngine(
            core_ids=cores,
            workdir=workdir_path,
            submit_class=submit_cls,
            submit_kwargs=submit_kwargs,
            seed_pool_size=10000,
            n_exec=500,
            task_para=para,
            shm_label=shm_label,
        ) as engine:

            async def add_initial_tasks():
                for i, task in enumerate(tasks):
                    logger.info(
                        f"Adding initial task {i + 1}/{len(tasks)}: {task.harness_name}"
                    )
                    await engine.add_task(task)
                    logger.info(f"Initial task {task.harness_name} added")

            # Start initial task addition
            initial_task = asyncio.create_task(add_initial_tasks())

            # Start SPA task monitoring
            spa_task = asyncio.create_task(
                add_spa_tasks(
                    engine=engine,
                    project_bundle=cp_metadata.project_bundle,
                    harnesses=cp_metadata.harnesses,
                    weighted_models=weighted_models,
                    metadata_path=Path(metadata_path),
                    cp_full_src=cp_metadata.cp_full_src,
                    exec_files=exec_files,
                    run_time=run_time,
                    workdir=workdir_path,
                    interval_seconds=spa_interval,
                    max_stuck_points=spa_max_stuck_points,
                )
            )

            """
            # Start monitoring for new task requests using CPMetadata
             monitor_task = asyncio.create_task(
                cp_metadata.monitor_task_requests(engine)
             )
            """

            # Wait for initial tasks to be added
            await initial_task

            # Run the engine
            await engine.run(time_limit=run_time)

            # Cancel the SPA task
            try:
                spa_task.cancel()
                await spa_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(
                    f"{CRS_ERR} Error while cancelling SPA task: {e} {traceback.format_exc()}"
                )

            """
            # Cancel the monitor task
             try:
                monitor_task.cancel()
                await monitor_task
             except asyncio.CancelledError:
                pass
             except Exception as e:
                logger.error(
                    f"{CRS_ERR} Error while cancelling monitor task: {e} {traceback.format_exc()}"
                )
            """

        logger.info("Engine execution completed.")

    except Exception as e:
        logger.error(f"Error during execution: {e}")
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="DeepGen Engine CLI tool for Java language"
    )

    parser.add_argument(
        "--cores",
        type=int,
        nargs="+",
        default=[1],
        help="CPU core IDs to use (default: [1])",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="claude-3-7-sonnet-20250219:1,gpt-4o:1",
        help="Model weights: 'model1:weight1,model2:weight2,...'",
    )
    parser.add_argument(
        "--metadata", type=str, required=True, help="Path to the CP metadata JSON file"
    )
    parser.add_argument(
        "--workdir",
        type=str,
        required=True,
        help="Working directory for DeepGen artifacts",
    )
    parser.add_argument(
        "--zmq-url", type=str, default=None, help="ZeroMQ URL for seed submission"
    )
    parser.add_argument(
        "--run-time", type=int, default=300, help="Time limit in seconds (default: 300)"
    )
    parser.add_argument(
        "--para",
        type=int,
        default=1,
        help="Parallelism factor for task execution (default: 1)",
    )
    parser.add_argument(
        "--spa-interval",
        type=int,
        default=300,
        help="Interval in seconds between SPA analysis cycles (default: 300)",
    )
    parser.add_argument(
        "--spa-max-stuck-points",
        type=int,
        default=5,
        help="Maximum number of stuck points to process per analysis (default: 5)",
    )
    parser.add_argument(
        "--exec-files",
        type=str,
        nargs="+",
        default=[],
        help="List of JaCoCo execution files (.exec) from fuzzer instances",
    )

    args = parser.parse_args()
    weighted_models = parse_model_weights(args.models)

    try:
        asyncio.run(
            run_deepgen(
                args.cores,
                weighted_models,
                args.metadata,
                args.workdir,
                args.zmq_url,
                args.run_time,
                args.para,
                args.spa_interval,
                args.spa_max_stuck_points,
                args.exec_files,
            )
        )
    except Exception as e:
        logger.error(f"{CRS_ERR} DeepGen execution failed: {e}")
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
