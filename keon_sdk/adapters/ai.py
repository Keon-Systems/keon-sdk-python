"""
AI Call Adapter for Keon

Wraps AI provider calls (OpenAI, Anthropic, etc.) with Keon governance.
Every AI call goes through decide -> execute -> evidence.

Example:
    ```python
    from keon_sdk import KeonClient
    from keon_sdk.adapters import AIAdapter, create_ai_adapter

    client = KeonClient(base_url="...", api_key="...")
    ai = create_ai_adapter(client, AIAdapterConfig(
        tenant_id="tenant-123",
        actor_id="user-456",
        provider=OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"]),
    ))

    # Governed AI call
    response = await ai.chat(ChatRequest(
        model="gpt-4",
        messages=[ChatMessage(role="user", content="Hello!")],
    ))

    # response includes receipt for audit
    print(response.receipt.receipt_id)
    ```
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

from ..client import KeonClient
from ..contracts import DecisionReceipt, ExecutionResult


@dataclass
class ChatMessage:
    """Chat message."""

    role: str  # 'system' | 'user' | 'assistant' | 'function' | 'tool'
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class ChatRequest:
    """Chat completion request."""

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatChoice:
    """Chat choice."""

    index: int
    message: ChatMessage
    finish_reason: str


@dataclass
class TokenUsage:
    """Token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatResponse:
    """Chat completion response."""

    id: str
    model: str
    choices: List[ChatChoice]
    usage: Optional[TokenUsage] = None


@dataclass
class CompletionRequest:
    """Text completion request."""

    model: str
    prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stop: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompletionResponse:
    """Text completion response."""

    id: str
    model: str
    text: str
    usage: Optional[TokenUsage] = None


@dataclass
class EmbeddingRequest:
    """Embedding request."""

    model: str
    input: Union[str, List[str]]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingResponse:
    """Embedding response."""

    id: str
    model: str
    embeddings: List[List[float]]
    usage: Optional[TokenUsage] = None


@dataclass
class GovernedChatResponse(ChatResponse):
    """Governed chat response - includes receipt for audit."""

    receipt: Optional[DecisionReceipt] = None
    execution: Optional[ExecutionResult] = None


@dataclass
class GovernedCompletionResponse(CompletionResponse):
    """Governed completion response - includes receipt for audit."""

    receipt: Optional[DecisionReceipt] = None
    execution: Optional[ExecutionResult] = None


@dataclass
class GovernedEmbeddingResponse(EmbeddingResponse):
    """Governed embedding response - includes receipt for audit."""

    receipt: Optional[DecisionReceipt] = None
    execution: Optional[ExecutionResult] = None


