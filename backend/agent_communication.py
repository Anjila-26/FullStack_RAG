import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from loguru import logger
import json

class MessageType(Enum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    COORDINATION = "coordination"
    BROADCAST = "broadcast"

class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK_REQUEST
    sender: str = ""
    recipient: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    correlation_id: Optional[str] = None

@dataclass
class AgentInfo:
    name: str
    status: AgentStatus = AgentStatus.IDLE
    capabilities: List[str] = field(default_factory=list)
    last_seen: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    error_count: int = 0

class SharedMemory:
    """Shared memory system for agents"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._subscribers: Dict[str, List[str]] = {}  # key -> list of agent names
    
    async def set(self, key: str, value: Any, agent_name: str = "system"):
        """Set a value in shared memory"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        
        async with self._locks[key]:
            old_value = self._data.get(key)
            self._data[key] = {
                "value": value,
                "timestamp": datetime.now(),
                "last_updated_by": agent_name
            }
            
            # Notify subscribers
            if key in self._subscribers:
                for subscriber in self._subscribers[key]:
                    logger.debug(f"Notifying {subscriber} of update to {key}")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from shared memory"""
        if key in self._data:
            return self._data[key]["value"]
        return default
    
    async def subscribe(self, key: str, agent_name: str):
        """Subscribe to changes in a key"""
        if key not in self._subscribers:
            self._subscribers[key] = []
        if agent_name not in self._subscribers[key]:
            self._subscribers[key].append(agent_name)
    
    async def get_all_keys(self) -> List[str]:
        """Get all available keys"""
        return list(self._data.keys())
    
    async def clear(self, key: str = None):
        """Clear specific key or all data"""
        if key:
            self._data.pop(key, None)
            self._locks.pop(key, None)
            self._subscribers.pop(key, None)
        else:
            self._data.clear()
            self._locks.clear()
            self._subscribers.clear()

class MessageBus:
    """Central message bus for agent communication"""
    
    def __init__(self):
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.agents: Dict[str, AgentInfo] = {}
        self.message_handlers: Dict[str, Dict[MessageType, Callable]] = {}
        self.message_history: List[Message] = []
        self.shared_memory = SharedMemory()
    
    def register_agent(self, name: str, capabilities: List[str] = None):
        """Register a new agent"""
        if capabilities is None:
            capabilities = []
        
        self.agents[name] = AgentInfo(name=name, capabilities=capabilities)
        self.message_queues[name] = asyncio.Queue()
        self.message_handlers[name] = {}
        logger.info(f"Registered agent: {name} with capabilities: {capabilities}")
    
    def register_handler(self, agent_name: str, message_type: MessageType, handler: Callable):
        """Register a message handler for an agent"""
        if agent_name not in self.message_handlers:
            self.message_handlers[agent_name] = {}
        self.message_handlers[agent_name][message_type] = handler
        logger.debug(f"Registered handler for {agent_name}: {message_type}")
    
    async def send_message(self, message: Message) -> bool:
        """Send a message to an agent"""
        try:
            if message.recipient not in self.message_queues:
                logger.error(f"Agent {message.recipient} not found")
                return False
            
            # Update sender status
            if message.sender in self.agents:
                self.agents[message.sender].message_count += 1
                self.agents[message.sender].last_seen = datetime.now()
            
            # Add to message history
            self.message_history.append(message)
            if len(self.message_history) > 1000:  # Keep last 1000 messages
                self.message_history.pop(0)
            
            # Send to recipient's queue
            await self.message_queues[message.recipient].put(message)
            logger.debug(f"Message sent from {message.sender} to {message.recipient}: {message.type}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def broadcast_message(self, message: Message, exclude: List[str] = None) -> int:
        """Broadcast a message to all agents (except excluded ones)"""
        if exclude is None:
            exclude = []
        
        sent_count = 0
        for agent_name in self.agents.keys():
            if agent_name not in exclude and agent_name != message.sender:
                message_copy = Message(
                    type=message.type,
                    sender=message.sender,
                    recipient=agent_name,
                    content=message.content.copy(),
                    requires_response=message.requires_response,
                    correlation_id=message.correlation_id
                )
                if await self.send_message(message_copy):
                    sent_count += 1
        
        logger.info(f"Broadcast message sent to {sent_count} agents")
        return sent_count
    
    async def get_message(self, agent_name: str, timeout: float = None) -> Optional[Message]:
        """Get a message for an agent"""
        if agent_name not in self.message_queues:
            return None
        
        try:
            if timeout:
                message = await asyncio.wait_for(
                    self.message_queues[agent_name].get(), 
                    timeout=timeout
                )
            else:
                message = await self.message_queues[agent_name].get()
            
            # Update agent status
            if agent_name in self.agents:
                self.agents[agent_name].last_seen = datetime.now()
            
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting message for {agent_name}: {e}")
            return None
    
    async def update_agent_status(self, agent_name: str, status: AgentStatus):
        """Update agent status"""
        if agent_name in self.agents:
            self.agents[agent_name].status = status
            self.agents[agent_name].last_seen = datetime.now()
            
            # Broadcast status update
            status_message = Message(
                type=MessageType.STATUS_UPDATE,
                sender=agent_name,
                content={"status": status.value, "timestamp": datetime.now().isoformat()}
            )
            await self.broadcast_message(status_message, exclude=[agent_name])
    
    def get_agent_status(self, agent_name: str) -> Optional[AgentInfo]:
        """Get agent status and info"""
        return self.agents.get(agent_name)
    
    def get_all_agents(self) -> Dict[str, AgentInfo]:
        """Get all registered agents"""
        return self.agents.copy()
    
    async def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability"""
        agents = []
        for name, info in self.agents.items():
            if capability in info.capabilities and info.status != AgentStatus.OFFLINE:
                agents.append(name)
        return agents
    
    def get_message_history(self, limit: int = 100) -> List[Message]:
        """Get recent message history"""
        return self.message_history[-limit:]

# Global message bus instance
message_bus = MessageBus()

class BaseAgent:
    """Base class for all agents with communication capabilities"""
    
    def __init__(self, name: str, capabilities: List[str] = None):
        self.name = name
        self.capabilities = capabilities or []
        self.is_running = False
        self.message_bus = message_bus
        
        # Register with message bus
        self.message_bus.register_agent(name, capabilities)
        
        # Register default handlers
        self.register_default_handlers()
    
    def register_default_handlers(self):
        """Register default message handlers"""
        self.message_bus.register_handler(
            self.name, 
            MessageType.STATUS_UPDATE, 
            self.handle_status_update
        )
        self.message_bus.register_handler(
            self.name, 
            MessageType.COORDINATION, 
            self.handle_coordination
        )
    
    async def start(self):
        """Start the agent"""
        self.is_running = True
        await self.message_bus.update_agent_status(self.name, AgentStatus.IDLE)
        logger.info(f"Agent {self.name} started")
        
        # Start message processing loop
        asyncio.create_task(self.message_processing_loop())
    
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        await self.message_bus.update_agent_status(self.name, AgentStatus.OFFLINE)
        logger.info(f"Agent {self.name} stopped")
    
    async def message_processing_loop(self):
        """Main message processing loop"""
        while self.is_running:
            try:
                message = await self.message_bus.get_message(self.name, timeout=1.0)
                if message:
                    await self.process_message(message)
            except Exception as e:
                logger.error(f"Error in message processing loop for {self.name}: {e}")
                await asyncio.sleep(1)
    
    async def process_message(self, message: Message):
        """Process incoming message"""
        try:
            await self.message_bus.update_agent_status(self.name, AgentStatus.BUSY)
            
            # Find appropriate handler
            handlers = self.message_bus.message_handlers.get(self.name, {})
            handler = handlers.get(message.type)
            
            if handler:
                await handler(message)
            else:
                logger.warning(f"No handler for message type {message.type} in agent {self.name}")
            
            await self.message_bus.update_agent_status(self.name, AgentStatus.IDLE)
            
        except Exception as e:
            logger.error(f"Error processing message in {self.name}: {e}")
            await self.message_bus.update_agent_status(self.name, AgentStatus.ERROR)
            
            # Send error response if required
            if message.requires_response:
                error_response = Message(
                    type=MessageType.ERROR,
                    sender=self.name,
                    recipient=message.sender,
                    content={"error": str(e), "original_message_id": message.id},
                    correlation_id=message.correlation_id
                )
                await self.message_bus.send_message(error_response)
    
    async def send_message(self, recipient: str, message_type: MessageType, 
                          content: Dict[str, Any], requires_response: bool = False) -> bool:
        """Send a message to another agent"""
        message = Message(
            type=message_type,
            sender=self.name,
            recipient=recipient,
            content=content,
            requires_response=requires_response
        )
        return await self.message_bus.send_message(message)
    
    async def broadcast_message(self, message_type: MessageType, content: Dict[str, Any]) -> int:
        """Broadcast a message to all other agents"""
        message = Message(
            type=message_type,
            sender=self.name,
            content=content
        )
        return await self.message_bus.broadcast_message(message, exclude=[self.name])
    
    async def request_task(self, recipient: str, task_type: str, 
                          task_data: Dict[str, Any]) -> Message:
        """Send a task request and wait for response"""
        correlation_id = str(uuid.uuid4())
        
        request = Message(
            type=MessageType.TASK_REQUEST,
            sender=self.name,
            recipient=recipient,
            content={"task_type": task_type, "data": task_data},
            requires_response=True,
            correlation_id=correlation_id
        )
        
        await self.message_bus.send_message(request)
        
        # Wait for response
        timeout = 30.0  # 30 seconds timeout
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            message = await self.message_bus.get_message(self.name, timeout=1.0)
            if (message and message.type == MessageType.TASK_RESPONSE and 
                message.correlation_id == correlation_id):
                return message
        
        raise TimeoutError(f"No response received from {recipient} for task {task_type}")
    
    async def handle_status_update(self, message: Message):
        """Handle status update messages"""
        sender_status = message.content.get("status")
        logger.debug(f"Agent {message.sender} status updated to: {sender_status}")
    
    async def handle_coordination(self, message: Message):
        """Handle coordination messages"""
        coordination_type = message.content.get("type")
        logger.debug(f"Coordination message from {message.sender}: {coordination_type}")
    
    # Shared memory convenience methods
    async def set_shared_data(self, key: str, value: Any):
        """Set data in shared memory"""
        await self.message_bus.shared_memory.set(key, value, self.name)
    
    async def get_shared_data(self, key: str, default: Any = None):
        """Get data from shared memory"""
        return await self.message_bus.shared_memory.get(key, default)
    
    async def subscribe_to_shared_data(self, key: str):
        """Subscribe to changes in shared data"""
        await self.message_bus.shared_memory.subscribe(key, self.name)

# Utility functions for coordination
async def coordinate_agents(initiator: str, participants: List[str], 
                           coordination_type: str, data: Dict[str, Any]) -> List[Message]:
    """Coordinate multiple agents for a task"""
    correlation_id = str(uuid.uuid4())
    responses = []
    
    # Send coordination messages
    for participant in participants:
        coord_message = Message(
            type=MessageType.COORDINATION,
            sender=initiator,
            recipient=participant,
            content={
                "type": coordination_type,
                "data": data,
                "participants": participants
            },
            requires_response=True,
            correlation_id=correlation_id
        )
        await message_bus.send_message(coord_message)
    
    # Collect responses
    timeout = 30.0
    start_time = datetime.now()
    
    while len(responses) < len(participants) and (datetime.now() - start_time).total_seconds() < timeout:
        for participant in participants:
            message = await message_bus.get_message(initiator, timeout=1.0)
            if (message and message.correlation_id == correlation_id and 
                message.sender == participant):
                responses.append(message)
    
    return responses

async def get_system_status() -> Dict[str, Any]:
    """Get overall system status"""
    agents = message_bus.get_all_agents()
    
    status = {
        "total_agents": len(agents),
        "active_agents": len([a for a in agents.values() if a.status != AgentStatus.OFFLINE]),
        "agents": {name: {
            "status": info.status.value,
            "capabilities": info.capabilities,
            "message_count": info.message_count,
            "error_count": info.error_count,
            "last_seen": info.last_seen.isoformat()
        } for name, info in agents.items()},
        "shared_memory_keys": await message_bus.shared_memory.get_all_keys(),
        "recent_messages": len(message_bus.get_message_history(50))
    }
    
    return status

class SimpleMessageBus:
    """Simple message bus for basic agent communication"""
    
    def __init__(self):
        self.agents = {}
        self.shared_data = {}
        # Register a system coordinator by default
        self.register_agent("system")
    
    def register_agent(self, name: str, handler_func=None):
        """Register an agent with optional message handler"""
        self.agents[name] = {
            "status": "idle",
            "handler": handler_func,
            "messages": []
        }
        logger.info(f"Registered agent: {name}")
    
    async def send_message(self, from_agent: str, to_agent: str, message_type: str, data: dict):
        """Send a simple message between agents"""
        if to_agent not in self.agents:
            # Instead of error, just log and ignore messages to non-existent agents
            logger.debug(f"Message ignored: {to_agent} not found (from {from_agent})")
            return False
        
        message = {
            "from": from_agent,
            "type": message_type,
            "data": data,
            "timestamp": datetime.now()
        }
        
        self.agents[to_agent]["messages"].append(message)
        
        # Call handler if available
        if self.agents[to_agent]["handler"]:
            try:
                await self.agents[to_agent]["handler"](message)
            except Exception as e:
                logger.error(f"Error in handler for {to_agent}: {e}")
        
        logger.debug(f"Message sent: {from_agent} -> {to_agent} ({message_type})")
        return True
    
    def get_messages(self, agent_name: str):
        """Get all messages for an agent"""
        if agent_name in self.agents:
            messages = self.agents[agent_name]["messages"].copy()
            self.agents[agent_name]["messages"].clear()  # Clear after reading
            return messages
        return []
    
    def set_shared_data(self, key: str, value: Any, agent_name: str = "system"):
        """Set shared data"""
        self.shared_data[key] = {
            "value": value,
            "updated_by": agent_name,
            "timestamp": datetime.now()
        }
        logger.debug(f"Shared data set: {key} by {agent_name}")
    
    def get_shared_data(self, key: str, default=None):
        """Get shared data"""
        if key in self.shared_data:
            return self.shared_data[key]["value"]
        return default
    
    def update_agent_status(self, agent_name: str, status: str):
        """Update agent status"""
        if agent_name in self.agents:
            self.agents[agent_name]["status"] = status
            logger.debug(f"Agent {agent_name} status: {status}")

class SimpleAgent:
    """Simple base agent class"""
    
    def __init__(self, name: str):
        self.name = name
        self.bus = simple_bus
        self.bus.register_agent(name, self.handle_message)
    
    async def handle_message(self, message):
        """Handle incoming messages - override in subclasses"""
        logger.debug(f"{self.name} received: {message['type']} from {message['from']}")
    
    async def send_message(self, to_agent: str, message_type: str, data: dict):
        """Send message to another agent"""
        return await self.bus.send_message(self.name, to_agent, message_type, data)
    
    def set_status(self, status: str):
        """Update agent status"""
        self.bus.update_agent_status(self.name, status)
    
    def set_shared_data(self, key: str, value: Any):
        """Set shared data"""
        self.bus.set_shared_data(key, value, self.name)
    
    def get_shared_data(self, key: str, default=None):
        """Get shared data"""
        return self.bus.get_shared_data(key, default)

class SimpleCoordinator(SimpleAgent):
    """Simple system coordinator"""
    
    def __init__(self):
        super().__init__("system")
        self.activity_log = []
    
    async def handle_message(self, message):
        """Handle system messages and log activities"""
        if message["type"] == "status_update":
            data = message["data"]
            activity = {
                "agent": data.get("agent", message["from"]),
                "activity": data.get("activity", "unknown"),
                "timestamp": message["timestamp"],
                "details": data
            }
            self.activity_log.append(activity)
            
            # Keep only last 100 activities
            if len(self.activity_log) > 100:
                self.activity_log.pop(0)
            
            logger.info(f"Activity logged: {activity['agent']} - {activity['activity']}")
    
    def get_recent_activities(self, limit=10):
        """Get recent activities"""
        return self.activity_log[-limit:]

# Global simple message bus
simple_bus = SimpleMessageBus()
coordinator = SimpleCoordinator()
