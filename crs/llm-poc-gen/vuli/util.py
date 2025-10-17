import asyncio

import psutil


async def async_process_run_and_exit(
    p, timeout: int, wait_time: int = 1
) -> tuple[int, bytes, bytes]:
    try:
        stdout, stderr = await asyncio.wait_for(p.communicate(), timeout=timeout)
        return (p.returncode, stdout, stderr)
    except TimeoutError as e:
        await terminate_process(p, timeout=wait_time)
        raise e


async def terminate_process(process, timeout: int = 3) -> None:
    pid: int = process.pid
    try:
        parent: psutil.Process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    children: list[psutil.Process] = parent.children(recursive=True)
    for p in children:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass

    _, alive_children = await asyncio.to_thread(
        psutil.wait_procs, children, timeout=timeout
    )
    if alive_children:
        for p in alive_children:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass

    try:
        parent.terminate()
    except psutil.NoSuchProcess:
        pass

    try:
        await asyncio.to_thread(parent.wait, timeout=timeout)
    except asyncio.TimeoutError:
        try:
            parent.kill()
        except psutil.NoSuchProcess:
            pass
    except psutil.NoSuchProcess:
        pass
