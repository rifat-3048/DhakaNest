import logging

from fastapi import APIRouter, HTTPException, status

from app.ml.predictor import predict_monthly_rent
from app.schemas.rent_prediction_schema import (
    RentPredictionRequest,
    RentPredictionResponse,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/rent",
    tags=["Rent Prediction"],
)


@router.post(
    "/predict",
    response_model=RentPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict monthly rent",
)
def predict_rent(
    payload: RentPredictionRequest,
) -> RentPredictionResponse:
    """
    Predict the estimated monthly base rent of a property in BDT.

    The model automatically selects one of three routes:

    - Primary micro-area model
    - Broad-area fallback
    - Dhaka-wide fallback
    """

    try:
        result = predict_monthly_rent(
            broad_area=payload.broad_area,
            model_micro_area=(
                payload.model_micro_area
            ),
            area_sqft=payload.area_sqft,
            bedrooms=payload.bedrooms,
            bathrooms=payload.bathrooms,
        )

        return RentPredictionResponse(
            **result
        )

    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(error),
        ) from error

    except RuntimeError as error:
        logger.exception(
            "The rent prediction model is unavailable."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "The rent prediction service "
                "is temporarily unavailable."
            ),
        ) from error

    except Exception as error:
        logger.exception(
            "Unexpected rent prediction error."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "An unexpected error occurred "
                "while generating the prediction."
            ),
        ) from error