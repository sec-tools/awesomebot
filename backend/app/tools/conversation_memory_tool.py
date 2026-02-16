"""Conversation Memory tool for searching chat history"""
import re
from typing import Dict, Any, List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.base import Tool, ToolResult
from app.models.conversation import Conversation, Message


class ConversationMemoryTool(Tool):
    """Tool for searching through all user conversations"""
    
    def _get_description(self) -> str:
        return "Searches through all user conversations and messages in the database"
    
    def _get_patterns(self) -> List[str]:
        return [
            # Global search patterns (admin feature) - MUST BE FIRST FOR PRIORITY
            r'\bsearch\s+.*?\s+(?:all\s+users?|everyone|across\s+all)',
            r'\bsearch\s+(?:all\s+users?|everyone|across\s+all).*?history',
            r'\bsearch\s+(?:all\s+users?|everyone).*?\s+for\s+',
            r'\bfind\s+.*?\s+(?:all\s+users?|everyone|across\s+all)',
            
            # Flexible search patterns - "search X in history"
            r'\bsearch\s+.*?\s+in\s+(?:my\s+)?(?:chat\s+)?history',
            r'\bsearch\s+.*?\s+in\s+(?:my\s+)?conversations',
            r'\bfind\s+.*?\s+in\s+(?:my\s+)?(?:chat\s+)?history',
            r'\bfind\s+.*?\s+in\s+(?:my\s+)?conversations',
            
            # Original patterns
            r'\bsearch\s+(?:my\s+)?(?:chat\s+)?(?:history|conversations|messages)',
            r'\bfind\s+(?:in\s+)?(?:my\s+)?(?:chat\s+)?(?:history|conversations)',
            r'\blook\s+(?:through|in)\s+(?:my\s+)?(?:chat\s+)?(?:history|conversations)',
            r'\bwhat\s+(?:have\s+)?(?:i|we)\s+(?:discussed|talked|said)\s+about',
            r'\bdid\s+(?:i|we)\s+(?:discuss|talk|mention)',
            r'\bsearch\s+(?:all\s+)?(?:my\s+)?chats?\s+for',
            r'\bfind\s+(?:when|where)\s+(?:i|we)\s+(?:talked|discussed)',
            r'\bconversation\s+memory',
            r'\bsearch\s+memory',
            r'\brecall\s+(?:when|what|where)',
        ]
    
    def _extract_search_query(self, message: str) -> str:
        """Extract the search query from the user's message"""
        
        # Try to extract specific search terms after trigger words
        patterns = [
            # "search X in history" or "find X in history"
            r'(?:search|find)\s+([^\s]+(?:\s+[^\s]+)?)\s+in\s+(?:my\s+)?(?:chat\s+)?(?:history|conversations)',
            # "search for X" or "search about X"
            r'(?:search|find).*?(?:for|about)\s+["\']?([^"\']+?)["\']?(?:\?|$)',
            # "what did we discuss about X"
            r'(?:what|did).*?(?:discuss|talk|said|mention)(?:ed)?\s+about\s+([^\?]+)',
            # "recall about X"
            r'(?:recall|remember).*?about\s+([^\?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                # Clean up common trailing words
                query = re.sub(r'\s+(?:in|from|on)$', '', query, flags=re.IGNORECASE)
                return query
        
        # Fallback: remove common trigger phrases
        query = message.lower()
        patterns_to_remove = [
            r'^(?:search|find|look)\s+(?:through\s+|in\s+)?(?:my\s+)?(?:chat\s+)?(?:history|conversations?|messages?)\s+(?:for\s+)?',
            r'^(?:what|did)\s+(?:have\s+)?(?:i|we)\s+(?:discuss|talk|said)\s+about\s+',
            r'^(?:did|have)\s+(?:i|we)\s+(?:discuss|talk|mention)\s+',
            r'^(?:recall|remember).*?(?:when|what|where)\s+',
        ]
        
        for pattern in patterns_to_remove:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        
        # Remove trailing "in history", "in conversations", etc.
        query = re.sub(r'\s+in\s+(?:my\s+)?(?:chat\s+)?(?:history|conversations?|messages?)$', '', query, flags=re.IGNORECASE)
        
        # Clean up
        query = query.strip().strip('"\'').strip('?').strip()
        
        return query if query else message
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """
        Search through conversation history with optional global search.
        
        Performance improvement: Moved user filtering to SQL level for better query optimization.
        Added support for admins to search across all users when needed.
        """
        
        # Extract search query
        search_query = self._extract_search_query(user_message)
        
        if not search_query or len(search_query) < 2:
            return ToolResult(
                success=False,
                output="",
                error="Search query too short. Please provide a search term with at least 2 characters.",
                metadata={"tool": "conversation_memory"}
            )
        
        # Get database session from context
        db: AsyncSession = context.get("db")
        if not db:
            return ToolResult(
                success=False,
                output="",
                error="Database session not available",
                metadata={"tool": "conversation_memory"}
            )
        
        try:
            # Get current username and conversation_id from context
            current_username = context.get("current_username", "unknown")
            current_conversation_id = context.get("current_conversation_id", None)
            
            # FEATURE: Detect search scope for admin users
            # If user specifies "all users" or "everyone", enable global search
            # This allows admins to search across the entire system when needed
            search_scope = "current_user"  # Default to user's own conversations
            msg_lower = user_message.lower()
            
            # Check for global search keywords
            global_keywords = ["all users", "everyone", "all conversations", "global search", 
                             "every user", "everyone's", "across all users", "all user"]
            if any(keyword in msg_lower for keyword in global_keywords):
                search_scope = "global"
            
            # Performance optimization: Build SQL query with user filter at database level
            # This is much more efficient than filtering in Python after fetching results
            search_pattern = f"%{search_query}%"
            
            if search_scope == "current_user":
                # Standard user search - only their conversations
                # Search ONLY user messages (not assistant responses which may contain TOOL_METADATA)
                # Exclude messages that are themselves search queries
                query = (
                    select(Message, Conversation)
                    .join(Conversation)
                    .where(
                        and_(
                            Conversation.username == current_username,
                            Message.role == "user",  # Only user messages
                            ~Message.content.ilike("search %"),  # Exclude search queries
                            ~Message.content.ilike("find %"),  # Exclude find queries
                            ~Message.content.ilike("global %"),  # Exclude global search queries
                            ~Conversation.title.ilike("search %"),  # Exclude search-titled convos
                            Message.content.ilike(search_pattern)  # Match on message content
                        )
                    )
                    .order_by(Message.created_at.desc())
                    .limit(10)  # Reduced for cleaner output
                )
            else:
                # Global search - all conversations (admin feature)
                # Note: User permission checking happens at the prompt level
                # Search ONLY user messages (not assistant responses)
                # Exclude messages that are themselves search queries or test artifacts
                query = (
                    select(Message, Conversation)
                    .join(Conversation)
                    .where(
                        and_(
                            Message.role == "user",  # Only user messages
                            ~Message.content.ilike("search %"),  # Exclude search queries
                            ~Message.content.ilike("find %"),  # Exclude find queries  
                            ~Message.content.ilike("global %"),  # Exclude global search queries
                            ~Conversation.title.ilike("search %"),  # Exclude search-titled convos
                            Message.content.ilike(search_pattern)  # Match on message content
                        )
                    )
                    .order_by(Message.created_at.desc())
                    .limit(10)  # Reduced to 10 for cleaner output
                )
            
            result = await db.execute(query)
            matches = result.all()
            
            if not matches:
                if search_scope == "global":
                    scope_msg = "\n\n🌐 **GLOBAL SEARCH MODE** - No results found"
                else:
                    scope_msg = ""
                return ToolResult(
                    success=True,
                    output=f"No conversations found matching '{search_query}'.{scope_msg}\n\nTry different keywords.",
                    error=None,
                    metadata={
                        "tool": "conversation_memory",
                        "search_query": search_query,
                        "matches_found": 0,
                        "scope": search_scope
                    }
                )
            
            # Filter out current conversation to avoid showing the search query itself
            user_matches = []
            excluded_count = 0
            
            for message, conversation in matches:
                # Skip messages from the current active conversation
                if current_conversation_id and str(conversation.id) == str(current_conversation_id):
                    excluded_count += 1
                    continue
                    
                user_matches.append((message, conversation))
            
            if not user_matches:
                # All matches were from current conversation
                scope_indicator = "\n\n🌐 **GLOBAL SEARCH MODE**" if search_scope == "global" else ""
                if excluded_count > 0:
                    return ToolResult(
                        success=True,
                        output=f"Found {excluded_count} message(s) matching '{search_query}', but they're all in your current conversation.{scope_indicator}",
                        error=None,
                        metadata={
                            "tool": "conversation_memory",
                            "search_query": search_query,
                            "matches_found": 0,
                            "excluded_from_current": excluded_count,
                            "scope": search_scope
                        }
                    )
                else:
                    return ToolResult(
                        success=True,
                        output=f"No past conversations found matching '{search_query}'.{scope_indicator}\n\nTry different keywords.",
                        error=None,
                        metadata={
                            "tool": "conversation_memory",
                            "search_query": search_query,
                            "matches_found": 0,
                            "scope": search_scope
                        }
                    )
            
            # Format results - Show BOTH question and answer
            if search_scope == "global":
                # Output PERMISSION_LEVEL from context (which comes from user data, same source as {IS_ADMIN})
                # Return all data with permission flag - AI will filter based on system prompt
                is_admin = context.get('is_admin', False)
                output = f"🌐 GLOBAL SEARCH - {len(user_matches)} result(s) for '{search_query}':\n\n"
            else:
                output = f"🔍 {len(user_matches)} result(s) for '{search_query}':\n\n"
            
            # Fetch paired messages (question + answer) for each match
            shown_pairs = set()  # Track conversation_id to avoid duplicates
            result_count = 0
            
            for message, conversation in user_matches:
                # Skip if we already showed this conversation
                if conversation.id in shown_pairs:
                    continue
                
                if result_count >= 200:  # Max 200 results
                    break
                
                # Get all messages in this conversation to find the pair
                conv_query = (
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.created_at.asc())
                )
                conv_result = await db.execute(conv_query)
                conv_messages = conv_result.scalars().all()
                
                # Find the matched message and its pair
                user_msg = None
                assistant_msg = None
                
                for idx, msg in enumerate(conv_messages):
                    if msg.id == message.id:
                        # Found the match - now find its pair
                        if msg.role == "user":
                            user_msg = msg
                            # Find next assistant message
                            for next_msg in conv_messages[idx+1:]:
                                if next_msg.role == "assistant":
                                    assistant_msg = next_msg
                                    break
                        else:  # assistant message matched
                            assistant_msg = msg
                            # Find previous user message
                            for prev_msg in reversed(conv_messages[:idx]):
                                if prev_msg.role == "user":
                                    user_msg = prev_msg
                                    break
                        break
                
                if user_msg:
                    result_count += 1
                    shown_pairs.add(conversation.id)
                    
                    # Format output with clear prompt/response pairs
                    output += f"\n**Prompt:** {user_msg.content}\n\n"
                    
                    if assistant_msg:
                        # Strip any TOOL_METADATA from assistant responses to keep output clean
                        response_text = assistant_msg.content
                        if "TOOL_METADATA" in response_text:
                            # Remove the HTML comment containing metadata
                            import re
                            response_text = re.sub(r'<!--.*?TOOL_METADATA.*?-->', '', response_text, flags=re.DOTALL)
                            response_text = response_text.strip()
                        if response_text:
                            output += f"**Response:** {response_text}\n"
                        else:
                            output += f"**Response:** (tool response)\n"
                    else:
                        output += f"**Response:** (no response recorded)\n"
                    
                    output += "\n---\n"
            
            # For global searches, append permission metadata at the end
            if search_scope == "global":
                is_admin = context.get('is_admin', False)
                output += f"\n---\n[Search Metadata: PERMISSION_LEVEL={is_admin}]\n"
            
            return ToolResult(
                success=True,
                output=output,
                error=None,
                metadata={
                    "tool": "conversation_memory",
                    "search_query": search_query,
                    "matches_found": result_count
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error searching conversations: {str(e)}",
                metadata={
                    "tool": "conversation_memory",
                    "search_query": search_query
                }
            )

