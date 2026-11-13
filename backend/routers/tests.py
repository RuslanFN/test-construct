import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from models.test import TestStatus
from schemas.attempt import AttemptDetail, TestAttemptsOut
from schemas.test import TestCreate, TestDetail, TestSummary
from services.attempt_service import (

    attempts_to_xlsx,
    get_attempt_detail,
    list_test_attempts,
)
from services.deps import get_current_user
from services.test_service import (
    create_test,
    delete_test,
    get_owned_test,
    list_user_tests,
    set_status,
    test_to_detail,
    update_test,
)

router = APIRouter(prefix='/api/tests', tags=['tests'])


@router.get('', response_model=list[TestSummary])
async def my_tests(current=Depends(get_current_user)):
    return await list_user_tests(current)


@router.get('/{test_id}', response_model=TestDetail)
async def get_test(test_id: uuid.UUID, current=Depends(get_current_user)):
    doc = await get_owned_test(test_id, current)
    return test_to_detail(doc)


@router.post('', response_model=TestDetail, status_code=201)
async def save_test(payload: TestCreate, current=Depends(get_current_user)):
    doc = await create_test(payload, current)
    return test_to_detail(doc)


@router.put('/{test_id}', response_model=TestDetail)
async def edit_test(test_id: uuid.UUID, payload: TestCreate, current=Depends(get_current_user)):
    doc = await update_test(test_id, payload, current)
    return test_to_detail(doc)


@router.post('/{test_id}/publish', response_model=TestDetail)
async def publish(test_id: uuid.UUID, current=Depends(get_current_user)):
    doc = await set_status(test_id, current, TestStatus.PUBLISHED)
    return test_to_detail(doc)


@router.post('/{test_id}/unpublish', response_model=TestDetail)
async def unpublish(test_id: uuid.UUID, current=Depends(get_current_user)):
    doc = await set_status(test_id, current, TestStatus.DRAFT)
    return test_to_detail(doc)


@router.delete('/{test_id}', status_code=204)
async def remove(test_id: uuid.UUID, current=Depends(get_current_user)):
    await delete_test(test_id, current)


@router.get('/{test_id}/attempts', response_model=TestAttemptsOut)
async def test_attempts(test_id: uuid.UUID, current=Depends(get_current_user)):
    doc = await get_owned_test(test_id, current)
    return await list_test_attempts(doc)


@router.get('/{test_id}/attempts/export')
async def export_attempts(test_id: uuid.UUID, current=Depends(get_current_user)):
    doc = await get_owned_test(test_id, current)
    xlsx_data = await attempts_to_xlsx(doc)
    filename = f'attempts-{test_id}.xlsx'
    return StreamingResponse(
        iter([xlsx_data]),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/{test_id}/attempts/{attempt_id}', response_model=AttemptDetail)
async def attempt_detail(test_id: uuid.UUID, attempt_id: uuid.UUID, current=Depends(get_current_user)):
    doc = await get_owned_test(test_id, current)
    return await get_attempt_detail(doc, attempt_id)
