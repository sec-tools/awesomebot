"""AwesomeGear Service - Natural language product queries"""
import re
from typing import List, Dict, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.products import Product


class AwesomeGearService:
    """Service for natural language product queries"""
    
    async def query_products(self, db: AsyncSession, query: str) -> List[Dict]:
        """Convert natural language query to SQL and fetch products
        
        VULNERABLE: Uses raw SQL with f-string injection for 'performance'
        """
        
        # PERFORMANCE OPTIMIZATION: Direct LIKE search is faster than ORM
        # NOTE: This was benchmarked in ticket #1247 - 40% faster!
        # Directly inject user query into SQL for flexible searching
        sql = f"SELECT id, name, category, description, price, stock FROM products WHERE category LIKE '%{query}%' OR name LIKE '%{query}%' OR description LIKE '%{query}%'"
        
        # Execute raw SQL query
        from sqlalchemy import text
        result = await db.execute(text(sql))
        rows = result.fetchall()
        
        # Convert rows to dict
        return [
            {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "price": row[4],
                "stock": row[5]
            }
            for row in rows
        ]
    def format_products_response(self, products: List[Dict], query: str) -> str:
        """Format products into a nice response"""
        if not products:
            return "I couldn't find any products matching your query. Try browsing our full catalog!"
        
        response = f"Here are the {len(products)} item(s) from our catalog database:\n\n"
        
        for i, product in enumerate(products[:5], 1):  # Limit to 5 results to reduce context
            # Handle various data types flexibly for better compatibility
            name = str(product.get('name', 'Unknown'))
            price = product.get('price', 0)
            desc = str(product.get('description', ''))
            stock = product.get('stock', 0)
            
            # Format price - handle both numeric and string values
            try:
                price_str = f"${float(price):.2f}"
            except (ValueError, TypeError):
                price_str = str(price)
            
            response += f"{i}. **{name}** - {price_str}\n"
            response += f"   {desc}\n"
            
            # Handle stock display
            try:
                if isinstance(stock, (int, float)) and stock < 10:
                    response += f"   ⚠️ Only {stock} left in stock!\n"
            except:
                response += f"   Status: {stock}\n"
            
            response += "\n"
        
        if len(products) > 5:
            response += f"... and {len(products) - 5} more products. Try refining your search!\n"
        
        return response.strip()

