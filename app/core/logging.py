import logging
import json

logger = logging.getLogger("clinic.domain")
logger.setLevel(logging.INFO)


def domain_log(event: str, payload: dict):
    logger.info(
        json.dumps(
            {
                "event": event,
                **payload,
            }
        )
    )