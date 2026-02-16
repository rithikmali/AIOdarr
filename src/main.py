#!/usr/bin/env python3
"""
AIODarr - AIOStreams-Radarr/Sonarr Bridge
Automatically adds wanted movies and TV shows to Real-Debrid using AIOStreams
"""

import logging
import time

import schedule

from src.config import Config
from src.media_processor import MediaProcessor


def setup_logging(log_level: str) -> None:
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main entry point"""
    # Load configuration
    try:
        config = Config()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please ensure all required environment variables are set.")
        print("See .env.example for required configuration.")
        return 1

    # Setup logging
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("AIODarr - AIOStreams Media Bridge Starting")
    logger.info("=" * 60)
    if config.radarr_enabled:
        logger.info(f"Radarr URL: {config.radarr_url}")
    if config.sonarr_enabled:
        logger.info(f"Sonarr URL: {config.sonarr_url}")
    logger.info(f"AIOStreams URL: {config.aiostreams_url}")
    logger.info(f"Poll Interval: {config.poll_interval_minutes} minutes")
    logger.info(f"Retry Failed: {config.retry_failed_hours} hours")
    logger.info("=" * 60)

    # Initialize processor
    processor = MediaProcessor(config)

    # Run immediately on startup
    logger.info("Running initial check...")
    processor.process_all()

    # Schedule periodic checks
    schedule.every(config.poll_interval_minutes).minutes.do(processor.process_all)

    logger.info(f"Scheduled to check every {config.poll_interval_minutes} minutes")
    logger.info("Press Ctrl+C to stop")

    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        return 0


if __name__ == "__main__":
    exit(main())
