"""
Error handling middleware.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger
import traceback


async def handle_errors(request: Request, call_next):
    """Global error handler middleware."""

    try:
        response = await call_next(request)
        return response

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": str(e)}
        )

    except KeyError as e:
        logger.warning(f"Missing field: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": f"Missing required field: {str(e)}"}
        )

    except Exception as e:
        logger.error(f"Unhandled error: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "Internal server error"}
        )
