"""Data service layer for database operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    AgentProfile,
    Demand,
    DemandStatus,
    CollaborationChannel,
    ChannelStatus,
    AgentResponse,
    ResponseStatus,
)


class AgentProfileService:
    """Service for managing agent profiles."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(
        self,
        name: str,
        agent_type: str,
        description: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        pricing_info: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentProfile:
        """Create a new agent profile.

        Args:
            name: Agent name.
            agent_type: Type of agent.
            description: Agent description.
            capabilities: Agent capabilities.
            pricing_info: Pricing information.
            config: Agent configuration.

        Returns:
            Created agent profile.
        """
        agent = AgentProfile(
            id=str(uuid4()),
            name=name,
            agent_type=agent_type,
            description=description,
            capabilities=capabilities or {},
            pricing_info=pricing_info or {},
            config=config or {},
        )
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def get_by_id(self, agent_id: str) -> Optional[AgentProfile]:
        """Get agent profile by ID.

        Args:
            agent_id: Agent ID.

        Returns:
            Agent profile or None if not found.
        """
        result = await self.session.execute(
            select(AgentProfile).where(AgentProfile.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_type(self, agent_type: str) -> Sequence[AgentProfile]:
        """Get all agents of a specific type.

        Args:
            agent_type: Type of agent.

        Returns:
            List of agent profiles.
        """
        result = await self.session.execute(
            select(AgentProfile)
            .where(AgentProfile.agent_type == agent_type)
            .where(AgentProfile.is_active == True)  # noqa: E712
        )
        return result.scalars().all()

    async def list_active(
        self, limit: int = 100, offset: int = 0
    ) -> Sequence[AgentProfile]:
        """List all active agent profiles.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of agent profiles.
        """
        result = await self.session.execute(
            select(AgentProfile)
            .where(AgentProfile.is_active == True)  # noqa: E712
            .order_by(AgentProfile.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update(
        self, agent_id: str, **kwargs: Any
    ) -> Optional[AgentProfile]:
        """Update an agent profile.

        Args:
            agent_id: Agent ID.
            **kwargs: Fields to update.

        Returns:
            Updated agent profile or None if not found.
        """
        await self.session.execute(
            update(AgentProfile)
            .where(AgentProfile.id == agent_id)
            .values(**kwargs)
        )
        return await self.get_by_id(agent_id)

    async def deactivate(self, agent_id: str) -> bool:
        """Deactivate an agent profile.

        Args:
            agent_id: Agent ID.

        Returns:
            True if successful.
        """
        result = await self.session.execute(
            update(AgentProfile)
            .where(AgentProfile.id == agent_id)
            .values(is_active=False)
        )
        return result.rowcount > 0


class DemandService:
    """Service for managing demands."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(
        self,
        title: str,
        description: str,
        user_id: str,
        requirements: Optional[Dict[str, Any]] = None,
        budget: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Demand:
        """Create a new demand.

        Args:
            title: Demand title.
            description: Demand description.
            user_id: ID of user creating the demand.
            requirements: Detailed requirements.
            budget: Budget information.
            tags: Tags for categorization.
            extra_metadata: Additional metadata.

        Returns:
            Created demand.
        """
        demand = Demand(
            id=str(uuid4()),
            title=title,
            description=description,
            user_id=user_id,
            requirements=requirements or {},
            budget=budget or {},
            tags=tags or [],
            extra_metadata=extra_metadata or {},
            status=DemandStatus.DRAFT.value,
        )
        self.session.add(demand)
        await self.session.flush()
        return demand

    async def get_by_id(self, demand_id: str) -> Optional[Demand]:
        """Get demand by ID.

        Args:
            demand_id: Demand ID.

        Returns:
            Demand or None if not found.
        """
        result = await self.session.execute(
            select(Demand).where(Demand.id == demand_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> Sequence[Demand]:
        """Get all demands for a user.

        Args:
            user_id: User ID.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of demands.
        """
        result = await self.session.execute(
            select(Demand)
            .where(Demand.user_id == user_id)
            .order_by(Demand.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_published(
        self, limit: int = 100, offset: int = 0
    ) -> Sequence[Demand]:
        """List all published demands.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of published demands.
        """
        result = await self.session.execute(
            select(Demand)
            .where(Demand.status == DemandStatus.PUBLISHED.value)
            .order_by(Demand.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update_status(
        self, demand_id: str, status: DemandStatus
    ) -> Optional[Demand]:
        """Update demand status.

        Args:
            demand_id: Demand ID.
            status: New status.

        Returns:
            Updated demand or None if not found.
        """
        await self.session.execute(
            update(Demand)
            .where(Demand.id == demand_id)
            .values(status=status.value)
        )
        return await self.get_by_id(demand_id)

    async def update(self, demand_id: str, **kwargs: Any) -> Optional[Demand]:
        """Update a demand.

        Args:
            demand_id: Demand ID.
            **kwargs: Fields to update.

        Returns:
            Updated demand or None if not found.
        """
        await self.session.execute(
            update(Demand).where(Demand.id == demand_id).values(**kwargs)
        )
        return await self.get_by_id(demand_id)

    async def delete(self, demand_id: str) -> bool:
        """Delete a demand.

        Args:
            demand_id: Demand ID.

        Returns:
            True if successful.
        """
        result = await self.session.execute(
            delete(Demand).where(Demand.id == demand_id)
        )
        return result.rowcount > 0


class CollaborationChannelService:
    """Service for managing collaboration channels."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(
        self,
        name: str,
        demand_id: str,
        participants: Dict[str, Any],
        description: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> CollaborationChannel:
        """Create a new collaboration channel.

        Args:
            name: Channel name.
            demand_id: Associated demand ID.
            participants: Channel participants.
            description: Channel description.
            context: Collaboration context.
            settings: Channel settings.

        Returns:
            Created channel.
        """
        channel = CollaborationChannel(
            id=str(uuid4()),
            name=name,
            demand_id=demand_id,
            participants=participants,
            description=description,
            context=context or {},
            settings=settings or {},
            status=ChannelStatus.ACTIVE.value,
        )
        self.session.add(channel)
        await self.session.flush()
        return channel

    async def get_by_id(self, channel_id: str) -> Optional[CollaborationChannel]:
        """Get channel by ID.

        Args:
            channel_id: Channel ID.

        Returns:
            Channel or None if not found.
        """
        result = await self.session.execute(
            select(CollaborationChannel).where(
                CollaborationChannel.id == channel_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_demand(
        self, demand_id: str
    ) -> Sequence[CollaborationChannel]:
        """Get all channels for a demand.

        Args:
            demand_id: Demand ID.

        Returns:
            List of channels.
        """
        result = await self.session.execute(
            select(CollaborationChannel)
            .where(CollaborationChannel.demand_id == demand_id)
            .order_by(CollaborationChannel.created_at.desc())
        )
        return result.scalars().all()

    async def update_status(
        self, channel_id: str, status: ChannelStatus
    ) -> Optional[CollaborationChannel]:
        """Update channel status.

        Args:
            channel_id: Channel ID.
            status: New status.

        Returns:
            Updated channel or None if not found.
        """
        await self.session.execute(
            update(CollaborationChannel)
            .where(CollaborationChannel.id == channel_id)
            .values(status=status.value)
        )
        return await self.get_by_id(channel_id)

    async def increment_message_count(
        self, channel_id: str
    ) -> Optional[CollaborationChannel]:
        """Increment message count for a channel.

        Args:
            channel_id: Channel ID.

        Returns:
            Updated channel or None if not found.
        """
        from datetime import datetime, timezone

        channel = await self.get_by_id(channel_id)
        if channel:
            await self.session.execute(
                update(CollaborationChannel)
                .where(CollaborationChannel.id == channel_id)
                .values(
                    message_count=channel.message_count + 1,
                    last_message_at=datetime.now(timezone.utc),
                )
            )
            return await self.get_by_id(channel_id)
        return None


class AgentResponseService:
    """Service for managing agent responses."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(
        self,
        demand_id: str,
        agent_id: str,
        message: str,
        proposal: Optional[Dict[str, Any]] = None,
        relevance_score: Optional[float] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Create a new agent response.

        Args:
            demand_id: Associated demand ID.
            agent_id: Responding agent ID.
            message: Response message.
            proposal: Proposal details.
            relevance_score: Relevance score.
            extra_metadata: Additional metadata.

        Returns:
            Created response.
        """
        response = AgentResponse(
            id=str(uuid4()),
            demand_id=demand_id,
            agent_id=agent_id,
            message=message,
            proposal=proposal or {},
            relevance_score=relevance_score,
            extra_metadata=extra_metadata or {},
            status=ResponseStatus.PENDING.value,
        )
        self.session.add(response)
        await self.session.flush()
        return response

    async def get_by_id(self, response_id: str) -> Optional[AgentResponse]:
        """Get response by ID.

        Args:
            response_id: Response ID.

        Returns:
            Response or None if not found.
        """
        result = await self.session.execute(
            select(AgentResponse).where(AgentResponse.id == response_id)
        )
        return result.scalar_one_or_none()

    async def get_by_demand(
        self, demand_id: str
    ) -> Sequence[AgentResponse]:
        """Get all responses for a demand.

        Args:
            demand_id: Demand ID.

        Returns:
            List of responses.
        """
        result = await self.session.execute(
            select(AgentResponse)
            .where(AgentResponse.demand_id == demand_id)
            .order_by(AgentResponse.relevance_score.desc().nullslast())
        )
        return result.scalars().all()

    async def get_by_agent(
        self, agent_id: str
    ) -> Sequence[AgentResponse]:
        """Get all responses from an agent.

        Args:
            agent_id: Agent ID.

        Returns:
            List of responses.
        """
        result = await self.session.execute(
            select(AgentResponse)
            .where(AgentResponse.agent_id == agent_id)
            .order_by(AgentResponse.created_at.desc())
        )
        return result.scalars().all()

    async def update_status(
        self, response_id: str, status: ResponseStatus
    ) -> Optional[AgentResponse]:
        """Update response status.

        Args:
            response_id: Response ID.
            status: New status.

        Returns:
            Updated response or None if not found.
        """
        await self.session.execute(
            update(AgentResponse)
            .where(AgentResponse.id == response_id)
            .values(status=status.value)
        )
        return await self.get_by_id(response_id)
