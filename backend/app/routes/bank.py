from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.models.bank import BankAccount
from app.schemas.bank import BankDeposit, BankWithdraw
from app.services.bank import deposit, withdraw

router = APIRouter(prefix="/bank", tags=["Bank"])


async def _get_or_create_account(db: AsyncSession, player: Player) -> BankAccount:
    result = await db.execute(select(BankAccount).where(BankAccount.player_id == player.id))
    account = result.scalar_one_or_none()
    if not account:
        account = BankAccount(player_id=player.id)
        db.add(account)
        await db.commit()
        await db.refresh(account)
    return account


@router.get("/")
async def bank_status(
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_or_create_account(db, current_player)
    return account.to_dict()


@router.post("/deposit")
async def bank_deposit(
    req: BankDeposit,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_or_create_account(db, current_player)
    ok, msg = deposit(current_player, account, req.items, req.currency)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    await db.refresh(account)
    return {"message": "Deposited to bank", "bank": account.to_dict()}


@router.post("/withdraw")
async def bank_withdraw(
    req: BankWithdraw,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_or_create_account(db, current_player)
    ok, msg = withdraw(current_player, account, req.items, req.currency)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    await db.refresh(account)
    return {"message": "Withdrawn from bank", "bank": account.to_dict()}
