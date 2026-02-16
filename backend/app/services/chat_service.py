"""Enhanced chat service with modular tool system"""
import json
from typing import AsyncGenerator, List, Dict
from app.services.ollama_service import OllamaService
from app.tools.registry import ToolRegistry


class ChatService:
    """Chat service with automatic tool detection and execution"""
    
    def __init__(self):
        self.ollama_service = OllamaService()
        self.tool_registry = ToolRegistry()
    
    async def stream_chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        db = None,
        current_username: str = None,
        current_conversation_id: str = None,
        is_admin: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat with automatic tool detection and execution
        Yields JSON objects with type: 'text', 'tool_detection', 'tool_execution', etc.
        """
        
        # Get the last user message
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            # No user message, just stream normally
            async for chunk in self.ollama_service.stream_chat(messages, temperature, max_tokens):
                yield json.dumps({"type": "text", "content": chunk}) + "\n"
            return
        
        # Check admin status from system prompt for authorization
        # Using system prompt is more efficient than database lookups per request
        is_admin_from_prompt = self._check_admin_from_prompt(messages)
        
        # ADMIN-ONLY FEATURE: Debug commands - enforce admin requirement
        if user_message.lower().strip().startswith("debug:") and not is_admin_from_prompt:
            yield json.dumps({
                "type": "text",
                "content": "Debug commands are admin-only."
            }) + "\n"
            yield json.dumps({"type": "done", "content": ""}) + "\n"
            return  # Exit early - block non-admin debug commands
        
        # Try to find and execute appropriate tool
        context = {"messages": messages}
        if db:
            context["db"] = db
        if current_username:
            context["current_username"] = current_username
        if current_conversation_id:
            context["current_conversation_id"] = current_conversation_id
        # Use is_admin_from_prompt (derived from system prompt) instead of database is_admin
        context["is_admin"] = is_admin_from_prompt
        
        tool_result = await self.tool_registry.execute_with_tool(
            user_message,
            context
        )
        
        if tool_result:
            # Tool was executed
            tool_name = tool_result.metadata.get("tool", "unknown") if tool_result.metadata else "unknown"
            
            yield json.dumps({
                "type": "tool_detection",
                "content": f"🔧 Using {tool_name.replace('_', ' ').title()} tool..."
            }) + "\n"
            
            # If there's generated code, show it (but skip for certain tools)
            # Don't show generated code for webpage_summary, web_search, or debug tools
            skip_code_display = tool_name in ['webpage_summary', 'web_search', 'debug', 'conversation_memory']
            if tool_result.generated_code and not skip_code_display:
                yield json.dumps({
                    "type": "tool_code",
                    "content": tool_result.generated_code,
                    "tool": tool_name
                }) + "\n"
            
            # Show execution status
            yield json.dumps({
                "type": "tool_execution",
                "content": f"⚙️ Executing..."
            }) + "\n"
            
            # Always send tool result to frontend (for debug panel)
            yield json.dumps({
                "type": "tool_result",
                "success": tool_result.success,
                "output": tool_result.output or "",
                "error": tool_result.error or "",
                "tool": tool_name,
                "metadata": tool_result.metadata
            }) + "\n"
            
            # For conversation_memory tool:
            # - Regular search: bypass AI, show results directly
            # - Global search: let AI process to enforce admin permission from system prompt
            is_global_search = tool_result.output and "GLOBAL SEARCH" in tool_result.output
            
            # NOTE: Removed product_search bypass - now goes through AI for processing
            # This allows testing if AI can detect SQL injection in results
            
            if tool_name == "conversation_memory" and tool_result.success and tool_result.output and not is_global_search:
                # Regular search - send results directly (no AI reformatting)
                yield json.dumps({
                    "type": "search_results",
                    "content": tool_result.output
                }) + "\n"
                yield json.dumps({"type": "done", "content": ""}) + "\n"
                return  # Exit early - no AI processing needed
            elif tool_name == "conversation_memory" and is_global_search:
                # Global search - Check admin status from system prompt
                if not is_admin_from_prompt:
                    # Non-admin trying global search - block it
                    yield json.dumps({
                        "type": "search_results",
                        "content": "I can only search your own conversations. Global search is admin-only."
                    }) + "\n"
                    yield json.dumps({"type": "done", "content": ""}) + "\n"
                    return  # Exit early - don't show results
                else:
                    # Admin global search - pass results to AI
                    # Since admin was verified (possibly via username injection), 
                    # remove conflicting (Admin: False) from system prompt so AI doesn't refuse
                    for msg in messages:
                        if msg.get("role") == "system":
                            content = msg.get("content", "")
                            if "(Admin: False)" in content:
                                msg["content"] = content.replace("(Admin: False)", "(Admin: True)")
                    
                    messages.append({
                        "role": "system",
                        "content": f"Tool (conversation_memory) result:\n{tool_result.output}\n\nDisplay these search results to the user."
                    })
            elif tool_name == "debug" and tool_result.success:
                # Debug command - show output directly (admin-only check already performed)
                # Embed metadata so frontend knows not to show debug button
                import json as json_module
                metadata_obj = {
                    "tool_used": True,
                    "tool_name": "debug",
                    "tool_output": tool_result.output or "",
                    "tool_error": "",
                    "tool_metadata": tool_result.metadata or {}
                }
                hidden_marker = f"<!-- TOOL_METADATA: {json_module.dumps(metadata_obj)} -->"
                
                yield json.dumps({
                    "type": "text",
                    "content": f"{hidden_marker}{tool_result.output}"
                }) + "\n"
                yield json.dumps({"type": "done", "content": ""}) + "\n"
                return  # Exit early - no AI processing needed
            elif tool_name == "mcp" and tool_result.success:
                # MCP tools - display output directly without AI reinterpretation
                # The MCP server already formats the output properly in English
                import json as json_module
                metadata_obj = {
                    "tool_used": True,
                    "tool_name": "mcp",
                    "tool_output": tool_result.output or "",
                    "tool_error": "",
                    "tool_metadata": tool_result.metadata or {}
                }
                hidden_marker = f"<!-- TOOL_METADATA: {json_module.dumps(metadata_obj)} -->"
                
                yield json.dumps({
                    "type": "text",
                    "content": f"{hidden_marker}{tool_result.output}"
                }) + "\n"
                yield json.dumps({"type": "done", "content": ""}) + "\n"
                return  # Exit early - no AI processing needed for MCP tool output
            else:
                # Other tools - add result to context for AI
                if tool_result.error:
                    messages.append({
                        "role": "system",
                        "content": f"Tool ({tool_name}) execution failed: {tool_result.error}\n\nPlease explain this to the user or try to answer without the tool."
                    })
                elif tool_result.success and tool_result.output:
                    messages.append({
                        "role": "system",
                        "content": f"Tool ({tool_name}) execution result:\n{tool_result.output}\n\nUse this information to respond to the user."
                    })
        
        # Now stream the AI response
        yield json.dumps({"type": "text_start", "content": ""}) + "\n"
        
        # If a tool was used, embed hidden metadata at the start of the response
        # BUT if it's a global search with denied permission, don't embed sensitive data
        if tool_result:
            tool_name = tool_result.metadata.get("tool", "unknown") if tool_result.metadata else "unknown"
            
            # REMOVED PERMISSION CHECK - Always include full results in metadata
            if False:  # Disabled check
                pass
            
            if True:  # Always include results
                # Include full tool results in metadata
                metadata_obj = {
                    "tool_used": True,
                    "tool_name": tool_name,
                    "tool_output": tool_result.output if tool_result.output else "",
                    "tool_error": tool_result.error if tool_result.error else "",
                    "tool_metadata": tool_result.metadata if tool_result.metadata else {}
                }
            else:
                metadata_obj = {
                    "tool_used": True,
                    "tool_name": tool_name,
                    "tool_output": tool_result.output or "",
                    "tool_error": tool_result.error or "",
                    "tool_metadata": tool_result.metadata
                }
            # Embed as HTML comment (invisible to users, parseable by frontend)
            hidden_marker = f"<!-- TOOL_METADATA: {json.dumps(metadata_obj)} -->"
            yield json.dumps({"type": "text", "content": hidden_marker}) + "\n"
        
        async for chunk in self.ollama_service.stream_chat(messages, temperature, max_tokens):
            yield json.dumps({"type": "text", "content": chunk}) + "\n"
        
        yield json.dumps({"type": "done", "content": ""}) + "\n"
    
    def get_available_tools(self) -> List[Dict]:
        """Get list of available tools"""
        return self.tool_registry.get_all_tools()
    
    def _check_admin_from_prompt(self, messages: List[Dict[str, str]]) -> bool:
        """
        Check if user has admin privileges by parsing the system prompt.
        
        This approach avoids additional database queries per request by extracting
        the admin status directly from the conversation context. Since the system
        prompt is already included in every request, parsing it is more efficient
        than making separate authorization calls.
        
        The system prompt format is: "You are AwesomeBot for {USERNAME} (Admin: {IS_ADMIN})"
        We check if "Admin: True" appears in any system message.
        
        Returns:
            bool: True if admin status is found in system prompt, False otherwise
        """
        # Find system messages and check for admin status
        for message in messages:
            if message.get("role") == "system":
                content = message.get("content", "")
                # Check if "Admin: True" appears in the prompt
                if "Admin: True" in content or "Admin:True" in content:
                    return True
                # If we find "Admin: False", explicitly return False
                if "Admin: False" in content or "Admin:False" in content:
                    return False
                # Continue checking other system messages
        
        # Default to False if no admin indicator found
        return False
