"""
Unit tests for SettlementRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Period, Settlement, User
from app.repositories import SettlementRepository
from tests.fixtures.factories import create_test_settlement


@pytest.mark.unit
class TestSettlementRepository:
    """Test suite for SettlementRepository."""

    @pytest.fixture
    def settlement_repository(self, db_session: AsyncSession) -> SettlementRepository:
        return SettlementRepository(db_session)

    async def test_get_settlement_by_id_exists(
        self, settlement_repository: SettlementRepository, settlement_factory: Callable[..., Awaitable[Settlement]]
    ):
        """Test retrieving a settlement by ID when it exists."""
        settlement = await settlement_factory(period_id=1, payer_id=1, payee_id=2, amount=5000)

        retrieved = await settlement_repository.get_settlement_by_id(settlement.id)

        assert retrieved is not None
        assert retrieved.id == settlement.id
        assert retrieved.period_id == settlement.period_id
        assert retrieved.payer_id == settlement.payer_id
        assert retrieved.payee_id == settlement.payee_id
        assert retrieved.amount == 5000

    async def test_get_settlement_by_id_not_exists(self, settlement_repository: SettlementRepository):
        """Test retrieving a settlement by ID when it doesn't exist."""
        result = await settlement_repository.get_settlement_by_id(99999)

        assert result is None

    async def test_get_settlement_by_id_relationships_loaded(
        self,
        settlement_repository: SettlementRepository,
        settlement_factory: Callable[..., Awaitable[Settlement]],
        user_factory: Callable[..., Awaitable[User]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that relationships (period, payer, payee) are loaded when retrieving by ID."""
        # Create users and period
        payer = await user_factory(email="payer@example.com", name="Payer")
        payee = await user_factory(email="payee@example.com", name="Payee")
        period = await period_factory(group_id=1, name="Test Period")

        # Create settlement
        settlement = await settlement_factory(period_id=period.id, payer_id=payer.id, payee_id=payee.id, amount=10000)

        # Retrieve settlement
        retrieved = await settlement_repository.get_settlement_by_id(settlement.id)

        assert retrieved is not None
        # Verify relationships are loaded (joinedload should populate these)
        assert retrieved.period is not None
        assert retrieved.period.id == period.id
        assert retrieved.period.name == period.name
        assert retrieved.payer is not None
        assert retrieved.payer.id == payer.id
        assert retrieved.payer.name == payer.name
        assert retrieved.payee is not None
        assert retrieved.payee.id == payee.id
        assert retrieved.payee.name == payee.name

    async def test_get_settlements_by_period_id_empty(
        self, settlement_repository: SettlementRepository, period_factory: Callable[..., Awaitable[Period]]
    ):
        """Test retrieving settlements for a period with no settlements."""
        period = await period_factory(group_id=1, name="Empty Period")

        settlements = await settlement_repository.get_settlements_by_period_id(period.id)

        assert isinstance(settlements, list)
        assert len(settlements) == 0

    async def test_get_settlements_by_period_id_multiple(
        self,
        settlement_repository: SettlementRepository,
        settlement_factory: Callable[..., Awaitable[Settlement]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving settlements for a period with multiple settlements."""
        # Create periods
        period1 = await period_factory(group_id=1, name="Period 1")
        period2 = await period_factory(group_id=1, name="Period 2")

        # Create settlements for different periods
        settlement1 = await settlement_factory(period_id=period1.id, payer_id=1, payee_id=2, amount=5000)
        settlement2 = await settlement_factory(period_id=period1.id, payer_id=2, payee_id=3, amount=3000)
        settlement3 = await settlement_factory(period_id=period2.id, payer_id=1, payee_id=2, amount=7000)

        # Get settlements for period 1
        period1_settlements = await settlement_repository.get_settlements_by_period_id(period1.id)

        assert len(period1_settlements) >= 2

        settlement_ids = {s.id for s in period1_settlements}

        assert settlement1.id in settlement_ids
        assert settlement2.id in settlement_ids
        assert settlement3.id not in settlement_ids

        # Get settlements for period 2
        period2_settlements = await settlement_repository.get_settlements_by_period_id(period2.id)

        assert len(period2_settlements) >= 1
        assert period2_settlements[0].id == settlement3.id

    async def test_get_settlements_by_period_id_relationships_loaded(
        self,
        settlement_repository: SettlementRepository,
        settlement_factory: Callable[..., Awaitable[Settlement]],
        user_factory: Callable[..., Awaitable[User]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that relationships are loaded when retrieving settlements by period ID."""
        # Create users and period
        payer = await user_factory(email="payer@example.com", name="Payer")
        payee = await user_factory(email="payee@example.com", name="Payee")
        period = await period_factory(group_id=1, name="Test Period")

        # Create settlement
        settlement = await settlement_factory(period_id=period.id, payer_id=payer.id, payee_id=payee.id, amount=10000)

        # Retrieve settlements
        settlements = await settlement_repository.get_settlements_by_period_id(period.id)

        assert len(settlements) >= 1
        retrieved = next(s for s in settlements if s.id == settlement.id)

        # Verify relationships are loaded
        assert retrieved.period is not None
        assert retrieved.period.id == period.id
        assert retrieved.payer is not None
        assert retrieved.payer.id == payer.id
        assert retrieved.payee is not None
        assert retrieved.payee.id == payee.id

    async def test_create_settlement(
        self,
        settlement_repository: SettlementRepository,
        user_factory: Callable[..., Awaitable[User]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test creating a new settlement."""
        # Create users and period
        payer = await user_factory(email="payer@example.com", name="Payer")
        payee = await user_factory(email="payee@example.com", name="Payee")
        period = await period_factory(group_id=1, name="Test Period")

        # Create settlement
        settlement = create_test_settlement(period_id=period.id, payer_id=payer.id, payee_id=payee.id, amount=15000)

        created = await settlement_repository.create_settlement(settlement)

        assert created.id is not None
        assert created.period_id == period.id
        assert created.payer_id == payer.id
        assert created.payee_id == payee.id
        assert created.amount == 15000
        assert created.date_paid is not None

        # Verify it's in the database
        retrieved = await settlement_repository.get_settlement_by_id(created.id)

        assert retrieved is not None
        assert retrieved.amount == 15000
        assert retrieved.payer_id == payer.id
        assert retrieved.payee_id == payee.id

    async def test_create_settlement_relationships_loaded(
        self,
        settlement_repository: SettlementRepository,
        user_factory: Callable[..., Awaitable[User]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that relationships are loaded after creating a settlement."""
        # Create users and period
        payer = await user_factory(email="payer@example.com", name="Payer")
        payee = await user_factory(email="payee@example.com", name="Payee")
        period = await period_factory(group_id=1, name="Test Period")

        # Create settlement
        settlement = create_test_settlement(period_id=period.id, payer_id=payer.id, payee_id=payee.id, amount=20000)

        created = await settlement_repository.create_settlement(settlement)

        # Verify relationships are loaded (repository eagerly loads them)
        assert created.period is not None
        assert created.period.id == period.id
        assert created.period.name == period.name
        assert created.payer is not None
        assert created.payer.id == payer.id
        assert created.payer.name == payer.name
        assert created.payee is not None
        assert created.payee.id == payee.id
        assert created.payee.name == payee.name
