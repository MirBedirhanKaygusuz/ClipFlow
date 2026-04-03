"""Centralized async FFmpeg runner with retry and timeout."""

import asyncio
import structlog
from app.exceptions import FFmpegError

log = structlog.get_logger()


async def run_ffmpeg(
    cmd: list[str],
    retries: int = 2,
    timeout: int = 300,
) -> tuple[str, str]:
    """Run an FFmpeg command asynchronously with retry and timeout.

    Args:
        cmd: FFmpeg command as list of arguments.
        retries: Number of retry attempts on failure.
        timeout: Timeout in seconds for each attempt.

    Returns:
        Tuple of (stdout, stderr) from the process.

    Raises:
        FFmpegError: If all retry attempts fail or timeout occurs.
    """
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            log.info(
                "ffmpeg_start",
                attempt=attempt + 1,
                total_attempts=retries + 1,
                cmd=" ".join(cmd[:5]) + "...",
            )

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                raise FFmpegError(stderr_str)

            log.info("ffmpeg_done", attempt=attempt + 1)
            return stdout_str, stderr_str

        except asyncio.TimeoutError:
            last_error = FFmpegError(f"FFmpeg timed out after {timeout}s")
            log.warning(
                "ffmpeg_timeout",
                attempt=attempt + 1,
                timeout=timeout,
            )
            # Kill the timed-out process
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass

        except FFmpegError as e:
            last_error = e
            log.warning(
                "ffmpeg_failed",
                attempt=attempt + 1,
                error=str(e)[:200],
            )

        if attempt < retries:
            wait_time = 2 ** attempt
            log.info("ffmpeg_retry_wait", seconds=wait_time)
            await asyncio.sleep(wait_time)

    raise last_error or FFmpegError("FFmpeg failed after all retries")


async def run_ffprobe(cmd: list[str], timeout: int = 30) -> str:
    """Run an FFprobe command asynchronously.

    Args:
        cmd: FFprobe command as list of arguments.
        timeout: Timeout in seconds.

    Returns:
        stdout output from ffprobe.

    Raises:
        FFmpegError: If the command fails or times out.
    """
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise FFmpegError(f"FFprobe timed out after {timeout}s")

    if process.returncode != 0:
        raise FFmpegError(stderr.decode("utf-8", errors="replace"))

    return stdout.decode("utf-8", errors="replace")
