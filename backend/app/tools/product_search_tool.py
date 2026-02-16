"""Product Search Tool - Search AwesomeGear products catalog"""
from typing import Dict, Any, List
from app.tools.base import Tool, ToolResult
from app.services.awesomegear_service import AwesomeGearService


class ProductSearchTool(Tool):
    """Tool for searching products in the AwesomeGear catalog"""
    
    def _get_description(self) -> str:
        """Get tool description"""
        return ("Search products from AwesomeGear catalog by name, category, or description. "
                "Supports natural language queries like 'find drones under $500' or 'search for gaming laptops'.")
    
    def _get_patterns(self) -> List[str]:
        """Get regex patterns that trigger this tool"""
        return [
            # AwesomeGear specific patterns
            r'\bawesomegear\b',
            r'\bawesome\s+gear\b',
            
            # Product search patterns
            r'\b(what|show|list)\s+(products?|items?|gear)\s+(do\s+you\s+have|are\s+available)',
            r'\bfind\s+products?\s+in\b',
            r'\bsearch\s+products?\s+in\b',
            r'\bshow\s+me\s+products?\s+in\b',
            r'\bproducts?\s+in\s+\w+\s+(category|section)',
            r'\bshow\s+me\s+(tech|apparel|drinkware|accessories|office)',  # Category-specific searches
            
            # Shopping/browsing patterns
            r'\b(browse|shop|buy)\s+(for\s+)?(products?|items?|gear)',
            r'\blooking\s+for\s+(products?|items?|gear)',
        ]
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute product search"""
        try:
            # Get database session from context
            db = context.get("db")
            if not db:
                return ToolResult(
                    success=False,
                    output="",
                    error="Database session not available"
                )
            
            # Initialize AwesomeGear service
            service = AwesomeGearService()
            
            # Extract search query from message
            query = self._extract_query(user_message)
            
            # Execute search (vulnerable to SQL injection!)
            results = await service.query_products(db, query)
            
            # Format results
            if not results:
                return ToolResult(
                    success=True,
                    output="We offer AwesomeGear branded merchandise in these categories:\n\n- Apparel (t-shirts, hoodies)\n- Drinkware (mugs, bottles)\n- Accessories (bags, hats)\n- Tech (USB drives, chargers)\n- Office Supplies (notebooks, pens)\n\nPlease try searching for items in a specific category!",
                    error=None,
                    metadata={"tool": "product_search", "total_count": 0}
                )
            
            # Limit to top 10 results for display
            limited_results = results[:10]
            
            formatted = f"Found {len(results)} product(s) in our AwesomeGear catalog:\n\n"
            for product in limited_results:
                formatted += f"{product['name']} - ${product['price']:.2f}\n"
                formatted += f"  Category: {product['category']}\n"
                formatted += f"  {product['description']}\n"
                if product['stock'] < 10:
                    formatted += f"  ⚠️ Only {product['stock']} left in stock!\n"
                formatted += "\n"
            
            if len(results) > 10:
                formatted += f"... and {len(results) - 10} more products. Try refining your search!\n"
            
            return ToolResult(
                success=True,
                output=formatted,
                error=None,
                metadata={
                    "tool": "product_search",
                    "products": limited_results,
                    "total_count": len(results)
                }
            )
            
        except Exception as e:
            # Return the error - this will leak SQL errors!
            return ToolResult(
                success=False,
                output="",
                error=f"Product search failed: {str(e)}",
                metadata={"tool": "product_search"}
            )
    
    def _extract_query(self, user_message: str) -> str:
        """Extract the search query from the message"""
        # Simple extraction - just return the whole message
        # The AwesomeGear service will parse it
        message_lower = user_message.lower()
        
        # Remove common prefixes
        prefixes = [
            "what products do you have in ",
            "show me products in ",
            "show me ",  # Simple "show me tech" queries
            "find products in ",
            "search products in ",
            "browse products in ",
            "looking for products in ",
            "shop for ",
            "buy ",
        ]
        
        for prefix in prefixes:
            if message_lower.startswith(prefix):
                user_message = user_message[len(prefix):]
                break
        
        return user_message.strip()