class AIProvider(ABC):
    """AI Provider interface - implement for each AI service."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'openai', 'anthropic', 'gemini')."""
        ...

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Execute a chat completion."""
        ...

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a text completion (if supported)."""
        raise NotImplementedError(f"Provider {self.name} does not support completions")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Execute an embedding request (if supported)."""
        raise NotImplementedError(f"Provider {self.name} does not support embeddings")


@dataclass
class AIAdapterConfig:
    """AI Adapter configuration."""

    tenant_id: str
    actor_id: str
    provider: AIProvider
    default_context: Optional[Dict[str, Any]] = None
    on_denied: Optional[Callable[[DecisionReceipt], None]] = None
    throw_on_denial: bool = True


class AIGovernanceError(Exception):
    """Error thrown when AI call is denied by governance."""

    def __init__(self, message: str, receipt: DecisionReceipt):
        super().__init__(message)
        self.receipt = receipt


class AIAdapter:
    """Governed AI Adapter."""

    def __init__(self, client: KeonClient, config: AIAdapterConfig):
        self.client = client
        self.config = config

    async def chat(self, request: ChatRequest) -> GovernedChatResponse:
        """Execute a governed chat completion."""
        config = self.config

        # Step 1: Request decision
        receipt = await self.client.decide(
            tenant_id=config.tenant_id,
            actor_id=config.actor_id,
            action="ai.chat",
            resource_type="ai.model",
            resource_id=request.model,
            context={
                **(config.default_context or {}),
                **(request.metadata or {}),
                "provider": config.provider.name,
                "message_count": len(request.messages),
                "model": request.model,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
        )

        # Step 2: Handle denial
        if receipt.decision == "deny":
            if config.on_denied:
                config.on_denied(receipt)
            if config.throw_on_denial:
                raise AIGovernanceError("AI call denied by policy", receipt)
            return GovernedChatResponse(
                id="",
                model=request.model,
                choices=[],
                receipt=receipt,
                execution=None,
            )

        # Step 3: Execute the AI call
        execution = await self.client.execute(
            receipt=receipt,
            action="ai.chat",
            parameters={
                "model": request.model,
                "message_count": len(request.messages),
            },
        )

        # Step 4: Make the actual AI call
        response = await config.provider.chat(request)

        # Step 5: Return governed response
        return GovernedChatResponse(
            id=response.id,
            model=response.model,
            choices=response.choices,
            usage=response.usage,
            receipt=receipt,
            execution=execution,
        )

    async def complete(self, request: CompletionRequest) -> GovernedCompletionResponse:
        """Execute a governed text completion."""
        config = self.config

        # Step 1: Request decision
        receipt = await self.client.decide(
            tenant_id=config.tenant_id,
            actor_id=config.actor_id,
            action="ai.complete",
            resource_type="ai.model",
            resource_id=request.model,
            context={
                **(config.default_context or {}),
                **(request.metadata or {}),
                "provider": config.provider.name,
                "prompt_length": len(request.prompt),
                "model": request.model,
                "max_tokens": request.max_tokens,
            },
        )

        # Step 2: Handle denial
        if receipt.decision == "deny":
            if config.on_denied:
                config.on_denied(receipt)
            if config.throw_on_denial:
                raise AIGovernanceError("AI completion denied by policy", receipt)
            return GovernedCompletionResponse(
                id="",
                model=request.model,
                text="",
                receipt=receipt,
                execution=None,
            )

        # Step 3: Execute
        execution = await self.client.execute(
            receipt=receipt,
            action="ai.complete",
            parameters={
                "model": request.model,
                "prompt_length": len(request.prompt),
            },
        )

        # Step 4: Make the actual AI call
        response = await config.provider.complete(request)

        return GovernedCompletionResponse(
            id=response.id,
            model=response.model,
            text=response.text,
            usage=response.usage,
            receipt=receipt,
            execution=execution,
        )

    async def embed(self, request: EmbeddingRequest) -> GovernedEmbeddingResponse:
        """Execute a governed embedding request."""
        config = self.config

        input_count = len(request.input) if isinstance(request.input, list) else 1

        # Step 1: Request decision
        receipt = await self.client.decide(
            tenant_id=config.tenant_id,
            actor_id=config.actor_id,
            action="ai.embed",
            resource_type="ai.model",
            resource_id=request.model,
            context={
                **(config.default_context or {}),
                **(request.metadata or {}),
                "provider": config.provider.name,
                "input_count": input_count,
                "model": request.model,
            },
        )

        # Step 2: Handle denial
        if receipt.decision == "deny":
            if config.on_denied:
                config.on_denied(receipt)
            if config.throw_on_denial:
                raise AIGovernanceError("AI embedding denied by policy", receipt)
            return GovernedEmbeddingResponse(
                id="",
                model=request.model,
                embeddings=[],
                receipt=receipt,
                execution=None,
            )

        # Step 3: Execute
        execution = await self.client.execute(
            receipt=receipt,
            action="ai.embed",
            parameters={
                "model": request.model,
                "input_count": input_count,
            },
        )

        # Step 4: Make the actual AI call
        response = await config.provider.embed(request)

        return GovernedEmbeddingResponse(
            id=response.id,
            model=response.model,
            embeddings=response.embeddings,
            usage=response.usage,
            receipt=receipt,
            execution=execution,
        )


def create_ai_adapter(client: KeonClient, config: AIAdapterConfig) -> AIAdapter:
    """Factory function to create an AI adapter."""
    return AIAdapter(client, config)
